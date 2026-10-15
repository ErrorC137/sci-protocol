// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {ProjectRegistry} from "./ProjectRegistry.sol";

/// @dev The slice of FundingPool that the escrow needs, to avoid a circular import.
interface IFundingPool {
    function hasCampaign(uint256 projectId) external view returns (bool);
    function contributionOf(uint256 projectId, address contributor) external view returns (uint256);
}

/// @title MilestoneEscrow
/// @notice "No progress, no money." Holds a project's funds and releases them one milestone
///         at a time, only after an attestor approves the submitted evidence. If a milestone
///         deadline passes without accepted (or under-review) evidence, anyone can trigger a
///         refund and every funder pulls back their pro-rata share of what was never released.
contract MilestoneEscrow is AccessControl, ReentrancyGuard {
    using SafeERC20 for IERC20;

    /// @notice Reviews milestone evidence. Centralized (backend signer) in the demo.
    bytes32 public constant ATTESTOR_ROLE = keccak256("ATTESTOR_ROLE");
    /// @notice Granted to FundingPool so it can move a successful raise into escrow.
    bytes32 public constant POOL_ROLE = keccak256("POOL_ROLE");

    uint256 public constant MAX_MILESTONES = 10;

    enum MilestoneState {
        Pending,
        Submitted,
        Approved,
        Rejected,
        Released
    }

    struct Milestone {
        string descriptionCID;
        uint256 amount;
        uint64 deadline;
        MilestoneState state;
        string evidenceCID;
    }

    struct Ledger {
        uint256 budget; // sum of milestone amounts
        uint256 deposited; // direct deposits + pool deposit
        uint256 poolDeposited; // portion that came from FundingPool (per-contributor shares live there)
        uint256 released; // paid out to the researcher
        uint256 refundPot; // unreleased balance snapshotted when the project failed
        uint256 refunded; // paid back to funders so far
        bool failed;
    }

    IERC20 public immutable token;
    ProjectRegistry public immutable registry;
    IFundingPool public pool;

    mapping(uint256 => Milestone[]) private _milestones;
    mapping(uint256 => Ledger) public ledgers;
    mapping(uint256 => mapping(address => uint256)) public directDeposits;
    mapping(uint256 => mapping(address => bool)) public refundClaimed;

    event PoolSet(address pool);
    event MilestonesSet(uint256 indexed projectId, uint256 count, uint256 budget);
    event Deposited(uint256 indexed projectId, address indexed from, uint256 amount, bool viaPool);
    event EvidenceSubmitted(uint256 indexed projectId, uint256 indexed index, string evidenceCID);
    event MilestoneApproved(uint256 indexed projectId, uint256 indexed index, address indexed attestor);
    event MilestoneRejected(uint256 indexed projectId, uint256 indexed index, address indexed attestor, string reasonCID);
    event MilestoneReleased(uint256 indexed projectId, uint256 indexed index, address indexed researcher, uint256 amount);
    event ProjectFailed(uint256 indexed projectId, uint256 indexed missedIndex, uint256 refundPot);
    event RefundClaimed(uint256 indexed projectId, address indexed funder, uint256 amount);

    error PoolAlreadySet();
    error NotResearcher(uint256 projectId, address caller);
    error NotDraft(uint256 projectId);
    error MilestonesAlreadySet(uint256 projectId);
    error MilestonesNotSet(uint256 projectId);
    error BadMilestoneInput();
    error CampaignActive(uint256 projectId);
    error ExceedsBudget(uint256 projectId, uint256 attempted, uint256 remaining);
    error ZeroAmount();
    error NotFullyFunded(uint256 projectId);
    error ProjectHasFailed(uint256 projectId);
    error ProjectNotFailed(uint256 projectId);
    error NotCurrentMilestone(uint256 projectId, uint256 index, uint256 current);
    error InvalidState(uint256 projectId, uint256 index, MilestoneState state);
    error DeadlinePassed(uint256 projectId, uint256 index);
    error NotRefundable(uint256 projectId);
    error NothingToClaim(uint256 projectId, address funder);
    error AlreadyClaimed(uint256 projectId, address funder);

    constructor(IERC20 token_, ProjectRegistry registry_, address admin) {
        token = token_;
        registry = registry_;
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
    }

    /// @notice One-time wiring; FundingPool and MilestoneEscrow reference each other.
    function setPool(address pool_) external onlyRole(DEFAULT_ADMIN_ROLE) {
        if (address(pool) != address(0)) revert PoolAlreadySet();
        pool = IFundingPool(pool_);
        _grantRole(POOL_ROLE, pool_);
        emit PoolSet(pool_);
    }

    // ---------------------------------------------------------------------
    // Setup & funding
    // ---------------------------------------------------------------------

    /// @notice Researcher declares what the money is for, before any raise opens.
    ///         Deadlines are absolute unix timestamps and must be strictly increasing.
    function setMilestones(
        uint256 projectId,
        string[] calldata descriptionCIDs,
        uint256[] calldata amounts,
        uint64[] calldata deadlines
    ) external {
        _requireResearcher(projectId);
        if (registry.statusOf(projectId) != ProjectRegistry.Status.Draft) revert NotDraft(projectId);
        if (_milestones[projectId].length != 0) revert MilestonesAlreadySet(projectId);
        uint256 n = amounts.length;
        if (n == 0 || n > MAX_MILESTONES || descriptionCIDs.length != n || deadlines.length != n) {
            revert BadMilestoneInput();
        }

        uint256 budget;
        uint64 prev = uint64(block.timestamp);
        for (uint256 i; i < n; ++i) {
            if (amounts[i] == 0 || deadlines[i] <= prev) revert BadMilestoneInput();
            prev = deadlines[i];
            budget += amounts[i];
            _milestones[projectId].push(
                Milestone({
                    descriptionCID: descriptionCIDs[i],
                    amount: amounts[i],
                    deadline: deadlines[i],
                    state: MilestoneState.Pending,
                    evidenceCID: ""
                })
            );
        }
        ledgers[projectId].budget = budget;
        emit MilestonesSet(projectId, n, budget);
    }

    /// @notice Direct deposit by a sponsor (e.g. a grant-maker using escrow without a crowd raise).
    ///         Disabled once a crowd campaign exists, so the two routes can't overshoot the budget.
    function depositForProject(uint256 projectId, uint256 amount) external nonReentrant {
        Ledger storage l = ledgers[projectId];
        if (l.budget == 0) revert MilestonesNotSet(projectId);
        if (l.failed) revert ProjectHasFailed(projectId);
        if (address(pool) != address(0) && pool.hasCampaign(projectId)) revert CampaignActive(projectId);
        _checkedDeposit(projectId, l, amount);
        directDeposits[projectId][msg.sender] += amount;
        token.safeTransferFrom(msg.sender, address(this), amount);
        emit Deposited(projectId, msg.sender, amount, false);
    }

    /// @notice Called by FundingPool when a raise hits its target.
    function depositFromPool(uint256 projectId, uint256 amount) external onlyRole(POOL_ROLE) nonReentrant {
        Ledger storage l = ledgers[projectId];
        if (l.failed) revert ProjectHasFailed(projectId);
        _checkedDeposit(projectId, l, amount);
        l.poolDeposited += amount;
        token.safeTransferFrom(msg.sender, address(this), amount);
        emit Deposited(projectId, msg.sender, amount, true);
    }

    function _checkedDeposit(uint256 projectId, Ledger storage l, uint256 amount) internal {
        if (amount == 0) revert ZeroAmount();
        uint256 remaining = l.budget - l.deposited;
        if (amount > remaining) revert ExceedsBudget(projectId, amount, remaining);
        l.deposited += amount;
        if (l.deposited == l.budget) registry.setStatus(projectId, ProjectRegistry.Status.Funded);
    }

    // ---------------------------------------------------------------------
    // Milestone lifecycle
    // ---------------------------------------------------------------------

    function submitEvidence(uint256 projectId, uint256 index, string calldata evidenceCID) external {
        _requireResearcher(projectId);
        Ledger storage l = ledgers[projectId];
        if (l.failed) revert ProjectHasFailed(projectId);
        if (l.budget == 0 || l.deposited != l.budget) revert NotFullyFunded(projectId);
        _requireCurrent(projectId, index);
        Milestone storage m = _milestones[projectId][index];
        if (m.state != MilestoneState.Pending && m.state != MilestoneState.Rejected) {
            revert InvalidState(projectId, index, m.state);
        }
        if (block.timestamp > m.deadline) revert DeadlinePassed(projectId, index);
        m.evidenceCID = evidenceCID;
        m.state = MilestoneState.Submitted;
        emit EvidenceSubmitted(projectId, index, evidenceCID);
    }

    function approveMilestone(uint256 projectId, uint256 index) external onlyRole(ATTESTOR_ROLE) {
        Milestone storage m = _submitted(projectId, index);
        m.state = MilestoneState.Approved;
        emit MilestoneApproved(projectId, index, msg.sender);
    }

    /// @notice Rejection is not failure: the researcher may resubmit until the deadline.
    function rejectMilestone(uint256 projectId, uint256 index, string calldata reasonCID)
        external
        onlyRole(ATTESTOR_ROLE)
    {
        Milestone storage m = _submitted(projectId, index);
        m.state = MilestoneState.Rejected;
        emit MilestoneRejected(projectId, index, msg.sender, reasonCID);
    }

    /// @notice Anyone may trigger payout of an approved milestone; funds always go to the researcher.
    function releaseMilestone(uint256 projectId, uint256 index) external nonReentrant {
        Ledger storage l = ledgers[projectId];
        if (l.failed) revert ProjectHasFailed(projectId);
        Milestone[] storage ms = _milestones[projectId];
        if (index >= ms.length) revert NotCurrentMilestone(projectId, index, ms.length);
        Milestone storage m = ms[index];
        if (m.state != MilestoneState.Approved) revert InvalidState(projectId, index, m.state);

        m.state = MilestoneState.Released;
        l.released += m.amount;
        address researcher = registry.researcherOf(projectId);
        if (index == ms.length - 1) registry.setStatus(projectId, ProjectRegistry.Status.Completed);
        token.safeTransfer(researcher, m.amount);
        emit MilestoneReleased(projectId, index, researcher, m.amount);
    }

    // ---------------------------------------------------------------------
    // Failure path
    // ---------------------------------------------------------------------

    /// @notice If the current milestone's deadline passed with no accepted or under-review
    ///         evidence, the project fails and all unreleased funds become refundable.
    function refundRemaining(uint256 projectId) external {
        Ledger storage l = ledgers[projectId];
        if (l.failed) revert ProjectHasFailed(projectId);
        if (l.budget == 0) revert MilestonesNotSet(projectId);
        (bool missed, uint256 index) = _missedMilestone(projectId);
        if (!missed) revert NotRefundable(projectId);

        l.failed = true;
        l.refundPot = l.deposited - l.released;
        registry.setStatus(projectId, ProjectRegistry.Status.Failed);
        emit ProjectFailed(projectId, index, l.refundPot);
    }

    /// @notice Pull-based pro-rata refund. Crowd contributors' shares are read from FundingPool.
    function claimRefund(uint256 projectId) external nonReentrant {
        Ledger storage l = ledgers[projectId];
        if (!l.failed) revert ProjectNotFailed(projectId);
        if (refundClaimed[projectId][msg.sender]) revert AlreadyClaimed(projectId, msg.sender);
        uint256 amount = _refundable(projectId, msg.sender);
        if (amount == 0) revert NothingToClaim(projectId, msg.sender);
        refundClaimed[projectId][msg.sender] = true;
        l.refunded += amount;
        token.safeTransfer(msg.sender, amount);
        emit RefundClaimed(projectId, msg.sender, amount);
    }

    // ---------------------------------------------------------------------
    // Views
    // ---------------------------------------------------------------------

    function milestoneCount(uint256 projectId) external view returns (uint256) {
        return _milestones[projectId].length;
    }

    function getMilestone(uint256 projectId, uint256 index) external view returns (Milestone memory) {
        return _milestones[projectId][index];
    }

    function getMilestones(uint256 projectId) external view returns (Milestone[] memory) {
        return _milestones[projectId];
    }

    function budgetOf(uint256 projectId) external view returns (uint256) {
        return ledgers[projectId].budget;
    }

    function depositedOf(uint256 projectId) external view returns (uint256) {
        return ledgers[projectId].deposited;
    }

    function firstDeadline(uint256 projectId) external view returns (uint64) {
        Milestone[] storage ms = _milestones[projectId];
        return ms.length == 0 ? 0 : ms[0].deadline;
    }

    /// @notice Index of the first milestone not yet released (== count when all are released).
    function currentMilestone(uint256 projectId) public view returns (uint256 i) {
        Milestone[] storage ms = _milestones[projectId];
        while (i < ms.length && ms[i].state == MilestoneState.Released) ++i;
    }

    /// @notice True when refundRemaining() would succeed right now.
    function isRefundable(uint256 projectId) external view returns (bool) {
        if (ledgers[projectId].failed || ledgers[projectId].budget == 0) return false;
        (bool missed,) = _missedMilestone(projectId);
        return missed;
    }

    function shareOf(uint256 projectId, address funder) public view returns (uint256) {
        uint256 s = directDeposits[projectId][funder];
        if (ledgers[projectId].poolDeposited > 0) s += pool.contributionOf(projectId, funder);
        return s;
    }

    function refundableOf(uint256 projectId, address funder) external view returns (uint256) {
        if (!ledgers[projectId].failed || refundClaimed[projectId][funder]) return 0;
        return _refundable(projectId, funder);
    }

    // ---------------------------------------------------------------------
    // Internals
    // ---------------------------------------------------------------------

    function _refundable(uint256 projectId, address funder) internal view returns (uint256) {
        Ledger storage l = ledgers[projectId];
        if (l.deposited == 0) return 0;
        // Rounds down; at most a few base units of dust remain in the contract.
        return (l.refundPot * shareOf(projectId, funder)) / l.deposited;
    }

    function _missedMilestone(uint256 projectId) internal view returns (bool, uint256) {
        uint256 i = currentMilestone(projectId);
        Milestone[] storage ms = _milestones[projectId];
        if (i >= ms.length) return (false, i);
        Milestone storage m = ms[i];
        bool open = m.state == MilestoneState.Pending || m.state == MilestoneState.Rejected;
        return (open && block.timestamp > m.deadline, i);
    }

    function _submitted(uint256 projectId, uint256 index) internal view returns (Milestone storage m) {
        if (ledgers[projectId].failed) revert ProjectHasFailed(projectId);
        if (index >= _milestones[projectId].length) revert NotCurrentMilestone(projectId, index, 0);
        m = _milestones[projectId][index];
        if (m.state != MilestoneState.Submitted) revert InvalidState(projectId, index, m.state);
    }

    function _requireCurrent(uint256 projectId, uint256 index) internal view {
        uint256 current = currentMilestone(projectId);
        if (index != current) revert NotCurrentMilestone(projectId, index, current);
    }

    function _requireResearcher(uint256 projectId) internal view {
        if (registry.researcherOf(projectId) != msg.sender) revert NotResearcher(projectId, msg.sender);
    }
}

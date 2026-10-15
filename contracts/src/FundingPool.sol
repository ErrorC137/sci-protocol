// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {ProjectRegistry} from "./ProjectRegistry.sol";
import {MilestoneEscrow} from "./MilestoneEscrow.sol";
import {SCIFraction} from "./SCIFraction.sol";

/// @title FundingPool
/// @notice All-or-nothing crowd raise in a stablecoin. If the target is met, the full amount
///         moves into MilestoneEscrow (released milestone by milestone) and contributors may
///         claim SCIFraction tokens. If the target is missed, contributors withdraw in full.
contract FundingPool is ReentrancyGuard {
    using SafeERC20 for IERC20;

    struct Campaign {
        uint256 target;
        uint256 raised;
        uint64 deadline;
        bool finalized;
        bool exists;
    }

    IERC20 public immutable token;
    ProjectRegistry public immutable registry;
    MilestoneEscrow public immutable escrow;
    SCIFraction public immutable fractions;

    mapping(uint256 => Campaign) public campaigns;
    mapping(uint256 => mapping(address => uint256)) public contributionOf;
    mapping(uint256 => mapping(address => bool)) public withdrawn;
    mapping(uint256 => mapping(address => bool)) public fractionsClaimed;

    event CampaignOpened(uint256 indexed projectId, uint256 target, uint64 deadline);
    event Contributed(uint256 indexed projectId, address indexed contributor, uint256 amount, uint256 raised);
    event CampaignFinalized(uint256 indexed projectId, uint256 raised);
    event ContributionWithdrawn(uint256 indexed projectId, address indexed contributor, uint256 amount);
    event FractionsClaimed(uint256 indexed projectId, address indexed contributor, uint256 amount);

    error NotResearcher(uint256 projectId, address caller);
    error NotDraft(uint256 projectId);
    error CampaignExists(uint256 projectId);
    error NoCampaign(uint256 projectId);
    error MilestonesNotSet(uint256 projectId);
    error NothingToRaise(uint256 projectId);
    error BadDeadline();
    error RaiseClosed(uint256 projectId);
    error AlreadyFinalized(uint256 projectId);
    error TargetNotMet(uint256 projectId);
    error ExceedsTarget(uint256 projectId, uint256 attempted, uint256 remaining);
    error ZeroAmount();
    error RaiseNotFailed(uint256 projectId);
    error NotFinalized(uint256 projectId);
    error NothingToClaim(uint256 projectId, address contributor);

    constructor(IERC20 token_, ProjectRegistry registry_, MilestoneEscrow escrow_, SCIFraction fractions_) {
        token = token_;
        registry = registry_;
        escrow = escrow_;
        fractions = fractions_;
    }

    /// @notice Opens a raise for whatever part of the milestone budget isn't already deposited.
    ///         The raise must close before the first milestone is due.
    function openCampaign(uint256 projectId, uint64 deadline) external {
        if (registry.researcherOf(projectId) != msg.sender) revert NotResearcher(projectId, msg.sender);
        if (registry.statusOf(projectId) != ProjectRegistry.Status.Draft) revert NotDraft(projectId);
        if (campaigns[projectId].exists) revert CampaignExists(projectId);
        uint256 budget = escrow.budgetOf(projectId);
        if (budget == 0) revert MilestonesNotSet(projectId);
        uint256 target = budget - escrow.depositedOf(projectId);
        if (target == 0) revert NothingToRaise(projectId);
        if (deadline <= block.timestamp || deadline >= escrow.firstDeadline(projectId)) revert BadDeadline();

        campaigns[projectId] = Campaign({target: target, raised: 0, deadline: deadline, finalized: false, exists: true});
        registry.setStatus(projectId, ProjectRegistry.Status.Open);
        emit CampaignOpened(projectId, target, deadline);
    }

    /// @notice Contributions are capped at the remaining target; the one that completes it
    ///         also finalizes the raise.
    function contribute(uint256 projectId, uint256 amount) external nonReentrant {
        Campaign storage c = campaigns[projectId];
        if (!c.exists) revert NoCampaign(projectId);
        if (c.finalized) revert AlreadyFinalized(projectId);
        if (block.timestamp > c.deadline) revert RaiseClosed(projectId);
        if (amount == 0) revert ZeroAmount();
        uint256 remaining = c.target - c.raised;
        if (amount > remaining) revert ExceedsTarget(projectId, amount, remaining);

        c.raised += amount;
        contributionOf[projectId][msg.sender] += amount;
        token.safeTransferFrom(msg.sender, address(this), amount);
        emit Contributed(projectId, msg.sender, amount, c.raised);

        if (c.raised == c.target) _finalize(projectId, c);
    }

    function finalize(uint256 projectId) external nonReentrant {
        Campaign storage c = campaigns[projectId];
        if (!c.exists) revert NoCampaign(projectId);
        if (c.finalized) revert AlreadyFinalized(projectId);
        if (c.raised != c.target) revert TargetNotMet(projectId);
        _finalize(projectId, c);
    }

    /// @notice Raise missed its target by the deadline: each contributor takes back exactly what they put in.
    function withdrawIfFailed(uint256 projectId) external nonReentrant {
        Campaign storage c = campaigns[projectId];
        if (!c.exists) revert NoCampaign(projectId);
        if (c.finalized || block.timestamp <= c.deadline) revert RaiseNotFailed(projectId);
        uint256 amount = contributionOf[projectId][msg.sender];
        if (amount == 0 || withdrawn[projectId][msg.sender]) revert NothingToClaim(projectId, msg.sender);

        withdrawn[projectId][msg.sender] = true;
        if (registry.statusOf(projectId) == ProjectRegistry.Status.Open) {
            registry.setStatus(projectId, ProjectRegistry.Status.Failed);
        }
        token.safeTransfer(msg.sender, amount);
        emit ContributionWithdrawn(projectId, msg.sender, amount);
    }

    /// @notice After a successful raise, mint 1 fraction per base unit contributed.
    function claimFractions(uint256 projectId) external {
        if (!campaigns[projectId].finalized) revert NotFinalized(projectId);
        uint256 amount = contributionOf[projectId][msg.sender];
        if (amount == 0 || fractionsClaimed[projectId][msg.sender]) revert NothingToClaim(projectId, msg.sender);
        fractionsClaimed[projectId][msg.sender] = true;
        fractions.mintFractions(projectId, msg.sender, amount);
        emit FractionsClaimed(projectId, msg.sender, amount);
    }

    function hasCampaign(uint256 projectId) external view returns (bool) {
        return campaigns[projectId].exists;
    }

    function isFailed(uint256 projectId) external view returns (bool) {
        Campaign storage c = campaigns[projectId];
        return c.exists && !c.finalized && block.timestamp > c.deadline;
    }

    function _finalize(uint256 projectId, Campaign storage c) internal {
        c.finalized = true;
        token.forceApprove(address(escrow), c.raised);
        escrow.depositFromPool(projectId, c.raised);
        emit CampaignFinalized(projectId, c.raised);
    }
}

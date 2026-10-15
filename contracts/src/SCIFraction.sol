// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {ERC1155} from "@openzeppelin/contracts/token/ERC1155/ERC1155.sol";
import {ERC1155Supply} from "@openzeppelin/contracts/token/ERC1155/extensions/ERC1155Supply.sol";
import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

/// @title SCIFraction
/// @notice ERC-1155 with one token id per project (id == projectId). Each unit is a pro-rata
///         claim on revenue later routed to that project via distributeRevenue().
/// @dev TESTNET MECHANISM DEMONSTRATION ONLY. A claim on future revenue is very likely a
///      security in most jurisdictions; nothing here is an offering.
///      Revenue uses the standard "magnified revenue per share" accounting, with per-holder
///      corrections applied on every mint/transfer so a buyer cannot claim revenue that was
///      distributed before they held the tokens.
contract SCIFraction is ERC1155Supply, AccessControl, ReentrancyGuard {
    using SafeERC20 for IERC20;

    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");
    uint256 private constant MAGNITUDE = 2 ** 128;

    IERC20 public immutable revenueToken;

    mapping(uint256 => uint256) public magnifiedRevenuePerShare;
    mapping(uint256 => mapping(address => int256)) private _corrections;
    mapping(uint256 => mapping(address => uint256)) public withdrawnRevenue;

    event FractionsMinted(uint256 indexed projectId, address indexed to, uint256 amount);
    event RevenueDistributed(uint256 indexed projectId, address indexed from, uint256 amount);
    event RevenueClaimed(uint256 indexed projectId, address indexed holder, uint256 amount);

    error NoHolders(uint256 projectId);
    error ZeroAmount();
    error NothingToClaim(uint256 projectId, address holder);

    constructor(string memory uri_, IERC20 revenueToken_, address admin) ERC1155(uri_) {
        revenueToken = revenueToken_;
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
    }

    function mintFractions(uint256 projectId, address to, uint256 amount) external onlyRole(MINTER_ROLE) {
        _mint(to, projectId, amount, "");
        emit FractionsMinted(projectId, to, amount);
    }

    /// @notice Route revenue (e.g. licensing income) to all current holders of a project's fractions.
    function distributeRevenue(uint256 projectId, uint256 amount) external nonReentrant {
        if (amount == 0) revert ZeroAmount();
        uint256 supply = totalSupply(projectId);
        if (supply == 0) revert NoHolders(projectId);
        magnifiedRevenuePerShare[projectId] += (amount * MAGNITUDE) / supply;
        revenueToken.safeTransferFrom(msg.sender, address(this), amount);
        emit RevenueDistributed(projectId, msg.sender, amount);
    }

    function claimRevenue(uint256 projectId) external nonReentrant {
        uint256 amount = withdrawableRevenueOf(projectId, msg.sender);
        if (amount == 0) revert NothingToClaim(projectId, msg.sender);
        withdrawnRevenue[projectId][msg.sender] += amount;
        revenueToken.safeTransfer(msg.sender, amount);
        emit RevenueClaimed(projectId, msg.sender, amount);
    }

    function accumulatedRevenueOf(uint256 projectId, address holder) public view returns (uint256) {
        int256 magnified =
            int256(magnifiedRevenuePerShare[projectId] * balanceOf(holder, projectId)) + _corrections[projectId][holder];
        // Corrections only ever offset revenue accrued before the holder held tokens, so this is >= 0.
        // forge-lint: disable-next-line(unsafe-typecast)
        return uint256(magnified) / MAGNITUDE;
    }

    function withdrawableRevenueOf(uint256 projectId, address holder) public view returns (uint256) {
        return accumulatedRevenueOf(projectId, holder) - withdrawnRevenue[projectId][holder];
    }

    function _update(address from, address to, uint256[] memory ids, uint256[] memory values)
        internal
        override
    {
        super._update(from, to, ids, values);
        for (uint256 i; i < ids.length; ++i) {
            int256 delta = int256(magnifiedRevenuePerShare[ids[i]] * values[i]);
            if (from != address(0)) _corrections[ids[i]][from] += delta;
            if (to != address(0)) _corrections[ids[i]][to] -= delta;
        }
    }

    function supportsInterface(bytes4 interfaceId) public view override(ERC1155, AccessControl) returns (bool) {
        return super.supportsInterface(interfaceId);
    }
}

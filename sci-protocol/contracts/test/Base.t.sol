// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {MockUSDC} from "../src/MockUSDC.sol";
import {ProjectRegistry} from "../src/ProjectRegistry.sol";
import {MilestoneEscrow} from "../src/MilestoneEscrow.sol";
import {FundingPool} from "../src/FundingPool.sol";
import {SCIFraction} from "../src/SCIFraction.sol";
import {AttestationRegistry} from "../src/AttestationRegistry.sol";
import {Wiring} from "../script/Wiring.sol";

abstract contract BaseTest is Test {
    MockUSDC usdc;
    ProjectRegistry registry;
    AttestationRegistry attestations;
    SCIFraction fractions;
    MilestoneEscrow escrow;
    FundingPool pool;

    address attestor = makeAddr("attestor");
    address researcher = makeAddr("researcher");
    address alice = makeAddr("alice");
    address bob = makeAddr("bob");
    address sponsor = makeAddr("sponsor");
    address stranger = makeAddr("stranger");

    uint256 constant USDC = 1e6;
    uint64 constant DAY = 1 days;

    function setUp() public virtual {
        vm.warp(1_750_000_000);
        usdc = new MockUSDC();
        Wiring.Deployment memory d = Wiring.deployAll(IERC20(address(usdc)), address(this), attestor, "ipfs://{id}");
        registry = d.registry;
        attestations = d.attestations;
        fractions = d.fractions;
        escrow = d.escrow;
        pool = d.pool;

        address[4] memory funders = [alice, bob, sponsor, stranger];
        for (uint256 i; i < funders.length; ++i) {
            usdc.mint(funders[i], 100_000 * USDC);
            vm.startPrank(funders[i]);
            usdc.approve(address(pool), type(uint256).max);
            usdc.approve(address(escrow), type(uint256).max);
            usdc.approve(address(fractions), type(uint256).max);
            vm.stopPrank();
        }
    }

    /// @dev Registers a project with milestones of the given amounts, due 30, 60, 90... days out.
    function _project(uint256[] memory amounts) internal returns (uint256 pid) {
        vm.startPrank(researcher);
        pid = registry.registerProject("bafy-metadata", 4);
        uint256 n = amounts.length;
        string[] memory cids = new string[](n);
        uint64[] memory deadlines = new uint64[](n);
        for (uint256 i; i < n; ++i) {
            cids[i] = string.concat("bafy-milestone-", vm.toString(i));
            deadlines[i] = uint64(block.timestamp) + uint64(30 * DAY * (i + 1));
        }
        escrow.setMilestones(pid, cids, amounts, deadlines);
        vm.stopPrank();
    }

    function _twoMilestones() internal returns (uint256) {
        uint256[] memory a = new uint256[](2);
        a[0] = 4_000 * USDC;
        a[1] = 6_000 * USDC;
        return _project(a);
    }

    function _open(uint256 pid) internal {
        vm.prank(researcher);
        pool.openCampaign(pid, uint64(block.timestamp + 14 * DAY));
    }

    function _fundByCrowd(uint256 pid) internal {
        _open(pid);
        vm.prank(alice);
        pool.contribute(pid, 2_500 * USDC); // 25%
        vm.prank(bob);
        pool.contribute(pid, 7_500 * USDC); // 75% - completes and finalizes the raise
    }

    function _submitAndApprove(uint256 pid, uint256 i) internal {
        vm.prank(researcher);
        escrow.submitEvidence(pid, i, "bafy-evidence");
        vm.prank(attestor);
        escrow.approveMilestone(pid, i);
    }
}

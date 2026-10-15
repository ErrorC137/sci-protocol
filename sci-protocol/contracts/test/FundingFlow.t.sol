// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {BaseTest} from "./Base.t.sol";
import {ProjectRegistry} from "../src/ProjectRegistry.sol";
import {MilestoneEscrow} from "../src/MilestoneEscrow.sol";
import {FundingPool} from "../src/FundingPool.sol";

contract FundingFlowTest is BaseTest {
    // ------------------------------------------------------------------
    // Happy path: raise -> escrow -> evidence -> approve -> release
    // ------------------------------------------------------------------

    function test_HappyPath_CrowdRaiseThroughCompletion() public {
        uint256 pid = _twoMilestones();
        _fundByCrowd(pid);

        (,,, bool finalized,) = pool.campaigns(pid);
        assertTrue(finalized, "raise auto-finalized on target");
        assertEq(usdc.balanceOf(address(escrow)), 10_000 * USDC);
        assertEq(uint8(registry.statusOf(pid)), uint8(ProjectRegistry.Status.Funded));

        _submitAndApprove(pid, 0);
        escrow.releaseMilestone(pid, 0); // permissionless trigger, pays researcher
        assertEq(usdc.balanceOf(researcher), 4_000 * USDC);
        assertEq(escrow.currentMilestone(pid), 1);

        _submitAndApprove(pid, 1);
        escrow.releaseMilestone(pid, 1);
        assertEq(usdc.balanceOf(researcher), 10_000 * USDC);
        assertEq(usdc.balanceOf(address(escrow)), 0);
        assertEq(uint8(registry.statusOf(pid)), uint8(ProjectRegistry.Status.Completed));
    }

    function test_RejectThenResubmit() public {
        uint256 pid = _twoMilestones();
        _fundByCrowd(pid);

        vm.prank(researcher);
        escrow.submitEvidence(pid, 0, "bafy-weak-evidence");
        vm.prank(attestor);
        escrow.rejectMilestone(pid, 0, "bafy-reason");
        assertEq(uint8(escrow.getMilestone(pid, 0).state), uint8(MilestoneEscrow.MilestoneState.Rejected));

        vm.expectRevert(
            abi.encodeWithSelector(
                MilestoneEscrow.InvalidState.selector, pid, 0, MilestoneEscrow.MilestoneState.Rejected
            )
        );
        escrow.releaseMilestone(pid, 0);

        _submitAndApprove(pid, 0);
        escrow.releaseMilestone(pid, 0);
        assertEq(usdc.balanceOf(researcher), 4_000 * USDC);
    }

    // ------------------------------------------------------------------
    // The credibility moment: missed milestone returns money to funders
    // ------------------------------------------------------------------

    function test_MissedMilestone_RefundsFundersProRata() public {
        uint256 pid = _twoMilestones();
        _fundByCrowd(pid);
        _submitAndApprove(pid, 0);
        escrow.releaseMilestone(pid, 0); // researcher earned 4,000 for milestone 0

        uint256 aliceBefore = usdc.balanceOf(alice);
        uint256 bobBefore = usdc.balanceOf(bob);

        // Milestone 1 not refundable before its deadline.
        assertFalse(escrow.isRefundable(pid));
        vm.expectRevert(abi.encodeWithSelector(MilestoneEscrow.NotRefundable.selector, pid));
        escrow.refundRemaining(pid);

        vm.warp(escrow.getMilestone(pid, 1).deadline + 1);
        assertTrue(escrow.isRefundable(pid));
        vm.prank(stranger); // anyone can trigger
        escrow.refundRemaining(pid);
        assertEq(uint8(registry.statusOf(pid)), uint8(ProjectRegistry.Status.Failed));

        // 6,000 unreleased: alice (25%) gets 1,500, bob (75%) gets 4,500.
        assertEq(escrow.refundableOf(pid, alice), 1_500 * USDC);
        vm.prank(alice);
        escrow.claimRefund(pid);
        vm.prank(bob);
        escrow.claimRefund(pid);
        assertEq(usdc.balanceOf(alice) - aliceBefore, 1_500 * USDC);
        assertEq(usdc.balanceOf(bob) - bobBefore, 4_500 * USDC);
        assertEq(usdc.balanceOf(address(escrow)), 0);
        assertEq(usdc.balanceOf(researcher), 4_000 * USDC, "researcher keeps only what was earned");

        vm.prank(alice);
        vm.expectRevert(abi.encodeWithSelector(MilestoneEscrow.AlreadyClaimed.selector, pid, alice));
        escrow.claimRefund(pid);
        vm.prank(stranger);
        vm.expectRevert(abi.encodeWithSelector(MilestoneEscrow.NothingToClaim.selector, pid, stranger));
        escrow.claimRefund(pid);
    }

    function test_SubmittedEvidenceBlocksRefundUntilReviewed() public {
        uint256 pid = _twoMilestones();
        _fundByCrowd(pid);
        vm.prank(researcher);
        escrow.submitEvidence(pid, 0, "bafy-evidence");

        // Attestor is slow; the researcher must not be penalised for review latency.
        vm.warp(escrow.getMilestone(pid, 0).deadline + 1);
        assertFalse(escrow.isRefundable(pid));

        vm.prank(attestor);
        escrow.rejectMilestone(pid, 0, "bafy-reason");
        assertTrue(escrow.isRefundable(pid), "rejected after deadline -> refundable");

        vm.prank(researcher);
        vm.expectRevert(abi.encodeWithSelector(MilestoneEscrow.DeadlinePassed.selector, pid, 0));
        escrow.submitEvidence(pid, 0, "bafy-too-late");
    }

    function test_FailedProjectFreezesEscrow() public {
        uint256 pid = _twoMilestones();
        _fundByCrowd(pid);
        vm.warp(escrow.getMilestone(pid, 0).deadline + 1);
        escrow.refundRemaining(pid);

        vm.prank(researcher);
        vm.expectRevert(abi.encodeWithSelector(MilestoneEscrow.ProjectHasFailed.selector, pid));
        escrow.submitEvidence(pid, 0, "x");
        vm.expectRevert(abi.encodeWithSelector(MilestoneEscrow.ProjectHasFailed.selector, pid));
        escrow.refundRemaining(pid);
    }

    // ------------------------------------------------------------------
    // Direct sponsor route (no crowd raise)
    // ------------------------------------------------------------------

    function test_SponsorDeposit_FundsAndRefunds() public {
        uint256 pid = _twoMilestones();
        vm.prank(sponsor);
        escrow.depositForProject(pid, 10_000 * USDC);
        assertEq(uint8(registry.statusOf(pid)), uint8(ProjectRegistry.Status.Funded));

        vm.warp(escrow.getMilestone(pid, 0).deadline + 1);
        escrow.refundRemaining(pid);
        uint256 before = usdc.balanceOf(sponsor);
        vm.prank(sponsor);
        escrow.claimRefund(pid);
        assertEq(usdc.balanceOf(sponsor) - before, 10_000 * USDC);
    }

    function test_PartialSponsorThenCrowdRaisesRemainder() public {
        uint256 pid = _twoMilestones();
        vm.prank(sponsor);
        escrow.depositForProject(pid, 2_000 * USDC);
        _open(pid);
        (uint256 target,,,,) = pool.campaigns(pid);
        assertEq(target, 8_000 * USDC, "crowd only raises the remainder");

        vm.prank(sponsor);
        vm.expectRevert(abi.encodeWithSelector(MilestoneEscrow.CampaignActive.selector, pid));
        escrow.depositForProject(pid, 1);

        vm.prank(alice);
        pool.contribute(pid, 8_000 * USDC);
        assertEq(uint8(registry.statusOf(pid)), uint8(ProjectRegistry.Status.Funded));

        // Fail before any release: sponsor gets 20%, alice 80% of 10,000.
        vm.warp(escrow.getMilestone(pid, 0).deadline + 1);
        escrow.refundRemaining(pid);
        assertEq(escrow.refundableOf(pid, sponsor), 2_000 * USDC);
        assertEq(escrow.refundableOf(pid, alice), 8_000 * USDC);
    }

    // ------------------------------------------------------------------
    // Raise misses target -> full withdrawal
    // ------------------------------------------------------------------

    function test_RaiseMissesTarget_ContributorsWithdraw() public {
        uint256 pid = _twoMilestones();
        _open(pid);
        vm.prank(alice);
        pool.contribute(pid, 3_000 * USDC);

        vm.prank(alice);
        vm.expectRevert(abi.encodeWithSelector(FundingPool.RaiseNotFailed.selector, pid));
        pool.withdrawIfFailed(pid);

        (,, uint64 deadline,,) = pool.campaigns(pid);
        vm.warp(deadline + 1);
        assertTrue(pool.isFailed(pid));

        vm.prank(bob);
        vm.expectRevert(abi.encodeWithSelector(FundingPool.RaiseClosed.selector, pid));
        pool.contribute(pid, 7_000 * USDC);

        uint256 before = usdc.balanceOf(alice);
        vm.prank(alice);
        pool.withdrawIfFailed(pid);
        assertEq(usdc.balanceOf(alice) - before, 3_000 * USDC);
        assertEq(uint8(registry.statusOf(pid)), uint8(ProjectRegistry.Status.Failed));

        vm.prank(alice);
        vm.expectRevert(abi.encodeWithSelector(FundingPool.NothingToClaim.selector, pid, alice));
        pool.withdrawIfFailed(pid);
    }

    // ------------------------------------------------------------------
    // Guards
    // ------------------------------------------------------------------

    function test_OnlyAttestorApproves() public {
        uint256 pid = _twoMilestones();
        _fundByCrowd(pid);
        vm.prank(researcher);
        escrow.submitEvidence(pid, 0, "bafy-evidence");

        vm.prank(researcher);
        vm.expectRevert();
        escrow.approveMilestone(pid, 0);
    }

    function test_OnlyResearcherSubmits() public {
        uint256 pid = _twoMilestones();
        _fundByCrowd(pid);
        vm.prank(stranger);
        vm.expectRevert(abi.encodeWithSelector(MilestoneEscrow.NotResearcher.selector, pid, stranger));
        escrow.submitEvidence(pid, 0, "bafy-evidence");
    }

    function test_MilestonesAreSequential() public {
        uint256 pid = _twoMilestones();
        _fundByCrowd(pid);
        vm.prank(researcher);
        vm.expectRevert(abi.encodeWithSelector(MilestoneEscrow.NotCurrentMilestone.selector, pid, 1, 0));
        escrow.submitEvidence(pid, 1, "bafy-evidence");
    }

    function test_CannotSubmitBeforeFullyFunded() public {
        uint256 pid = _twoMilestones();
        _open(pid);
        vm.prank(alice);
        pool.contribute(pid, 1_000 * USDC);
        vm.prank(researcher);
        vm.expectRevert(abi.encodeWithSelector(MilestoneEscrow.NotFullyFunded.selector, pid));
        escrow.submitEvidence(pid, 0, "bafy-evidence");
    }

    function test_ContributionCappedAtTarget() public {
        uint256 pid = _twoMilestones();
        _open(pid);
        vm.prank(alice);
        vm.expectRevert(
            abi.encodeWithSelector(FundingPool.ExceedsTarget.selector, pid, 10_001 * USDC, 10_000 * USDC)
        );
        pool.contribute(pid, 10_001 * USDC);
    }

    function test_MilestoneInputValidation() public {
        vm.startPrank(researcher);
        uint256 pid = registry.registerProject("bafy", 3);
        string[] memory cids = new string[](2);
        uint256[] memory amounts = new uint256[](2);
        uint64[] memory deadlines = new uint64[](2);
        amounts[0] = 1;
        amounts[1] = 1;
        deadlines[0] = uint64(block.timestamp + 10 * DAY);
        deadlines[1] = uint64(block.timestamp + 5 * DAY); // not increasing
        vm.expectRevert(MilestoneEscrow.BadMilestoneInput.selector);
        escrow.setMilestones(pid, cids, amounts, deadlines);
        vm.stopPrank();

        vm.prank(stranger);
        vm.expectRevert(abi.encodeWithSelector(MilestoneEscrow.NotResearcher.selector, pid, stranger));
        escrow.setMilestones(pid, cids, amounts, deadlines);
    }

    function test_RaiseMustCloseBeforeFirstMilestone() public {
        uint256 pid = _twoMilestones();
        vm.prank(researcher);
        vm.expectRevert(FundingPool.BadDeadline.selector);
        pool.openCampaign(pid, uint64(block.timestamp + 31 * DAY));
    }

    function test_MetadataFrozenOnceRaiseOpens() public {
        uint256 pid = _twoMilestones();
        _open(pid);
        vm.prank(researcher);
        vm.expectRevert(abi.encodeWithSelector(ProjectRegistry.NotDraft.selector, pid));
        registry.updateMetadata(pid, "bafy-changed");
    }

    // ------------------------------------------------------------------
    // Fuzz: refunds never exceed the pot, and dust is bounded
    // ------------------------------------------------------------------

    function testFuzz_RefundsConserveFunds(uint96 a, uint96 b, uint96 c, bool releaseFirst) public {
        uint256 budget = 10_000 * USDC;
        uint256 x = bound(a, 1, budget - 2);
        uint256 y = bound(b, 1, budget - x - 1);
        uint256 z = budget - x - y;
        c; // sponsor share is z, derived

        uint256 pid = _twoMilestones();
        vm.prank(sponsor);
        escrow.depositForProject(pid, z);
        _open(pid);
        vm.prank(alice);
        pool.contribute(pid, x);
        vm.prank(bob);
        pool.contribute(pid, y);

        if (releaseFirst) {
            _submitAndApprove(pid, 0);
            escrow.releaseMilestone(pid, 0);
        }
        vm.warp(escrow.getMilestone(pid, 1).deadline + 1);
        escrow.refundRemaining(pid);
        (,,,, uint256 pot,,) = escrow.ledgers(pid);

        uint256 total;
        address[3] memory fs = [alice, bob, sponsor];
        for (uint256 i; i < 3; ++i) {
            // A share of a few base units can round down to a zero refund; nothing to claim then.
            if (escrow.refundableOf(pid, fs[i]) == 0) continue;
            uint256 before = usdc.balanceOf(fs[i]);
            vm.prank(fs[i]);
            escrow.claimRefund(pid);
            total += usdc.balanceOf(fs[i]) - before;
        }
        assertLe(total, pot);
        assertLe(pot - total, 3, "dust bounded by number of funders");
        assertEq(usdc.balanceOf(address(escrow)), pot - total);
    }
}

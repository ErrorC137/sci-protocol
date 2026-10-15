// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {BaseTest} from "./Base.t.sol";
import {ProjectRegistry} from "../src/ProjectRegistry.sol";
import {AttestationRegistry} from "../src/AttestationRegistry.sol";
import {SCIFraction} from "../src/SCIFraction.sol";
import {FundingPool} from "../src/FundingPool.sol";

contract ProjectRegistryTest is BaseTest {
    function test_Register() public {
        vm.prank(researcher);
        uint256 pid = registry.registerProject("bafy-meta", 4);
        assertEq(pid, 1);
        ProjectRegistry.Project memory p = registry.getProject(pid);
        assertEq(p.researcher, researcher);
        assertEq(p.trl, 4);
        assertEq(uint8(p.status), uint8(ProjectRegistry.Status.Draft));
        assertEq(p.privateDetailHash, bytes32(0));
    }

    function test_RejectsInvalidTRL() public {
        vm.expectRevert(abi.encodeWithSelector(ProjectRegistry.InvalidTRL.selector, 0));
        registry.registerProject("bafy", 0);
        vm.expectRevert(abi.encodeWithSelector(ProjectRegistry.InvalidTRL.selector, 10));
        registry.registerProject("bafy", 10);
    }

    function test_UpdateTRLIsAttestorGated() public {
        vm.prank(researcher);
        uint256 pid = registry.registerProject("bafy", 4);

        vm.prank(researcher);
        vm.expectRevert();
        registry.updateTRL(pid, 6);

        vm.prank(attestor);
        registry.updateTRL(pid, 5);
        assertEq(registry.getProject(pid).trl, 5);
    }

    function test_StatusIsModuleGated() public {
        vm.prank(researcher);
        uint256 pid = registry.registerProject("bafy", 4);
        vm.prank(researcher);
        vm.expectRevert();
        registry.setStatus(pid, ProjectRegistry.Status.Completed);
    }

    function test_PrivateDetailHashOnlyByResearcher() public {
        vm.prank(researcher);
        uint256 pid = registry.registerProject("bafy", 4);
        vm.prank(stranger);
        vm.expectRevert(abi.encodeWithSelector(ProjectRegistry.NotResearcher.selector, pid, stranger));
        registry.setPrivateDetailHash(pid, keccak256("x"));
        vm.prank(researcher);
        registry.setPrivateDetailHash(pid, keccak256("x"));
        assertEq(registry.getProject(pid).privateDetailHash, keccak256("x"));
    }
}

contract AttestationRegistryTest is BaseTest {
    function test_AnchorIsFirstComeFirstServed() public {
        bytes32 h = keccak256("ciphertext");
        vm.prank(researcher);
        attestations.anchor(h, "bafy-cipher");
        AttestationRegistry.Anchor memory a = attestations.getAnchor(h);
        assertEq(a.submitter, researcher);
        assertEq(a.timestamp, block.timestamp);

        vm.warp(block.timestamp + 1 days);
        vm.prank(stranger);
        vm.expectRevert(
            abi.encodeWithSelector(AttestationRegistry.AlreadyAnchored.selector, h, researcher, uint64(block.timestamp - 1 days))
        );
        attestations.anchor(h, "bafy-copycat");
    }

    function test_AttestIsRoleGated() public {
        vm.prank(stranger);
        vm.expectRevert();
        attestations.attest(1, keccak256("claim"), "bafy-evidence");

        vm.prank(attestor);
        attestations.attest(1, keccak256("claim"), "bafy-evidence");
        AttestationRegistry.Attestation[] memory list = attestations.attestationsOf(1);
        assertEq(list.length, 1);
        assertEq(list[0].attestor, attestor);
        assertEq(list[0].evidenceCID, "bafy-evidence");
    }
}

contract SCIFractionTest is BaseTest {
    function _raised() internal returns (uint256 pid) {
        pid = _twoMilestones();
        _fundByCrowd(pid); // alice 2,500 / bob 7,500
    }

    function test_ClaimFractionsAfterRaise() public {
        uint256 pid = _raised();
        vm.prank(alice);
        pool.claimFractions(pid);
        vm.prank(bob);
        pool.claimFractions(pid);
        assertEq(fractions.balanceOf(alice, pid), 2_500 * USDC);
        assertEq(fractions.totalSupply(pid), 10_000 * USDC);

        vm.prank(alice);
        vm.expectRevert(abi.encodeWithSelector(FundingPool.NothingToClaim.selector, pid, alice));
        pool.claimFractions(pid);
    }

    function test_NoFractionsBeforeFinalized() public {
        uint256 pid = _twoMilestones();
        _open(pid);
        vm.prank(alice);
        pool.contribute(pid, 100 * USDC);
        vm.prank(alice);
        vm.expectRevert(abi.encodeWithSelector(FundingPool.NotFinalized.selector, pid));
        pool.claimFractions(pid);
    }

    function test_OnlyPoolMints() public {
        vm.prank(stranger);
        vm.expectRevert();
        fractions.mintFractions(1, stranger, 1);
    }

    function test_RevenueIsProRataAndTransferSafe() public {
        uint256 pid = _raised();
        vm.prank(alice);
        pool.claimFractions(pid);
        vm.prank(bob);
        pool.claimFractions(pid);

        // 1,000 of licensing revenue: alice 25%, bob 75%. Accounting rounds down by at most 1 base unit.
        vm.prank(sponsor);
        fractions.distributeRevenue(pid, 1_000 * USDC);
        assertApproxEqAbs(fractions.withdrawableRevenueOf(pid, alice), 250 * USDC, 1);
        assertApproxEqAbs(fractions.withdrawableRevenueOf(pid, bob), 750 * USDC, 1);

        // Bob sells half his fractions to stranger AFTER the first distribution.
        vm.prank(bob);
        fractions.safeTransferFrom(bob, stranger, pid, 3_750 * USDC, "");
        assertEq(fractions.withdrawableRevenueOf(pid, stranger), 0, "buyer gets no past revenue");
        assertApproxEqAbs(fractions.withdrawableRevenueOf(pid, bob), 750 * USDC, 1, "seller keeps accrued revenue");

        vm.prank(sponsor);
        fractions.distributeRevenue(pid, 1_000 * USDC);
        assertApproxEqAbs(fractions.withdrawableRevenueOf(pid, stranger), 375 * USDC, 1);
        assertApproxEqAbs(fractions.withdrawableRevenueOf(pid, bob), 1_125 * USDC, 1);

        uint256 before = usdc.balanceOf(bob);
        vm.prank(bob);
        fractions.claimRevenue(pid);
        assertApproxEqAbs(usdc.balanceOf(bob) - before, 1_125 * USDC, 1);
        assertEq(fractions.withdrawableRevenueOf(pid, bob), 0);
    }

    function test_DistributeRequiresHolders() public {
        vm.prank(sponsor);
        vm.expectRevert(abi.encodeWithSelector(SCIFraction.NoHolders.selector, 99));
        fractions.distributeRevenue(99, 1);
    }
}

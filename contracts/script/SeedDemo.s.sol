// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Script, console2} from "forge-std/Script.sol";
import {MockUSDC} from "../src/MockUSDC.sol";
import {ProjectRegistry} from "../src/ProjectRegistry.sol";
import {MilestoneEscrow} from "../src/MilestoneEscrow.sol";
import {FundingPool} from "../src/FundingPool.sol";

/// @notice Pre-stages the two on-chain projects the demo needs, against an existing deployment.
///
///   Project A ("live raise"): registered, milestones set, raise OPEN and unfunded -
///             you contribute, submit evidence, approve and release live on stage.
///   Project B ("failure path"): fully funded, milestone 1 due FAIL_DELAY seconds from now.
///             Run this ~FAIL_DELAY before the pitch; by demo time the deadline has passed,
///             so you click "Trigger refund" and funders visibly get their money back.
///
/// Env: RESEARCHER_KEY, FUNDER_KEY  (two distinct funded testnet wallets)
///      METADATA_CID_A, METADATA_CID_B (from POST /ipfs/pin; scripts/seed-demo.sh does this)
///      FAIL_DELAY (seconds, default 600)
contract SeedDemo is Script {
    function run() external {
        string memory path = string.concat(vm.projectRoot(), "/deployments/", vm.toString(block.chainid), ".json");
        string memory json = vm.readFile(path);
        MockUSDC usdc = MockUSDC(vm.parseJsonAddress(json, ".MockUSDC"));
        ProjectRegistry registry = ProjectRegistry(vm.parseJsonAddress(json, ".ProjectRegistry"));
        MilestoneEscrow escrow = MilestoneEscrow(vm.parseJsonAddress(json, ".MilestoneEscrow"));
        FundingPool pool = FundingPool(vm.parseJsonAddress(json, ".FundingPool"));

        uint256 researcherKey = vm.envUint("RESEARCHER_KEY");
        uint256 funderKey = vm.envUint("FUNDER_KEY");
        string memory cidA = vm.envOr("METADATA_CID_A", string("demo-metadata-a"));
        string memory cidB = vm.envOr("METADATA_CID_B", string("demo-metadata-b"));
        uint64 failDelay = uint64(vm.envOr("FAIL_DELAY", uint256(600)));
        uint64 nowTs = uint64(block.timestamp);

        // Milestone descriptions are short plain text here for convenience; the web app pins
        // a JSON description to IPFS and stores its CID instead. The UI renders either.

        // ---- Project A: live raise -------------------------------------------------
        vm.startBroadcast(researcherKey);
        uint256 a = registry.registerProject(cidA, 5);
        {
            string[] memory d = new string[](2);
            d[0] = "Regenerated NMC cathode meets capacity spec (1 kg pilot batch)";
            d[1] = "Third-party cell test report";
            uint256[] memory amt = new uint256[](2);
            amt[0] = 3_000e6;
            amt[1] = 5_000e6;
            uint64[] memory dl = new uint64[](2);
            dl[0] = nowTs + 30 days;
            dl[1] = nowTs + 90 days;
            escrow.setMilestones(a, d, amt, dl);
        }
        pool.openCampaign(a, nowTs + 14 days);
        vm.stopBroadcast();

        // ---- Project B: funded, milestone about to be missed ----------------------
        vm.startBroadcast(researcherKey);
        uint256 b = registry.registerProject(cidB, 4);
        {
            string[] memory d = new string[](2);
            d[0] = "Reproduce LFP relithiation in an independent lab";
            d[1] = "Upcycled LFP coin-cell prototype";
            uint256[] memory amt = new uint256[](2);
            amt[0] = 1_000e6;
            amt[1] = 2_000e6;
            uint64[] memory dl = new uint64[](2);
            dl[0] = nowTs + failDelay;
            dl[1] = nowTs + failDelay + 30 days;
            escrow.setMilestones(b, d, amt, dl);
        }
        pool.openCampaign(b, nowTs + failDelay / 2);
        vm.stopBroadcast();

        vm.startBroadcast(funderKey);
        if (usdc.balanceOf(vm.addr(funderKey)) < 3_000e6) usdc.faucet();
        usdc.approve(address(pool), type(uint256).max);
        pool.contribute(b, 3_000e6); // completes target -> escrow funded
        vm.stopBroadcast();

        console2.log("Project A (live raise) id:", a);
        console2.log("Project B (failure path) id:", b);
        console2.log("Project B milestone 1 deadline (unix):", nowTs + failDelay);
    }
}

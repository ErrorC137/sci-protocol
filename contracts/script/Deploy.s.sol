// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Script, console2} from "forge-std/Script.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {MockUSDC} from "../src/MockUSDC.sol";
import {Wiring} from "./Wiring.sol";

/// @notice Deploys the full protocol and writes addresses to deployments/<chainId>.json.
///
/// Env:
///   PRIVATE_KEY     deployer key (becomes admin)                     [required]
///   ATTESTOR        attestor address (default: deployer)             [optional]
///   USDC_ADDRESS    existing stablecoin; if unset, deploys MockUSDC   [optional]
///   FRACTION_URI    ERC-1155 metadata URI template with {id}          [optional]
///
///   forge script script/Deploy.s.sol --rpc-url base_sepolia --broadcast
contract Deploy is Script {
    function run() external returns (Wiring.Deployment memory d) {
        uint256 pk = vm.envUint("PRIVATE_KEY");
        address deployer = vm.addr(pk);
        address attestor = vm.envOr("ATTESTOR", deployer);
        address usdcAddr = vm.envOr("USDC_ADDRESS", address(0));
        string memory uri = vm.envOr("FRACTION_URI", string("http://localhost:8000/chain/fractions/{id}.json"));
        uint256 startBlock = block.number;

        vm.startBroadcast(pk);
        if (usdcAddr == address(0)) usdcAddr = address(new MockUSDC());
        d = Wiring.deployAll(IERC20(usdcAddr), deployer, attestor, uri);
        vm.stopBroadcast();

        string memory o = "deployment";
        vm.serializeUint(o, "chainId", block.chainid);
        vm.serializeUint(o, "startBlock", startBlock);
        vm.serializeAddress(o, "deployer", deployer);
        vm.serializeAddress(o, "attestor", attestor);
        vm.serializeAddress(o, "MockUSDC", usdcAddr);
        vm.serializeAddress(o, "ProjectRegistry", address(d.registry));
        vm.serializeAddress(o, "AttestationRegistry", address(d.attestations));
        vm.serializeAddress(o, "SCIFraction", address(d.fractions));
        vm.serializeAddress(o, "MilestoneEscrow", address(d.escrow));
        string memory json = vm.serializeAddress(o, "FundingPool", address(d.pool));
        string memory path = string.concat(vm.projectRoot(), "/deployments/", vm.toString(block.chainid), ".json");
        vm.writeJson(json, path);

        console2.log("Deployed to chain", block.chainid);
        console2.log("Addresses written to", path);
    }
}

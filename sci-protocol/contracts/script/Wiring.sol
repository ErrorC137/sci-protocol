// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {ProjectRegistry} from "../src/ProjectRegistry.sol";
import {MilestoneEscrow} from "../src/MilestoneEscrow.sol";
import {FundingPool} from "../src/FundingPool.sol";
import {SCIFraction} from "../src/SCIFraction.sol";
import {AttestationRegistry} from "../src/AttestationRegistry.sol";

/// @notice Single source of truth for deployment + role wiring, shared by Deploy.s.sol and the tests,
///         so the tests exercise exactly the permissions that ship. The caller must be `admin`.
library Wiring {
    struct Deployment {
        IERC20 usdc;
        ProjectRegistry registry;
        AttestationRegistry attestations;
        SCIFraction fractions;
        MilestoneEscrow escrow;
        FundingPool pool;
    }

    function deployAll(IERC20 usdc, address admin, address attestor, string memory fractionURI)
        internal
        returns (Deployment memory d)
    {
        d.usdc = usdc;
        d.registry = new ProjectRegistry(admin);
        d.attestations = new AttestationRegistry(admin);
        d.fractions = new SCIFraction(fractionURI, usdc, admin);
        d.escrow = new MilestoneEscrow(usdc, d.registry, admin);
        d.pool = new FundingPool(usdc, d.registry, d.escrow, d.fractions);

        d.escrow.setPool(address(d.pool));
        d.registry.grantRole(d.registry.MODULE_ROLE(), address(d.pool));
        d.registry.grantRole(d.registry.MODULE_ROLE(), address(d.escrow));
        d.fractions.grantRole(d.fractions.MINTER_ROLE(), address(d.pool));

        d.registry.grantRole(d.registry.ATTESTOR_ROLE(), attestor);
        d.escrow.grantRole(d.escrow.ATTESTOR_ROLE(), attestor);
        d.attestations.grantRole(d.attestations.ATTESTOR_ROLE(), attestor);
    }
}

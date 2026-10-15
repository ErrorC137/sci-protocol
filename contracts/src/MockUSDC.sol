// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";

/// @title MockUSDC
/// @notice TESTNET ONLY. 6-decimal stand-in for a real stablecoin with an open faucet,
///         so demos use a stablecoin flow instead of native gas tokens.
contract MockUSDC is ERC20 {
    uint256 public constant FAUCET_AMOUNT = 10_000 * 1e6;

    constructor() ERC20("Mock USDC (testnet)", "mUSDC") {}

    function decimals() public pure override returns (uint8) {
        return 6;
    }

    function faucet() external {
        _mint(msg.sender, FAUCET_AMOUNT);
    }

    function mint(address to, uint256 amount) external {
        require(amount <= 1_000_000 * 1e6, "MockUSDC: max 1M per mint");
        _mint(to, amount);
    }
}

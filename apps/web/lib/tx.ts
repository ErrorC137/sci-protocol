"use client";

import { useState } from "react";
import { BaseError, ContractFunctionRevertedError, type Abi, type TransactionReceipt } from "viem";
import { useAccount, usePublicClient, useSwitchChain, useWriteContract } from "wagmi";
import { TARGET_CHAIN } from "./chain";

/** Plain-language versions of the protocol's custom errors, shown instead of hex revert data. */
const FRIENDLY: Record<string, string> = {
  NotRefundable: "Not refundable: the current milestone's deadline hasn't passed, or its evidence is under review.",
  NotResearcher: "Only the project's researcher can do this.",
  NotFullyFunded: "The escrow isn't fully funded yet.",
  DeadlinePassed: "The milestone deadline has passed - evidence can no longer be submitted.",
  NotCurrentMilestone: "Milestones are completed in order - this isn't the current one.",
  InvalidState: "That action isn't possible in the milestone's current state.",
  ExceedsTarget: "That's more than the amount still needed.",
  RaiseClosed: "The raise has closed.",
  RaiseNotFailed: "The raise hasn't failed - withdrawals are only possible if the target was missed.",
  AlreadyAnchored: "This exact hash was already anchored (the first timestamp stands).",
  AlreadyClaimed: "Already claimed.",
  NothingToClaim: "Nothing to claim for this wallet.",
  BadDeadline: "The raise must close in the future and before the first milestone is due.",
  BadMilestoneInput: "Milestones need amounts > 0 and strictly increasing future deadlines.",
  AccessControlUnauthorizedAccount: "This wallet doesn't have the attestor role.",
  ERC20InsufficientBalance: "Not enough test USDC - use the faucet first.",
  ERC20InsufficientAllowance: "Token allowance too low.",
};

export function errorMessage(e: unknown): string {
  if (e instanceof BaseError) {
    const revert = e.walk((err) => err instanceof ContractFunctionRevertedError);
    if (revert instanceof ContractFunctionRevertedError) {
      const name = revert.data?.errorName;
      if (name) return FRIENDLY[name] ?? name;
      return revert.reason ?? revert.shortMessage;
    }
    if (/User rejected|denied/i.test(e.message)) return "Cancelled in wallet.";
    return e.shortMessage;
  }
  return e instanceof Error ? e.message : String(e);
}

export interface TxState {
  label?: string;
  status: "idle" | "pending" | "confirming" | "done" | "error";
  hash?: `0x${string}`;
  error?: string;
}

export interface Call {
  address: `0x${string}`;
  abi: Abi | readonly unknown[];
  functionName: string;
  args?: readonly unknown[];
}

/** simulate (surfaces revert reasons before the wallet prompt) -> write -> wait for receipt. */
export function useTx() {
  const publicClient = usePublicClient({ chainId: TARGET_CHAIN.id });
  const { address, chainId } = useAccount();
  const { switchChainAsync } = useSwitchChain();
  const { writeContractAsync } = useWriteContract();
  const [state, setState] = useState<TxState>({ status: "idle" });

  async function send(label: string, call: Call): Promise<TransactionReceipt> {
    setState({ label, status: "pending" });
    try {
      if (!address || !publicClient) throw new Error("Connect a wallet first.");
      if (chainId !== TARGET_CHAIN.id) await switchChainAsync({ chainId: TARGET_CHAIN.id });
      const { request } = await publicClient.simulateContract({ ...(call as any), account: address });
      const hash = await writeContractAsync(request as any);
      setState({ label, status: "confirming", hash });
      const receipt = await publicClient.waitForTransactionReceipt({ hash });
      if (receipt.status !== "success") throw new Error("Transaction reverted");
      setState({ label, status: "done", hash });
      return receipt;
    } catch (e) {
      setState({ label, status: "error", error: errorMessage(e) });
      throw e;
    }
  }

  return { send, state, busy: state.status === "pending" || state.status === "confirming", reset: () => setState({ status: "idle" }) };
}

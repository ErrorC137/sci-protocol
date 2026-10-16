import { ProjectRegistryAbi, deployments, type Deployment } from "@sci/shared";
import { avalanche, avalancheFuji, baseSepolia, bscTestnet, foundry, type Chain } from "viem/chains";

// Chain facts that don't need the wallet stack: which chain, which deployment, explorer links, enum labels.
// Kept apart from lib/chain.ts (RainbowKit/wagmi config) so light pages - the landing - can import them
// without pulling in wallet connector SDKs.

const CHAINS: Record<number, Chain> = {
  [avalancheFuji.id]: avalancheFuji, // 43113 - default target (testnet)
  [avalanche.id]: avalanche, // 43114 - C-Chain mainnet: only with a real legal structure in place
  [baseSepolia.id]: baseSepolia,
  [bscTestnet.id]: bscTestnet,
  [foundry.id]: foundry,
};

export const TARGET_CHAIN: Chain = CHAINS[Number(process.env.NEXT_PUBLIC_CHAIN_ID || avalancheFuji.id)] ?? avalancheFuji;
export const RPC = process.env.NEXT_PUBLIC_RPC_URL || undefined;
// Addresses from the in-browser deploy page (/setup) can be supplied as NEXT_PUBLIC_DEPLOYMENT_JSON (inlined at
// build time, so redeploy the web app after setting it); otherwise contracts/deployments/<chainId>.json via @sci/shared.
function envDeployment(): Deployment | undefined {
  const raw = process.env.NEXT_PUBLIC_DEPLOYMENT_JSON;
  if (!raw) return undefined;
  try {
    const d = JSON.parse(raw) as Deployment;
    return Number(d.chainId) === TARGET_CHAIN.id ? d : undefined;
  } catch {
    return undefined;
  }
}

export const DEPLOYMENT: Deployment | undefined = envDeployment() ?? deployments[TARGET_CHAIN.id];

export const EXPLORER = TARGET_CHAIN.blockExplorers?.default.url;
export const txUrl = (hash: string) => (EXPLORER ? `${EXPLORER}/tx/${hash}` : undefined);
export const addressUrl = (a: string) => (EXPLORER ? `${EXPLORER}/address/${a}` : undefined);

export const PROJECT_STATUS = ["Draft", "Open", "Funded", "Completed", "Failed"] as const;
export const MILESTONE_STATE = ["Pending", "Submitted", "Approved", "Rejected", "Released"] as const;
export const USDC_DECIMALS = 6;

/** Registry only - enough to list projects without loading every ABI. */
export const registryContract = () => (DEPLOYMENT ? { address: DEPLOYMENT.ProjectRegistry, abi: ProjectRegistryAbi } as const : null);

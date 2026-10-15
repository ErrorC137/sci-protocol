import { connectorsForWallets, getDefaultConfig } from "@rainbow-me/rainbowkit";
import { injectedWallet } from "@rainbow-me/rainbowkit/wallets";
import {
  AttestationRegistryAbi, FundingPoolAbi, MilestoneEscrowAbi, MockUSDCAbi, ProjectRegistryAbi, SCIFractionAbi,
  deployments, type Deployment,
} from "@sci/shared";
import { http, createConfig } from "wagmi";
import { baseSepolia, bscTestnet, foundry, type Chain } from "wagmi/chains";

const CHAINS: Record<number, Chain> = { [baseSepolia.id]: baseSepolia, [bscTestnet.id]: bscTestnet, [foundry.id]: foundry };

export const TARGET_CHAIN: Chain = CHAINS[Number(process.env.NEXT_PUBLIC_CHAIN_ID || baseSepolia.id)] ?? baseSepolia;
const RPC = process.env.NEXT_PUBLIC_RPC_URL || undefined;
const WC_ID = process.env.NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID;

export const wagmiConfig = WC_ID
  ? getDefaultConfig({
      appName: "SCI Protocol",
      projectId: WC_ID,
      chains: [TARGET_CHAIN],
      transports: { [TARGET_CHAIN.id]: http(RPC) },
      ssr: true,
    })
  : createConfig({
      // No WalletConnect project id: offer browser-injected wallets only (MetaMask, Rabby, ...).
      connectors: connectorsForWallets([{ groupName: "Browser wallet", wallets: [injectedWallet] }], {
        appName: "SCI Protocol",
        projectId: "unused",
      }),
      chains: [TARGET_CHAIN],
      transports: { [TARGET_CHAIN.id]: http(RPC) },
      ssr: true,
    });

export const DEPLOYMENT: Deployment | undefined = deployments[TARGET_CHAIN.id];

export function contracts() {
  const d = DEPLOYMENT;
  if (!d) return null;
  return {
    registry: { address: d.ProjectRegistry, abi: ProjectRegistryAbi },
    escrow: { address: d.MilestoneEscrow, abi: MilestoneEscrowAbi },
    pool: { address: d.FundingPool, abi: FundingPoolAbi },
    fractions: { address: d.SCIFraction, abi: SCIFractionAbi },
    attestations: { address: d.AttestationRegistry, abi: AttestationRegistryAbi },
    usdc: { address: d.MockUSDC, abi: MockUSDCAbi },
  } as const;
}

export type Contracts = NonNullable<ReturnType<typeof contracts>>;

export const EXPLORER = TARGET_CHAIN.blockExplorers?.default.url;
export const txUrl = (hash: string) => (EXPLORER ? `${EXPLORER}/tx/${hash}` : undefined);
export const addressUrl = (a: string) => (EXPLORER ? `${EXPLORER}/address/${a}` : undefined);

export const PROJECT_STATUS = ["Draft", "Open", "Funded", "Completed", "Failed"] as const;
export const MILESTONE_STATE = ["Pending", "Submitted", "Approved", "Rejected", "Released"] as const;
export const USDC_DECIMALS = 6;

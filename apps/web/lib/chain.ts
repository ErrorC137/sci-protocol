import { connectorsForWallets, getDefaultConfig } from "@rainbow-me/rainbowkit";
import { injectedWallet } from "@rainbow-me/rainbowkit/wallets";
import {
  AttestationRegistryAbi, FundingPoolAbi, MilestoneEscrowAbi, MockUSDCAbi, ProjectRegistryAbi, SCIFractionAbi,
} from "@sci/shared";
import { http, createConfig } from "wagmi";
import { DEPLOYMENT, RPC, TARGET_CHAIN } from "./chain-meta";

// Wallet config (RainbowKit + wagmi). Plain chain facts live in ./chain-meta and are re-exported here.
export * from "./chain-meta";

const WC_ID = process.env.NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID;

export const wagmiConfig = WC_ID
  ? getDefaultConfig({
      appName: "UPLO",
      projectId: WC_ID,
      chains: [TARGET_CHAIN],
      transports: { [TARGET_CHAIN.id]: http(RPC) },
      ssr: true,
    })
  : createConfig({
      // No WalletConnect project id: offer browser-injected wallets only (MetaMask, Rabby, ...).
      connectors: connectorsForWallets([{ groupName: "Browser wallet", wallets: [injectedWallet] }], {
        appName: "UPLO",
        projectId: "unused",
      }),
      chains: [TARGET_CHAIN],
      transports: { [TARGET_CHAIN.id]: http(RPC) },
      ssr: true,
    });

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

import type { ReactNode } from "react";
import { AppShell } from "@/components/AppShell";
import { Providers } from "../providers";

// Wallet + query providers live here, not in the root layout: the app pages need them, the landing doesn't
// (it loads the wallet stack on demand - components/LandingWallet.tsx).
export default function AppLayout({ children }: { children: ReactNode }) {
  return <Providers><AppShell>{children}</AppShell></Providers>;
}

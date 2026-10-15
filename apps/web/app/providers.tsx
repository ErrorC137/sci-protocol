"use client";

import { RainbowKitProvider, lightTheme } from "@rainbow-me/rainbowkit";
import "@rainbow-me/rainbowkit/styles.css";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { WagmiProvider } from "wagmi";
import { TARGET_CHAIN, wagmiConfig } from "@/lib/chain";

// RainbowKit modal in UPLO colours: lime accent with charcoal text, small radius, the app's own font.
const base = lightTheme({ accentColor: "#D7EB79", accentColorForeground: "#1E2320", borderRadius: "small", overlayBlur: "small" });
const theme = {
  ...base,
  colors: { ...base.colors, modalBackground: "#FAF8F4", modalText: "#1E2320", modalTextSecondary: "#5E645F", generalBorder: "#D9D9D6" },
  fonts: { body: "var(--font-sans), var(--font-thai), ui-sans-serif, system-ui, sans-serif" },
};

export function Providers({ children }: { children: ReactNode }) {
  const [qc] = useState(() => new QueryClient({ defaultOptions: { queries: { refetchOnWindowFocus: false, retry: 1 } } }));
  return (
    <WagmiProvider config={wagmiConfig}>
      <QueryClientProvider client={qc}>
        <RainbowKitProvider initialChain={TARGET_CHAIN} theme={theme}>{children}</RainbowKitProvider>
      </QueryClientProvider>
    </WagmiProvider>
  );
}

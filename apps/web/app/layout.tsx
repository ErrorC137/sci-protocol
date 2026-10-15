import type { Metadata } from "next";
import type { ReactNode } from "react";
import { Nav } from "@/components/Nav";
import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "SCI Protocol",
  description:
    "Describe your research once, in non-confidential terms, and get matched to grants, accelerators and milestone-gated funding.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Providers>
          <Nav />
          <main className="mx-auto max-w-6xl px-4 pb-24 pt-6 sm:px-6">{children}</main>
          <footer className="border-t border-slate-200 py-6 text-center text-xs text-ink-muted">
            Testnet only · no real value · not a securities offering · centralized attestor (decentralizing it is future work)
          </footer>
        </Providers>
      </body>
    </html>
  );
}

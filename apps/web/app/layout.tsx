import type { Metadata, Viewport } from "next";
import { Inter, Noto_Sans_Thai, Space_Grotesk } from "next/font/google";
import type { ReactNode } from "react";
import "./globals.css";
import { Providers } from "./providers";

const display = Space_Grotesk({ subsets: ["latin"], weight: ["500", "600", "700"], variable: "--font-display", display: "swap" });
const sans = Inter({ subsets: ["latin"], variable: "--font-sans", display: "swap" });
const thai = Noto_Sans_Thai({ subsets: ["thai"], weight: ["400", "500", "600", "700"], variable: "--font-thai", display: "swap" });

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL
  || (process.env.VERCEL_PROJECT_PRODUCTION_URL && `https://${process.env.VERCEL_PROJECT_PRODUCTION_URL}`)
  || "http://localhost:3000";

const TAGLINE = "Today's Capital. Tomorrow's Breakthroughs.";
const SUB = "Connecting commercial battery recycling with the next generation of circular innovation.";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: { default: `UPLO · ${TAGLINE}`, template: "%s · UPLO" },
  description: `${TAGLINE} ${SUB}`,
  applicationName: "UPLO",
  openGraph: { title: "UPLO", description: `${TAGLINE} ${SUB}`, siteName: "UPLO", type: "website" },
  twitter: { card: "summary_large_image", title: "UPLO", description: `${TAGLINE} ${SUB}` },
};

export const viewport: Viewport = { themeColor: "#1E2320" };

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className={`${display.variable} ${sans.variable} ${thai.variable}`}>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}

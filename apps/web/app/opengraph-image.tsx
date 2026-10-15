import { ImageResponse } from "next/og";

// Social preview card. TODO(logo): swap the plain-text "UPLO" for the approved logo PNG once supplied.
export const alt = "UPLO - Today's Capital. Tomorrow's Breakthroughs.";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";
export const runtime = "edge"; // rendered on request (also sidesteps a Next 14 build-time font-path bug on Windows)

export default function OpengraphImage() {
  return new ImageResponse(
    (
      <div style={{ width: "100%", height: "100%", display: "flex", flexDirection: "column", justifyContent: "space-between", background: "#EDE8DD", padding: 72, color: "#1E2320", fontFamily: "sans-serif" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ fontSize: 40, fontWeight: 700, letterSpacing: 4 }}>UPLO</div>
          <div style={{ fontSize: 18, letterSpacing: 4, color: "#5E645F" }}>CIRCULAR INNOVATION FINANCE</div>
        </div>
        <div style={{ display: "flex", flexDirection: "column" }}>
          <div style={{ fontSize: 76, fontWeight: 700, lineHeight: 1.05 }}>Today&apos;s Capital.</div>
          <div style={{ display: "flex", marginTop: 12 }}>
            <div style={{ fontSize: 76, fontWeight: 700, lineHeight: 1.05, background: "#1E2320", color: "#D7EB79", padding: "4px 18px" }}>Tomorrow&apos;s Breakthroughs.</div>
          </div>
          <div style={{ fontSize: 28, marginTop: 32, color: "#3E4541", maxWidth: 900 }}>
            Connecting commercial battery recycling with the next generation of circular innovation.
          </div>
        </div>
        <div style={{ display: "flex", fontSize: 18, color: "#5E645F", letterSpacing: 3 }}>
          PEOPLE × CAPITAL × RESEARCH × INDUSTRY × A CLEANER TOMORROW
        </div>
      </div>
    ),
    size,
  );
}

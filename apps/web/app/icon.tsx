import { ImageResponse } from "next/og";

// TODO(logo): replace with the approved UPLO app icon / symbol mark (apps/web/public/brand/uplo-mark.png) once
// supplied. Until then: a neutral brand-colour tile - deliberately not a redrawn logo.
export const size = { width: 32, height: 32 };
export const contentType = "image/png";
export const runtime = "edge"; // rendered on request (also sidesteps a Next 14 build-time font-path bug on Windows)

export default function Icon() {
  return new ImageResponse(
    (
      <div style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", background: "#1E2320", borderRadius: 7 }}>
        <div style={{ width: 12, height: 12, borderRadius: 3, background: "#D7EB79" }} />
      </div>
    ),
    size,
  );
}

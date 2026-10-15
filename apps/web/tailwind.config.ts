import type { Config } from "tailwindcss";

// UPLO design tokens (docs/uplo/brand-brief.md). The six brand colours are the DEFAULT of each scale; the extra
// steps exist for hover/pressed states and for text that has to pass WCAG AA on limestone or white
// (e.g. lime-700 for "positive" text - plain lime is never used for small text on light backgrounds).
export default {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        lime: {
          DEFAULT: "#D7EB79", // Signal Lime - primary CTA, active states, key metrics, capital-flow lines
          50: "#F7FBE4", 100: "#EFF6C9", 200: "#E3F0A0", 300: "#D7EB79", 400: "#C9E05F", 500: "#B3CB45",
          600: "#8FA531", 700: "#5F6F1F", 800: "#46521A",
        },
        charcoal: {
          DEFAULT: "#1E2320", // Deep Charcoal - primary text, dark sections, sidebar, nav
          950: "#131614", 900: "#1E2320", 800: "#29302B", 700: "#363E39", 600: "#4B534E",
          soft: "#3E4541", // secondary text
          muted: "#5E645F", // supporting text; >= 4.5:1 on limestone and white
          dim: "#8A908B", // de-emphasised text ON charcoal; still >= 4.5:1 there
        },
        copper: {
          DEFAULT: "#B57856", // Mineral Copper - industrial / material accent, secondary chart series
          50: "#F8F0EA", 100: "#F0DFD3", 200: "#E1BFA8", 300: "#CC9877", 600: "#9A603F", 700: "#7A4A2F",
        },
        limestone: {
          DEFAULT: "#EDE8DD", // main page background - no pure-white pages
          50: "#FAF8F4", 100: "#F5F2EB", 200: "#EDE8DD", 300: "#E3DCCD", 400: "#D2C8B3",
        },
        sage: {
          DEFAULT: "#A7B8A1", // Sage Gray - secondary info, innovation indicators
          50: "#F1F5EF", 100: "#E2EADF", 200: "#C9D6C4", 600: "#6D8266", 700: "#52654C",
        },
        neutral: { DEFAULT: "#D9D9D6" }, // Neutral Gray - borders, dividers, disabled
        error: {
          DEFAULT: "#B42318", // destructive actions and errors - never lime
          50: "#FEF3F2", 100: "#FEE4E2", 200: "#FECDCA", 600: "#B42318", 700: "#912018",
        },
      },
      fontFamily: {
        sans: ["var(--font-sans)", "var(--font-thai)", "ui-sans-serif", "system-ui", "Segoe UI", "Roboto", "sans-serif"],
        display: ["var(--font-display)", "var(--font-thai)", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      letterSpacing: { eyebrow: "0.18em" },
    },
  },
  plugins: [],
} satisfies Config;

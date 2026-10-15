# UPLO brand assets

Put the **official** transparent UPLO PNGs here (do not redraw or re-typeset the logo):

| File | Use |
|---|---|
| `uplo-logo.png` | wordmark for light backgrounds (limestone / white) |
| `uplo-logo-dark.png` | wordmark for dark backgrounds (charcoal) |
| `uplo-mark.png` | standalone segmented "O" symbol (favicon / app icon), if available |

Then set `LOGO_FILES_PRESENT = true` in `apps/web/components/Logo.tsx`, and swap the placeholders in
`apps/web/app/icon.tsx` and `apps/web/app/opengraph-image.tsx` (search for `TODO(logo)`).

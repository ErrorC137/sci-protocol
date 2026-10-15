import Image from "next/image";
import { cx } from "./ui";

// TODO(logo): the official transparent UPLO PNGs were not supplied with the kit. Drop them in
// apps/web/public/brand/ (uplo-logo.png for light backgrounds, uplo-logo-dark.png for dark ones) and set this
// to true. Until then a plain-text placeholder is rendered - never a redrawn or re-typeset logo.
const LOGO_FILES_PRESENT = false;

export function Logo({ on = "light", className }: { on?: "light" | "dark"; className?: string }) {
  if (LOGO_FILES_PRESENT) {
    return (
      <Image src={on === "dark" ? "/brand/uplo-logo-dark.png" : "/brand/uplo-logo.png"} alt="UPLO"
        width={112} height={28} priority className={cx("h-7 w-auto", className)} />
    );
  }
  return (
    <span className={cx("font-display text-xl font-bold tracking-[0.06em]", on === "dark" ? "text-limestone-50" : "text-charcoal", className)}>
      UPLO
    </span>
  );
}

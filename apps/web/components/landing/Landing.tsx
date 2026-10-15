"use client";

import { gsap } from "gsap";
import Lenis from "lenis";
import { useEffect, type ReactNode } from "react";
import { measure, prefersReducedMotion, startScrollLoop } from "./motion";
import { RingCanvas } from "./RingCanvas";

// Motion layer for the landing page: the scroll store, Lenis smooth scroll (desktop), and GSAP reveals triggered
// by ONE IntersectionObserver - no per-element ScrollTriggers, so there is no layout read per animation and the
// main thread stays quiet on phones.
export function Landing({ children }: { children: ReactNode }) {
  useEffect(() => {
    const stopLoop = startScrollLoop();
    const html = document.documentElement;
    if (prefersReducedMotion()) {
      html.classList.remove("motion");
      return stopLoop;
    }
    // Arriving by client-side navigation skips the inline gate script; switch motion on here instead.
    html.classList.add("motion");
    if (html.classList.contains("preload")) {
      try { sessionStorage.setItem("uplo-preloaded", "1"); } catch { /* private mode */ }
      window.setTimeout(() => html.classList.remove("preload"), 1500);
    }

    // Smooth scroll only where there's a wheel/trackpad; touch devices keep native scrolling.
    const desktop = window.matchMedia("(min-width: 768px) and (pointer: fine)").matches;
    const lenis = desktop ? new Lenis({ lerp: 0.1, smoothWheel: true, anchors: true }) : null;
    const raf = (time: number) => lenis?.raf(time * 1000);
    if (lenis) { gsap.ticker.add(raf); gsap.ticker.lagSmoothing(0); }

    // Take over from the CSS pre-hide within one frame (no flash). Drop the CSS rule FIRST so GSAP doesn't read the
    // pre-hide transform as a base offset, then set the same hidden state inline.
    const groups = Array.from(document.querySelectorAll<HTMLElement>("[data-reveal-group]"));
    const lines = groups.flatMap((g) => Array.from(g.querySelectorAll<HTMLElement>(".reveal-line")));
    const blocks = Array.from(document.querySelectorAll<HTMLElement>(".reveal-block"));
    html.classList.add("motion-ready");
    gsap.set(lines, { yPercent: 105, y: 0 });
    gsap.set(blocks, { autoAlpha: 0, y: 28 });

    const io = new IntersectionObserver((entries) => {
      for (const e of entries) {
        if (!e.isIntersecting) continue;
        const el = e.target as HTMLElement;
        io.unobserve(el);
        if (el.hasAttribute("data-reveal-group")) {
          gsap.to(el.querySelectorAll(".reveal-line"), { yPercent: 0, duration: 1.1, ease: "expo.out", stagger: 0.09 });
        } else {
          gsap.to(el, { autoAlpha: 1, y: 0, duration: 1, ease: "expo.out", delay: Number(el.dataset.revealDelay ?? 0) });
        }
      }
    }, { rootMargin: "0px 0px -10% 0px" });
    [...groups, ...blocks].forEach((el) => io.observe(el));

    // Hero: the headline is already on screen; the supporting copy follows it in.
    const hero = gsap.from([".hero-sub", ".hero-cta"], { autoAlpha: 0, y: 18, duration: 1, ease: "expo.out", stagger: 0.1, delay: 0.15 });

    document.fonts?.ready.then(measure);
    window.addEventListener("load", measure);

    return () => {
      window.removeEventListener("load", measure);
      io.disconnect();
      hero.revert();
      gsap.killTweensOf([...lines, ...blocks]);
      gsap.set([...lines, ...blocks], { clearProps: "all" });
      if (lenis) { gsap.ticker.remove(raf); lenis.destroy(); }
      html.classList.remove("motion", "motion-ready");
      stopLoop();
    };
  }, []);

  return <><RingCanvas />{children}</>;
}

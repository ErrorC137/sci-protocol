"use client";

import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import Lenis from "lenis";
import { useEffect, type ReactNode } from "react";
import { measure, prefersReducedMotion, startScrollLoop } from "./motion";

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

    gsap.registerPlugin(ScrollTrigger);
    const lenis = new Lenis({ lerp: 0.1, smoothWheel: true, anchors: true });
    lenis.on("scroll", ScrollTrigger.update);
    const raf = (time: number) => lenis.raf(time * 1000);
    gsap.ticker.add(raf);
    gsap.ticker.lagSmoothing(0);

    const ctx = gsap.context(() => {
      // Take over from the CSS pre-hide in the same frame (no flash): inline GSAP state, then drop the CSS rule.
      const lines = gsap.utils.toArray<HTMLElement>(".reveal-line");
      const blocks = gsap.utils.toArray<HTMLElement>(".reveal-block");
      gsap.set(lines, { yPercent: 105 });
      gsap.set(blocks, { autoAlpha: 0, y: 28 });
      html.classList.add("motion-ready");

      document.querySelectorAll<HTMLElement>("[data-reveal-group]").forEach((g) => {
        gsap.to(g.querySelectorAll(".reveal-line"), {
          yPercent: 0, duration: 1.1, ease: "expo.out", stagger: 0.09,
          scrollTrigger: { trigger: g, start: "top 88%", once: true },
        });
      });
      blocks.forEach((el) => {
        gsap.to(el, {
          autoAlpha: 1, y: 0, duration: 1, ease: "expo.out", delay: Number(el.dataset.revealDelay ?? 0),
          scrollTrigger: { trigger: el, start: "top 92%", once: true },
        });
      });
      // Hero: headline is already on screen; the supporting copy follows it in.
      gsap.from([".hero-sub", ".hero-cta"], { autoAlpha: 0, y: 18, duration: 1, ease: "expo.out", stagger: 0.1, delay: 0.15 });
    });

    const refresh = () => { measure(); ScrollTrigger.refresh(); };
    document.fonts?.ready.then(refresh);
    window.addEventListener("load", refresh);

    return () => {
      window.removeEventListener("load", refresh);
      ctx.revert();
      gsap.ticker.remove(raf);
      lenis.destroy();
      html.classList.remove("motion", "motion-ready");
      stopLoop();
    };
  }, []);

  return <>{children}</>;
}

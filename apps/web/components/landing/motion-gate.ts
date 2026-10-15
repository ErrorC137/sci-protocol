// Inline, render-blocking gate (runs before first paint). With motion allowed:
//   - `motion` on <html> pre-hides reveal targets (CSS in globals.css) until GSAP takes over;
//   - `preload` shows the S0 preloader on the first desktop visit this session (phones go straight to the headline,
//     which keeps mobile LCP well under 2.5s).
// Failsafes remove both if the app never hydrates, so content can't stay hidden.
export const MOTION_GATE = `(function(){try{var d=document.documentElement;if(matchMedia('(prefers-reduced-motion: reduce)').matches)return;d.classList.add('motion');var first=true;try{first=!sessionStorage.getItem('uplo-preloaded')}catch(e){}if(first&&matchMedia('(min-width: 768px)').matches)d.classList.add('preload');setTimeout(function(){d.classList.remove('preload')},2500);setTimeout(function(){if(!d.classList.contains('motion-ready'))d.classList.remove('motion')},4000)}catch(e){}})();`;

// Inline, render-blocking gate: with motion allowed, `motion` goes on <html> before first paint so reveal targets
// start hidden (CSS in globals.css). If the app never hydrates, the failsafe removes it and everything shows.
export const MOTION_GATE = `(function(){try{var d=document.documentElement;if(!matchMedia('(prefers-reduced-motion: reduce)').matches){d.classList.add('motion');setTimeout(function(){if(!d.classList.contains('motion-ready'))d.classList.remove('motion')},4000)}}catch(e){}})();`;

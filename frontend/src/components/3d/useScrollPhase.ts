import { useEffect, useRef } from 'react';

export interface ScrollAndPointerState {
  scrollProgress: number; // 0.0 to 1.0
  scrollY: number;
  scrollVelocity: number;
  mouseX: number; // -1.0 to 1.0
  mouseY: number; // -1.0 to 1.0
  targetMouseX: number;
  targetMouseY: number;
  isReducedMotion: boolean;
}

/**
 * Hook for capturing smooth scroll and pointer interactions for 3D canvas rendering.
 */
export function useScrollAndPointer() {
  const state = useRef<ScrollAndPointerState>({
    scrollProgress: 0,
    scrollY: 0,
    scrollVelocity: 0,
    mouseX: 0,
    mouseY: 0,
    targetMouseX: 0,
    targetMouseY: 0,
    isReducedMotion: false,
  });

  useEffect(() => {
    // Check reduced motion preference
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    state.current.isReducedMotion = mediaQuery.matches;

    const handleMotionChange = (e: MediaQueryListEvent) => {
      state.current.isReducedMotion = e.matches;
    };
    mediaQuery.addEventListener('change', handleMotionChange);

    let lastScrollY = window.scrollY;
    let lastScrollTime = performance.now();

    const handleScroll = () => {
      const currentScrollY = window.scrollY;
      const currentTime = performance.now();
      const dt = Math.max(1, currentTime - lastScrollTime);
      const totalScrollable = Math.max(1, document.documentElement.scrollHeight - window.innerHeight);
      
      const progress = Math.min(1, Math.max(0, currentScrollY / totalScrollable));
      const velocity = (currentScrollY - lastScrollY) / dt;

      state.current.scrollY = currentScrollY;
      state.current.scrollProgress = progress;
      state.current.scrollVelocity = velocity;

      lastScrollY = currentScrollY;
      lastScrollTime = currentTime;
    };

    const handlePointerMove = (e: PointerEvent) => {
      // Normalize to -1.0 ... +1.0
      const x = (e.clientX / window.innerWidth) * 2 - 1;
      const y = -(e.clientY / window.innerHeight) * 2 + 1;
      state.current.targetMouseX = x;
      state.current.targetMouseY = y;
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    window.addEventListener('pointermove', handlePointerMove, { passive: true });

    // Initial calculation
    handleScroll();

    return () => {
      mediaQuery.removeEventListener('change', handleMotionChange);
      window.removeEventListener('scroll', handleScroll);
      window.removeEventListener('pointermove', handlePointerMove);
    };
  }, []);

  return state;
}


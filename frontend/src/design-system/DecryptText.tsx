import React, { useEffect, useState } from 'react';
import { useReducedMotion } from 'framer-motion';

const CHARS = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ/-.';

export interface DecryptTextProps {
  text: string;
  delayMs?: number;
  durationMs?: number;
  className?: string;
}

/**
 * One-shot scramble-to-resolve text reveal, played once on mount. Echoes
 * the hero's cursor-matrix background without looping or repeating — a
 * single orchestrated entrance, not per-section motion.
 */
export const DecryptText: React.FC<DecryptTextProps> = ({
  text,
  delayMs = 0,
  durationMs = 700,
  className,
}) => {
  const reduceMotion = useReducedMotion();
  const [display, setDisplay] = useState(reduceMotion ? text : '');

  useEffect(() => {
    if (reduceMotion) {
      setDisplay(text);
      return;
    }

    let raf = 0;
    let start: number | null = null;
    const total = text.length;

    const timer = setTimeout(() => {
      const tick = (now: number) => {
        if (start === null) start = now;
        const progress = Math.min((now - start) / durationMs, 1);
        const revealed = Math.floor(progress * total);
        let out = '';
        for (let i = 0; i < total; i++) {
          const ch = text[i];
          if (ch === ' ') {
            out += ' ';
          } else if (i < revealed) {
            out += ch;
          } else {
            out += CHARS[Math.floor(Math.random() * CHARS.length)];
          }
        }
        setDisplay(out);
        if (progress < 1) {
          raf = requestAnimationFrame(tick);
        } else {
          setDisplay(text);
        }
      };
      raf = requestAnimationFrame(tick);
    }, delayMs);

    return () => {
      clearTimeout(timer);
      if (raf) cancelAnimationFrame(raf);
    };
  }, [text, delayMs, durationMs, reduceMotion]);

  return <span className={className}>{display}</span>;
};

import React, { useEffect, useRef, useState } from 'react';
import { cn } from '../lib/cn';

const CHARS = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ/-.';

// Approximate cell metrics for the 10px/14px mono-styled text below.
// The app's ".font-mono" is a system sans stack, not a true fixed-width
// face, so this is a deliberate overscan estimate, not an exact grid.
const CHAR_W = 7;
const LINE_H = 14;

function generateNoise(rows: number, cols: number): string {
  const lines: string[] = [];
  for (let r = 0; r < rows; r++) {
    let line = '';
    for (let c = 0; c < cols; c++) {
      line += CHARS[Math.floor(Math.random() * CHARS.length)];
    }
    lines.push(line);
  }
  return lines.join('\n');
}

export interface CursorMatrixFieldProps {
  className?: string;
}

/**
 * Dense monospace character field on a dark ground, sized to fill whatever
 * container it's placed in (measured live via ResizeObserver, so it covers
 * the full hero at any viewport width instead of a fixed-size block). A
 * radial mask tracks the pointer, brightening nearby glyphs — the
 * cursor-reactive black hero treatment. Pure CSS mask, no per-frame canvas
 * redraw.
 */
export const CursorMatrixField: React.FC<CursorMatrixFieldProps> = ({ className }) => {
  const wrapRef = useRef<HTMLDivElement>(null);
  const [text, setText] = useState(() => generateNoise(20, 40));

  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;

    let lastCols = 0;
    let lastRows = 0;

    const resize = (width: number, height: number) => {
      const cols = Math.ceil(width / CHAR_W) + 4;
      const rows = Math.ceil(height / LINE_H) + 2;
      if (cols !== lastCols || rows !== lastRows) {
        lastCols = cols;
        lastRows = rows;
        setText(generateNoise(rows, cols));
      }
    };

    resize(el.clientWidth, el.clientHeight);

    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry) resize(entry.contentRect.width, entry.contentRect.height);
    });
    observer.observe(el);

    const onMove = (e: MouseEvent) => {
      const rect = el.getBoundingClientRect();
      el.style.setProperty('--mx', `${e.clientX - rect.left}px`);
      el.style.setProperty('--my', `${e.clientY - rect.top}px`);
    };
    window.addEventListener('mousemove', onMove);

    return () => {
      observer.disconnect();
      window.removeEventListener('mousemove', onMove);
    };
  }, []);

  return (
    <div
      ref={wrapRef}
      aria-hidden="true"
      className={cn('absolute inset-0 overflow-hidden select-none pointer-events-none', className)}
      style={{ ['--mx' as string]: '50%', ['--my' as string]: '30%' }}
    >
      <pre className="absolute inset-0 m-0 font-mono text-[10px] leading-[14px] text-white/[0.12] whitespace-pre">
        {text}
      </pre>
      <pre
        className="absolute inset-0 m-0 font-mono text-[10px] leading-[14px] text-white/50 whitespace-pre"
        style={{
          WebkitMaskImage:
            'radial-gradient(circle 240px at var(--mx) var(--my), black 0%, transparent 75%)',
          maskImage:
            'radial-gradient(circle 240px at var(--mx) var(--my), black 0%, transparent 75%)',
        }}
      >
        {text}
      </pre>
    </div>
  );
};

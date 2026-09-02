import React from 'react';
import { cn } from '../lib/cn';

export interface GhostWordmarkProps {
  /** Words rendered oversized and low-contrast, stacked or inline. */
  words: string[];
  className?: string;
}

/**
 * Oversized, low-contrast background wordmark that bleeds off the edges
 * of its container. Purely decorative typographic texture behind a hero
 * or statement section — never the primary reading layer.
 */
export const GhostWordmark: React.FC<GhostWordmarkProps> = ({ words, className }) => {
  return (
    <div
      aria-hidden="true"
      className={cn(
        'pointer-events-none absolute inset-0 z-0 flex items-center overflow-hidden',
        words.length > 1 ? 'justify-between' : 'justify-center',
        className,
      )}
    >
      {words.map((word, i) => (
        <span
          key={`${word}-${i}`}
          className="shrink-0 font-black uppercase leading-none text-border-strong"
          style={{
            fontSize: 'clamp(8rem, 20vw, 16rem)',
            letterSpacing: '-0.05em',
            marginLeft: words.length > 1 && i === 0 ? '-2vw' : undefined,
          }}
        >
          {word}
        </span>
      ))}
    </div>
  );
};

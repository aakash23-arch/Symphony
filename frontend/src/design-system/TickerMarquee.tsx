import React from 'react';
import { cn } from '../lib/cn';

export interface TickerMarqueeProps {
  /** Repeating unit of text rendered across the row (evidence tokens, not decoration). */
  text: string;
  className?: string;
  /** Visual weight — 'ghost' for a faint background layer, 'label' for a readable strip. */
  tone?: 'ghost' | 'label';
}

/**
 * Infinite horizontally-scrolling row of repeating mono text.
 * Pure CSS animation (not scroll-linked) so it never fights the
 * scroll-progress-driven Framer Motion transforms elsewhere on the page.
 * Disabled entirely under prefers-reduced-motion (see index.css).
 */
export const TickerMarquee: React.FC<TickerMarqueeProps> = ({ text, className, tone = 'ghost' }) => {
  const unit = `${text}    `;

  return (
    <div
      aria-hidden="true"
      className={cn(
        'pointer-events-none select-none overflow-hidden whitespace-nowrap font-mono',
        tone === 'ghost' ? 'text-fg-subtle/60 text-xs' : 'text-fg-tertiary text-[0.6875rem] uppercase tracking-wider',
        className,
      )}
    >
      <div className="marquee-track inline-flex w-max">
        <span className="inline-block">{unit.repeat(6)}</span>
        <span className="inline-block">{unit.repeat(6)}</span>
      </div>
    </div>
  );
};

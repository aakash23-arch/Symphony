import React from 'react';
import { cn } from '../lib/cn';

interface PanelProps {
  title: string;
  /** Small right-aligned label, e.g. the layer or provenance tag. */
  tag?: string;
  /** Amber staleness rule shown while the live feed is lost. */
  stale?: boolean;
  staleLabel?: string;
  className?: string;
  bodyClassName?: string;
  children: React.ReactNode;
}

/**
 * The one panel frame. Border, not shadow: drop shadows on a dark console read
 * as muddy, and a 1px border does the separation work at less visual cost.
 */
export const Panel: React.FC<PanelProps> = ({
  title,
  tag,
  stale = false,
  staleLabel,
  className,
  bodyClassName,
  children,
}) => (
  <section
    className={cn(
      'flex flex-col rounded-xl border border-border bg-surface',
      stale && 'border-l-2 border-l-band-medium',
      className,
    )}
    aria-label={title}
  >
    <header className="flex items-center justify-between gap-3 border-b border-border px-5 py-3">
      <h2 className="text-[0.9375rem] font-semibold tracking-tight text-fg">{title}</h2>
      {tag ? (
        <span className="shrink-0 font-mono text-micro uppercase text-fg-tertiary">{tag}</span>
      ) : null}
    </header>

    {stale && staleLabel ? (
      <p className="border-b border-border bg-band-medium/10 px-5 py-1.5 font-mono text-micro uppercase text-band-medium">
        {staleLabel}
      </p>
    ) : null}

    <div className={cn('flex-1 px-5 py-4', bodyClassName)}>{children}</div>
  </section>
);

import React from 'react';
import { cn } from '../lib/cn';

interface PanelProps {
  title: string;
  /** Section number for editorial pacing (e.g. "01", "02", "03"). */
  sectionNumber?: string;
  /** Small right-aligned label, e.g. the layer or provenance tag. */
  tag?: string;
  /** Subtitle or brief layer explanation. */
  subtitle?: string;
  /** Amber staleness rule shown while the live feed is lost. */
  stale?: boolean;
  staleLabel?: string;
  className?: string;
  headerClassName?: string;
  bodyClassName?: string;
  children: React.ReactNode;
}

/**
 * The primary panel frame with editorial section numbering, fine borders,
 * and high-contrast typography hierarchy.
 */
export const Panel: React.FC<PanelProps> = ({
  title,
  sectionNumber,
  tag,
  subtitle,
  stale = false,
  staleLabel,
  className,
  headerClassName,
  bodyClassName,
  children,
}) => (
  <section
    className={cn(
      'group relative flex flex-col border border-border bg-surface transition-all duration-200',
      'hover:border-border-strong',
      stale && 'border-l-4 border-l-band-medium',
      className,
    )}
    aria-label={title}
  >
    <header
      className={cn(
        'flex items-center justify-between gap-3 border-b border-border/80 px-5 py-3.5',
        headerClassName,
      )}
    >
      <div className="flex items-center gap-2.5 min-w-0">
        {sectionNumber ? (
          <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-md bg-accent/10 font-mono text-[0.6875rem] font-bold text-accent">
            {sectionNumber}
          </span>
        ) : null}
        <div className="min-w-0">
          <h2 className="text-sm font-semibold tracking-tight text-fg truncate">{title}</h2>
          {subtitle ? (
            <p className="text-[0.6875rem] text-fg-tertiary truncate">{subtitle}</p>
          ) : null}
        </div>
      </div>

      {tag ? (
        <span className="shrink-0 rounded-md bg-surface-elevated/80 px-2 py-0.5 font-mono text-micro uppercase tracking-wider text-fg-secondary border border-border/60">
          {tag}
        </span>
      ) : null}
    </header>

    {stale && staleLabel ? (
      <p className="border-b border-border bg-band-medium/10 px-5 py-1.5 font-mono text-micro uppercase tracking-wider text-band-medium">
        {staleLabel}
      </p>
    ) : null}

    <div className={cn('flex-1 px-5 py-4', bodyClassName)}>{children}</div>
  </section>
);


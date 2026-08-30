import React from 'react';
import { cn } from '../lib/cn';
import { SectionIndex } from './SectionIndex';

export interface SignalPanelProps {
  title: string;
  subtitle?: string;
  sectionNumber?: string | number;
  tag?: string;
  headerActions?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  bodyClassName?: string;
  stale?: boolean;
  staleLabel?: string;
  accentBorder?: boolean;
}

/**
 * Editorial infrastructure signal panel.
 * Composes section indices, technical telemetry tags, and structured panel body.
 */
export const SignalPanel: React.FC<SignalPanelProps> = ({
  title,
  subtitle,
  sectionNumber,
  tag,
  headerActions,
  children,
  className,
  bodyClassName,
  stale = false,
  staleLabel = 'Telemetry Stale',
  accentBorder = false,
}) => {
  return (
    <section
      aria-label={title}
      className={cn(
        'relative flex flex-col rounded-2xl border border-border/80 bg-surface/95 p-5 shadow-lg backdrop-blur-sm transition-all',
        accentBorder && 'border-accent/40 shadow-accent/5',
        stale && 'opacity-70 border-dashed border-border-strong',
        className,
      )}
    >
      {/* Panel Header */}
      <header className="flex items-start justify-between gap-3 border-b border-border/60 pb-3.5">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            {sectionNumber !== undefined ? (
              <SectionIndex index={sectionNumber} />
            ) : null}
            <h3 className="font-semibold text-sm text-fg tracking-tight truncate uppercase">
              {title}
            </h3>
            {tag ? (
              <span className="rounded border border-border/60 bg-surface-elevated/70 px-2 py-0.5 font-mono text-micro-label uppercase text-fg-tertiary">
                {tag}
              </span>
            ) : null}
          </div>
          {subtitle ? (
            <p className="mt-1 text-micro-label text-fg-muted leading-tight">{subtitle}</p>
          ) : null}
        </div>

        <div className="flex shrink-0 items-center gap-2">
          {stale ? (
            <span className="rounded bg-amber-500/10 px-2 py-0.5 font-mono text-micro-label uppercase text-amber-400 border border-amber-500/30">
              {staleLabel}
            </span>
          ) : null}
          {headerActions}
        </div>
      </header>

      {/* Panel Body */}
      <div className={cn('pt-4 min-h-0 flex-1', bodyClassName)}>{children}</div>
    </section>
  );
};

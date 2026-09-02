import React from 'react';
import { cn } from '../lib/cn';
import { SemanticState } from './StatusIndicator';

export interface TimelineItem {
  id: string | number;
  label: string;
  timestamp: string;
  detail?: string;
  severity?: SemanticState | 'INFO' | 'WARN' | 'CRITICAL' | 'SAFE' | string;
  kind?: string;
  seq?: number;
}

export interface SystemTimelineProps {
  items: TimelineItem[];
  emptyMessage?: string;
  maxHeight?: string;
  className?: string;
  pinnedTopNotice?: string;
}

const SEVERITY_BARS: Record<string, string> = {
  INFO: 'border-l-fg-tertiary',
  SAFE: 'border-l-emerald-500',
  LOW: 'border-l-emerald-500',
  WARN: 'border-l-amber-500',
  MEDIUM: 'border-l-amber-500',
  HIGH: 'border-l-rose-500',
  CRITICAL: 'border-l-red-500 bg-red-950/20',
  UNCERTAIN: 'border-l-purple-400',
};

/**
 * Infrastructure Audit Ledger timeline primitive.
 */
export const SystemTimeline: React.FC<SystemTimelineProps> = ({
  items,
  emptyMessage = 'No system events recorded yet.',
  maxHeight = 'max-h-96',
  className,
  pinnedTopNotice,
}) => {
  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-8 text-center border border-dashed border-border bg-surface">
        <p className="font-mono text-technical-label text-fg-tertiary">{emptyMessage}</p>
      </div>
    );
  }

  return (
    <div className={cn('flex flex-col space-y-2', className)}>
      <ol
        className={cn(
          'scroll-slim space-y-2.5 overflow-y-auto pr-1.5',
          maxHeight,
        )}
      >
        {items.map((item) => {
          const normSeverity = (item.severity ?? 'INFO').toUpperCase();
          const borderStyle = SEVERITY_BARS[normSeverity] ?? 'border-l-fg-tertiary';

          return (
            <li
              key={item.id}
              className={cn(
                'rounded-sm border border-border bg-surface p-3 border-l-4 transition-colors hover:border-r-fg-primary hover:border-y-fg-primary hover:bg-surface-elevated',
                borderStyle,
              )}
            >
              <div className="flex items-baseline justify-between gap-2">
                <span className="font-semibold text-xs text-fg leading-snug truncate">
                  {item.label}
                </span>
                <span className="shrink-0 font-mono tnum text-micro-label text-fg-tertiary">
                  {item.timestamp}
                </span>
              </div>

              {item.detail ? (
                <p className="mt-1 text-xs leading-relaxed text-fg-secondary">
                  {item.detail}
                </p>
              ) : null}

              <div className="mt-2 flex items-center justify-between font-mono text-[0.625rem] text-fg-tertiary uppercase">
                <span>{item.kind ? item.kind.replace(/_/g, ' ') : 'EVENT'}</span>
                {item.seq !== undefined ? <span>SEQ #{item.seq}</span> : null}
              </div>
            </li>
          );
        })}
      </ol>

      {pinnedTopNotice ? (
        <p className="pt-2 text-right font-mono text-micro-label text-fg-muted border-t border-border">
          {pinnedTopNotice}
        </p>
      ) : null}
    </div>
  );
};

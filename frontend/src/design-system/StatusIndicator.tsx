import React from 'react';
import { cn } from '../lib/cn';

export type SemanticState =
  | 'SAFE'
  | 'LOW'
  | 'MEDIUM'
  | 'HIGH'
  | 'CRITICAL'
  | 'UNCERTAIN'
  | 'PROCESSING'
  | 'DISCONNECTED';

export interface StatusIndicatorProps {
  status: SemanticState | string;
  label?: string;
  sublabel?: string;
  size?: 'sm' | 'base' | 'lg';
  variant?: 'dot' | 'badge' | 'card';
  pulse?: boolean;
  className?: string;
}

const STATE_CONFIG: Record<
  string,
  { label: string; text: string; bg: string; border: string; dot: string; glow: string }
> = {
  SAFE: {
    label: 'Safe',
    text: 'text-emerald-400',
    bg: 'bg-emerald-500/10',
    border: 'border-emerald-500/30',
    dot: 'bg-emerald-400',
    glow: 'rgba(16, 185, 129, 0.2)',
  },
  LOW: {
    label: 'Low Risk',
    text: 'text-emerald-400',
    bg: 'bg-emerald-500/10',
    border: 'border-emerald-500/30',
    dot: 'bg-emerald-400',
    glow: 'rgba(16, 185, 129, 0.2)',
  },
  MEDIUM: {
    label: 'Medium Risk',
    text: 'text-amber-400',
    bg: 'bg-amber-500/10',
    border: 'border-amber-500/30',
    dot: 'bg-amber-400',
    glow: 'rgba(245, 158, 11, 0.2)',
  },
  HIGH: {
    label: 'High Threat',
    text: 'text-rose-400',
    bg: 'bg-rose-500/10',
    border: 'border-rose-500/30',
    dot: 'bg-rose-400',
    glow: 'rgba(239, 68, 68, 0.2)',
  },
  CRITICAL: {
    label: 'Critical Alert',
    text: 'text-white font-bold',
    bg: 'bg-red-950/80',
    border: 'border-red-500',
    dot: 'bg-red-500',
    glow: 'rgba(239, 68, 68, 0.4)',
  },
  UNCERTAIN: {
    label: 'Uncertain',
    text: 'text-purple-300',
    bg: 'bg-purple-500/10',
    border: 'border-purple-500/30',
    dot: 'bg-purple-400',
    glow: 'rgba(167, 139, 250, 0.2)',
  },
  PROCESSING: {
    label: 'Processing',
    text: 'text-sky-400',
    bg: 'bg-sky-500/10',
    border: 'border-sky-500/30',
    dot: 'bg-sky-400',
    glow: 'rgba(56, 189, 248, 0.2)',
  },
  DISCONNECTED: {
    label: 'Disconnected',
    text: 'text-fg-tertiary',
    bg: 'bg-surface-elevated/80',
    border: 'border-border',
    dot: 'bg-fg-muted',
    glow: 'transparent',
  },
};

/**
 * High-precision semantic status indicator.
 * Strictly uses color for operational threat states rather than decoration.
 */
export const StatusIndicator: React.FC<StatusIndicatorProps> = ({
  status,
  label,
  sublabel,
  size = 'base',
  variant = 'badge',
  pulse = false,
  className,
}) => {
  const normStatus = status.toUpperCase();
  const config = STATE_CONFIG[normStatus] ?? STATE_CONFIG.DISCONNECTED;
  const displayLabel = label ?? config.label;

  const dotSize = {
    sm: 'h-1.5 w-1.5',
    base: 'h-2 w-2',
    lg: 'h-2.5 w-2.5',
  }[size];

  if (variant === 'dot') {
    return (
      <span className={cn('inline-flex items-center gap-2 font-mono text-technical-label', className)}>
        <span
          className={cn('rounded-full shrink-0', dotSize, config.dot, pulse && 'animate-pulse-dot')}
          style={{ boxShadow: `0 0 6px ${config.glow}` }}
          aria-hidden="true"
        />
        <span className={config.text}>{displayLabel}</span>
      </span>
    );
  }

  if (variant === 'card') {
    return (
      <div
        className={cn(
          'flex items-center justify-between gap-3 rounded-xl border p-3 font-mono transition-all',
          config.bg,
          config.border,
          normStatus === 'CRITICAL' && 'animate-pulse-edge',
          className,
        )}
      >
        <div className="flex items-center gap-2.5">
          <span
            className={cn('rounded-full shrink-0', dotSize, config.dot, pulse && 'animate-pulse-dot')}
            style={{ boxShadow: `0 0 8px ${config.glow}` }}
            aria-hidden="true"
          />
          <div>
            <p className={cn('text-technical-value uppercase font-bold', config.text)}>
              {displayLabel}
            </p>
            {sublabel ? (
              <p className="text-micro-label text-fg-tertiary">{sublabel}</p>
            ) : null}
          </div>
        </div>
        <span className="text-micro-label text-fg-tertiary uppercase">STATE // {normStatus}</span>
      </div>
    );
  }

  // Default 'badge' variant
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 font-mono text-micro-label uppercase tracking-wider',
        config.bg,
        config.border,
        config.text,
        className,
      )}
    >
      <span
        className={cn('rounded-full shrink-0', dotSize, config.dot, pulse && 'animate-pulse-dot')}
        style={{ boxShadow: `0 0 6px ${config.glow}` }}
        aria-hidden="true"
      />
      <span>{displayLabel}</span>
    </span>
  );
};

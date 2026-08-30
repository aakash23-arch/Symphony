import React from 'react';
import { cn } from '../lib/cn';

export interface MetricReadoutProps {
  label: string;
  value: string | number | null;
  unit?: string;
  sublabel?: string;
  nullPlaceholder?: string;
  tone?: 'default' | 'safe' | 'medium' | 'high' | 'critical' | 'uncertain';
  size?: 'sm' | 'base' | 'lg' | 'hero';
  className?: string;
  trend?: {
    direction: 'up' | 'down' | 'neutral';
    value: string;
    pointsTowardsRisk?: boolean;
  };
}

/**
 * Infrastructure-scale numerical readout.
 * Enforces tabular numbers (tnum) so digits never jitter during live streaming telemetry.
 */
export const MetricReadout: React.FC<MetricReadoutProps> = ({
  label,
  value,
  unit,
  sublabel,
  nullPlaceholder = '—',
  tone = 'default',
  size = 'base',
  className,
  trend,
}) => {
  const toneClasses = {
    default: 'text-fg',
    safe: 'text-emerald-400',
    medium: 'text-amber-400',
    high: 'text-rose-400',
    critical: 'text-rose-300 font-bold',
    uncertain: 'text-purple-300',
  }[tone];

  const sizeClasses = {
    sm: 'text-xl',
    base: 'text-3xl',
    lg: 'text-5xl',
    hero: 'text-6xl sm:text-7xl',
  }[size];

  const formattedValue = value === null || value === undefined ? nullPlaceholder : value;

  return (
    <div className={cn('flex flex-col', className)}>
      <div className="flex items-center justify-between gap-2">
        <span className="font-mono text-technical-label uppercase text-fg-tertiary">
          {label}
        </span>
        {unit ? (
          <span className="font-mono text-micro-label text-fg-muted uppercase">{unit}</span>
        ) : null}
      </div>

      <div className="mt-1 flex items-baseline gap-2">
        <span
          className={cn(
            'font-mono tnum font-bold tracking-tight leading-none',
            sizeClasses,
            toneClasses,
          )}
        >
          {formattedValue}
        </span>

        {trend ? (
          <span
            className={cn(
              'font-mono text-micro-label font-semibold',
              trend.pointsTowardsRisk ? 'text-rose-400' : 'text-emerald-400',
            )}
          >
            {trend.direction === 'up' ? '▲' : trend.direction === 'down' ? '▼' : '■'} {trend.value}
          </span>
        ) : null}
      </div>

      {sublabel ? (
        <p className="mt-1 text-micro-label text-fg-muted leading-snug">{sublabel}</p>
      ) : null}
    </div>
  );
};

import React from 'react';
import { cn } from '../lib/cn';
import { NONE } from '../lib/format';

interface MetricProps {
  label: string;
  /**
   * Pass null for "no evidence". The component renders an em dash and the
   * nullLabel, never a zero.
   *
   * This is the component-level guard for the project's cardinal rule: a
   * missing P_spoof means the experts produced nothing, which is a completely
   * different claim from "the probability of synthesis is 0.00". Callers must
   * not `?? 0` on the way in.
   */
  value: string | number | null;
  unit?: string;
  nullLabel?: string;
  hint?: string;
  mono?: boolean;
  valueClassName?: string;
  className?: string;
}

export const Metric: React.FC<MetricProps> = ({
  label,
  value,
  unit,
  nullLabel = 'no evidence',
  hint,
  mono = true,
  valueClassName,
  className,
}) => {
  const absent = value === null || value === undefined || value === '';

  return (
    <div className={cn('min-w-0', className)}>
      <dt className="font-mono text-micro uppercase text-fg-tertiary">{label}</dt>
      <dd
        className={cn(
          'mt-0.5 break-words text-[0.9375rem] text-fg',
          mono && 'font-mono tnum',
          absent && 'text-fg-tertiary',
          valueClassName,
        )}
        title={absent ? nullLabel : String(value)}
      >
        {absent ? NONE : value}
        {!absent && unit ? <span className="ml-1 text-xs text-fg-tertiary">{unit}</span> : null}
      </dd>
      {absent ? (
        <p className="mt-0.5 text-[0.6875rem] text-fg-tertiary/70">{nullLabel}</p>
      ) : hint ? (
        <p className="mt-0.5 text-[0.6875rem] text-fg-tertiary/70">{hint}</p>
      ) : null}
    </div>
  );
};

/**
 * A [0,1] quantity as a bar. Renders no bar at all when the value is null —
 * an empty bar reads as "zero", which is the thing being avoided.
 */
export const MetricBar: React.FC<{
  label: string;
  value: number | null;
  tone?: string;
  nullLabel?: string;
}> = ({ label, value, tone = 'bg-accent', nullLabel = 'no evidence' }) => (
  <div>
    <div className="flex items-baseline justify-between gap-2">
      <span className="font-mono text-micro uppercase text-fg-tertiary">{label}</span>
      <span className={cn('font-mono tnum text-[0.8125rem]', value === null ? 'text-fg-tertiary' : 'text-fg')}>
        {value === null ? NONE : value.toFixed(2)}
      </span>
    </div>
    {value === null ? (
      <p className="mt-1 text-[0.6875rem] text-fg-tertiary/70">{nullLabel}</p>
    ) : (
      <div className="mt-1.5 h-1 overflow-hidden rounded-full bg-surface-elevated">
        <div
          className={cn('h-full rounded-full transition-[width] duration-300', tone)}
          style={{ width: `${Math.max(0, Math.min(1, value)) * 100}%` }}
        />
      </div>
    )}
  </div>
);

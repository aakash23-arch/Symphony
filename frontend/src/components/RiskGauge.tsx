import React from 'react';
import { cn } from '../lib/cn';
import type { RiskBand, PolicyAction } from '../types/contracts';
import { bandLabel, formatScore } from '../lib/risk';

interface RiskGaugeProps {
  /** Risk score 0.00–1.00. Null = not yet available. */
  score: number | null;
  /** Risk band for arc color. */
  band: RiskBand | null;
  /** Human-readable risk label e.g. 'CRITICAL THREAT'. */
  label?: string;
  /** Policy action e.g. 'HOLD', 'ALLOW'. */
  action?: PolicyAction | string | null;
  /** Assessment confidence 0.00–1.00. */
  confidence?: number | null;
  /** Show evaluating animation when true. */
  isEvaluating?: boolean;
  /** Additional detail text e.g. 'POSSIBLE VOICE IMPERSONATION' */
  detail?: string | null;
  className?: string;
}

const BAND_COLOR_MAP: Record<RiskBand, { stroke: string; text: string; bg: string }> = {
  LOW: { stroke: '#059669', text: 'text-emerald-600', bg: 'bg-emerald-50 text-emerald-700' },
  MEDIUM: { stroke: '#D97706', text: 'text-amber-600', bg: 'bg-amber-50 text-amber-700' },
  HIGH: { stroke: '#EA580C', text: 'text-orange-600', bg: 'bg-orange-50 text-orange-700' },
  CRITICAL: { stroke: '#DC2626', text: 'text-red-600', bg: 'bg-red-50 text-red-700' },
  UNCERTAIN: { stroke: '#7C3AED', text: 'text-purple-600', bg: 'bg-purple-50 text-purple-700' },
};

export const RiskGauge: React.FC<RiskGaugeProps> = ({
  score,
  band,
  label,
  action,
  confidence,
  isEvaluating = false,
  detail,
  className,
}) => {
  const currentBand = band ?? 'LOW';
  const bandStyle = BAND_COLOR_MAP[currentBand] || BAND_COLOR_MAP.LOW;

  const radius = 85;
  const center = 110;
  const circumference = 2 * Math.PI * radius;
  const arcLength = circumference * 0.75; // 270 degrees
  const gapLength = circumference * 0.25;

  const validScore = score !== null && Number.isFinite(score) ? Math.max(0, Math.min(1, score)) : 0;
  const strokeDashoffset = arcLength - (validScore * arcLength);

  const confText =
    confidence != null && Number.isFinite(confidence)
      ? confidence >= 0.8
        ? 'HIGH'
        : confidence >= 0.5
        ? 'MEDIUM'
        : 'LOW'
      : 'COMPUTING';

  return (
    <div className={cn('relative flex flex-col items-center justify-center p-6', className)}>
      {/* Eyebrow Label */}
      <div className="flex items-center gap-2 mb-2">
        <span className="h-1.5 w-1.5 rounded-full bg-fg-tertiary" />
        <span className="font-mono text-micro-label uppercase tracking-widest text-fg-tertiary">
          VOICEBELIEF — COMPOSITE RISK
        </span>
      </div>

      {/* SVG Arc Gauge */}
      <div className="relative w-[220px] h-[220px] flex items-center justify-center">
        <svg
          viewBox="0 0 220 220"
          className="w-full h-full"
          style={{ transform: 'rotate(135deg)' }}
        >
          {/* Background Track Arc */}
          <circle
            cx={center}
            cy={center}
            r={radius}
            fill="none"
            stroke="#EBEBEA"
            strokeWidth="8"
            strokeDasharray={`${arcLength} ${gapLength}`}
            strokeLinecap="round"
          />

          {/* Evaluating Pulse Track */}
          {isEvaluating && score === null && (
            <circle
              cx={center}
              cy={center}
              r={radius}
              fill="none"
              stroke="#0A0A0A"
              strokeWidth="8"
              strokeDasharray={`${arcLength * 0.25} ${circumference}`}
              strokeLinecap="round"
              className="animate-spin origin-center"
              style={{ animationDuration: '2s' }}
            />
          )}

          {/* Active Score Arc */}
          {score !== null && (
            <circle
              cx={center}
              cy={center}
              r={radius}
              fill="none"
              stroke={bandStyle.stroke}
              strokeWidth="8"
              strokeDasharray={`${arcLength} ${gapLength}`}
              strokeDashoffset={strokeDashoffset}
              strokeLinecap="round"
              className="transition-all duration-700 ease-out"
            />
          )}
        </svg>

        {/* Center Content */}
        <div className="absolute inset-0 flex flex-col items-center justify-center text-center px-4">
          {score !== null ? (
            <>
              <div className="flex items-baseline justify-center">
                <span className="font-mono font-bold text-5xl tracking-tight text-fg tnum">
                  {formatScore(score)}
                </span>
              </div>
              <span className={cn('font-mono text-xs font-bold uppercase tracking-wider mt-1', bandStyle.text)}>
                {label || (band ? bandLabel(band) : 'EVALUATING')}
              </span>
              <span className="text-micro text-fg-tertiary mt-1 max-w-[140px] truncate">
                {detail || (band === 'LOW' ? 'NOMINAL SPEECH' : 'SUSPICIOUS SIGNAL')}
              </span>
            </>
          ) : (
            <>
              <span className="font-mono text-2xl font-bold tracking-tight text-fg-tertiary animate-pulse">
                —
              </span>
              <span className="font-mono text-[0.6875rem] font-semibold uppercase tracking-wider text-fg-tertiary mt-1">
                EVALUATING
              </span>
              <span className="text-micro text-fg-muted mt-1">STREAMING INGEST</span>
            </>
          )}
        </div>
      </div>

      {/* Footer Metrics */}
      <div className="flex items-center gap-6 mt-2 font-mono text-micro-label uppercase tracking-widest text-fg-secondary">
        <div className="flex items-center gap-1.5">
          <span className="text-fg-tertiary">CONFIDENCE</span>
          <span className="font-bold text-fg">{confText}</span>
        </div>
        <div className="h-3 w-px bg-border" />
        <div className="flex items-center gap-1.5">
          <span className="text-fg-tertiary">ACTION</span>
          <span className={cn('font-bold', bandStyle.text)}>
            {action || (band === 'CRITICAL' || band === 'HIGH' ? 'HOLD + ESCALATE' : 'ALLOW')}
          </span>
        </div>
      </div>
    </div>
  );
};

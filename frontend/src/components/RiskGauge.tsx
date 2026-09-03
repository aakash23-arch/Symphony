import React from 'react';
import { Activity, Clock, Cpu, Radio } from 'lucide-react';
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
  /** Additional detail text e.g. 'LIVE ACOUSTIC EVALUATION' */
  detail?: string | null;
  className?: string;
}

const BAND_COLOR_MAP: Record<string, { stroke: string; text: string; bg: string; glow: string }> = {
  LOW: { stroke: '#059669', text: 'text-emerald-600', bg: 'bg-emerald-50 text-emerald-700', glow: 'rgba(5, 150, 105, 0.4)' },
  GENUINE: { stroke: '#059669', text: 'text-emerald-600', bg: 'bg-emerald-50 text-emerald-700', glow: 'rgba(5, 150, 105, 0.4)' },
  MEDIUM: { stroke: '#D97706', text: 'text-amber-600', bg: 'bg-amber-50 text-amber-700', glow: 'rgba(217, 119, 6, 0.4)' },
  SUSPICIOUS: { stroke: '#D97706', text: 'text-amber-600', bg: 'bg-amber-50 text-amber-700', glow: 'rgba(217, 119, 6, 0.4)' },
  ELEVATED: { stroke: '#D97706', text: 'text-amber-600', bg: 'bg-amber-50 text-amber-700', glow: 'rgba(217, 119, 6, 0.4)' },
  UNCERTAIN: { stroke: '#7C3AED', text: 'text-purple-600', bg: 'bg-purple-50 text-purple-700', glow: 'rgba(124, 58, 237, 0.4)' },
  HIGH: { stroke: '#EA580C', text: 'text-orange-600', bg: 'bg-orange-50 text-orange-700', glow: 'rgba(234, 88, 12, 0.4)' },
  SYNTHETIC: { stroke: '#EA580C', text: 'text-orange-600', bg: 'bg-orange-50 text-orange-700', glow: 'rgba(234, 88, 12, 0.4)' },
  CRITICAL: { stroke: '#DC2626', text: 'text-red-600', bg: 'bg-red-50 text-red-700', glow: 'rgba(220, 38, 38, 0.45)' },
  SYNTHETIC_HIGH_CONFIDENCE: { stroke: '#DC2626', text: 'text-red-600', bg: 'bg-red-50 text-red-700', glow: 'rgba(220, 38, 38, 0.45)' },
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
  const effectiveBandKey = (
    band ?? (score != null ? (score >= 0.75 ? 'CRITICAL' : score >= 0.60 ? 'HIGH' : score >= 0.35 ? 'UNCERTAIN' : 'LOW') : 'LOW')
  ).toUpperCase();

  const bandStyle =
    BAND_COLOR_MAP[effectiveBandKey] ||
    (effectiveBandKey.includes('CRIT')
      ? BAND_COLOR_MAP.CRITICAL
      : effectiveBandKey.includes('HIGH') || effectiveBandKey.includes('SYNTH')
      ? BAND_COLOR_MAP.HIGH
      : effectiveBandKey.includes('UNCERT')
      ? BAND_COLOR_MAP.UNCERTAIN
      : effectiveBandKey.includes('SUSP') || effectiveBandKey.includes('MED')
      ? BAND_COLOR_MAP.SUSPICIOUS
      : BAND_COLOR_MAP.LOW);

  const radius = 90;
  const center = 115;
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
      : 'LOW';

  const actionText =
    action ||
    (effectiveBandKey.includes('CRIT') || effectiveBandKey.includes('HIGH')
      ? 'ESCALATE'
      : effectiveBandKey.includes('UNCERT')
      ? 'STEP_UP'
      : 'ALLOW');

  return (
    <div className={cn('relative flex flex-col items-center justify-center py-4 px-6 overflow-hidden', className)}>
      
      {/* Background Ambient Acoustic Wave Meshes (Left Red / Right Cyan) */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden flex items-center justify-between opacity-70">
        {/* Left Red Particle Wave */}
        <div className="w-1/2 h-full bg-[radial-gradient(ellipse_at_left_center,rgba(239,68,68,0.09)_0%,rgba(239,68,68,0.02)_50%,transparent_75%)]" />
        {/* Right Cyan Particle Wave */}
        <div className="w-1/2 h-full bg-[radial-gradient(ellipse_at_right_center,rgba(56,189,248,0.09)_0%,rgba(59,130,246,0.02)_50%,transparent_75%)]" />
      </div>

      {/* Decorative Wavy Lines on Left and Right (Exact match to reference) */}
      <svg className="absolute left-4 top-1/2 -translate-y-1/2 w-72 h-36 pointer-events-none opacity-30 text-red-500 hidden md:block" viewBox="0 0 200 100" fill="none">
        <path d="M0,50 Q25,20 50,50 T100,50 T150,50 T200,50" stroke="currentColor" strokeWidth="1" strokeDasharray="2 3" />
        <path d="M0,60 Q30,30 60,60 T120,60 T180,60" stroke="currentColor" strokeWidth="1" strokeDasharray="3 4" opacity="0.6" />
        <path d="M0,40 Q20,10 40,40 T80,40 T120,40 T160,40" stroke="currentColor" strokeWidth="0.75" strokeDasharray="1 3" opacity="0.4" />
      </svg>
      <svg className="absolute right-4 top-1/2 -translate-y-1/2 w-72 h-36 pointer-events-none opacity-30 text-cyan-500 hidden md:block" viewBox="0 0 200 100" fill="none">
        <path d="M0,50 Q25,80 50,50 T100,50 T150,50 T200,50" stroke="currentColor" strokeWidth="1" strokeDasharray="2 3" />
        <path d="M0,40 Q30,70 60,40 T120,40 T180,40" stroke="currentColor" strokeWidth="1" strokeDasharray="3 4" opacity="0.6" />
        <path d="M0,60 Q20,90 40,60 T80,60 T120,60 T160,60" stroke="currentColor" strokeWidth="0.75" strokeDasharray="1 3" opacity="0.4" />
      </svg>

      {/* Eyebrow Label */}
      <div className="relative z-10 flex items-center gap-1.5 mb-2">
        <span className="h-1.5 w-1.5 rounded-full bg-red-600 animate-pulse" />
        <span className="font-mono text-[0.625rem] font-semibold uppercase tracking-widest text-fg-tertiary">
          VOICEBELIEF — COMPOSITE RISK
        </span>
      </div>

      {/* SVG Arc Gauge */}
      <div className="relative z-10 w-[210px] h-[210px] flex items-center justify-center my-0.5">
        <svg
          viewBox="0 0 230 230"
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
            strokeWidth="9"
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
              stroke="#DC2626"
              strokeWidth="9"
              strokeDasharray={`${arcLength * 0.25} ${circumference}`}
              strokeLinecap="round"
              className="animate-spin origin-center"
              style={{ animationDuration: '2s' }}
            />
          )}

          {/* Active Score Arc with Soft Glow Drop Shadow */}
          {score !== null && (
            <circle
              cx={center}
              cy={center}
              r={radius}
              fill="none"
              stroke={bandStyle.stroke}
              strokeWidth="9"
              strokeDasharray={`${arcLength} ${gapLength}`}
              strokeDashoffset={strokeDashoffset}
              strokeLinecap="round"
              className="transition-all duration-700 ease-out"
              style={{
                filter: `drop-shadow(0 0 10px ${bandStyle.glow})`,
              }}
            />
          )}
        </svg>

        {/* Center Content */}
        <div className="absolute inset-0 flex flex-col items-center justify-center text-center px-4">
          {score !== null ? (
            <>
              <div className="flex items-baseline justify-center">
                <span className="font-mono font-black text-4xl sm:text-5xl tracking-tight text-fg tnum">
                  {formatScore(score)}
                </span>
              </div>
              <span className={cn('font-mono text-[0.6875rem] font-bold uppercase tracking-wider mt-1', bandStyle.text)}>
                {label || bandLabel(effectiveBandKey, score)}
              </span>
              <span className="font-mono text-[0.5625rem] text-fg-tertiary uppercase tracking-wider mt-0.5">
                {detail || 'LIVE ACOUSTIC EVALUATION'}
              </span>
              {/* Miniature Red Soundwave Icon */}
              <div className="flex items-center gap-0.5 mt-1 text-red-500">
                <span className="h-1 w-0.5 bg-current rounded-full" />
                <span className="h-1.5 w-0.5 bg-current rounded-full" />
                <span className="h-2.5 w-0.5 bg-current rounded-full" />
                <span className="h-1.5 w-0.5 bg-current rounded-full" />
                <span className="h-2 w-0.5 bg-current rounded-full" />
                <span className="h-1 w-0.5 bg-current rounded-full" />
              </div>
            </>
          ) : (
            <>
              <span className="font-mono text-2xl font-bold tracking-tight text-fg-tertiary animate-pulse">
                —
              </span>
              <span className="font-mono text-[0.6875rem] font-bold uppercase tracking-wider text-fg-tertiary mt-1">
                EVALUATING
              </span>
              <span className="font-mono text-[0.5625rem] text-fg-muted mt-0.5">ACOUSTIC STREAM</span>
            </>
          )}
        </div>
      </div>

      {/* Below Arc: Confidence and Action */}
      <div className="relative z-10 flex items-center gap-4 mt-2 font-mono text-[0.6875rem] tracking-wider uppercase text-fg-secondary">
        <div className="flex items-center gap-1.5">
          <span className="text-fg-tertiary">CONFIDENCE</span>
          <strong className="font-bold text-fg">{confText}</strong>
        </div>
        <span className="text-border-strong">|</span>
        <div className="flex items-center gap-1.5">
          <span className="text-fg-tertiary">ACTION</span>
          <strong className={cn('font-bold', bandStyle.text)}>
            {actionText}
          </strong>
        </div>
      </div>

      {/* Bottom Forensic Signal Telemetry Instrument Strip (4 Cards) */}
      <div className="relative z-10 mt-6 w-full max-w-2xl grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono">
        <div className="flex items-center gap-2.5 p-2.5 bg-white border border-border/80 rounded-lg shadow-sm hover:border-fg/20 transition-all">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-red-50 text-red-500">
            <Radio className="h-4 w-4" />
          </div>
          <div className="min-w-0">
            <span className="text-fg-tertiary block text-[0.625rem] font-semibold uppercase">ACOUSTIC SNR</span>
            <strong className="text-fg font-bold text-xs">28.4 dB</strong>
          </div>
        </div>

        <div className="flex items-center gap-2.5 p-2.5 bg-white border border-border/80 rounded-lg shadow-sm hover:border-fg/20 transition-all">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-red-50 text-red-500">
            <Activity className="h-4 w-4" />
          </div>
          <div className="min-w-0">
            <span className="text-fg-tertiary block text-[0.625rem] font-semibold uppercase">SAMPLE RATE</span>
            <strong className="text-fg font-bold text-xs">16.0 kHz</strong>
          </div>
        </div>

        <div className="flex items-center gap-2.5 p-2.5 bg-white border border-border/80 rounded-lg shadow-sm hover:border-fg/20 transition-all">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-red-50 text-red-500">
            <Clock className="h-4 w-4" />
          </div>
          <div className="min-w-0">
            <span className="text-fg-tertiary block text-[0.625rem] font-semibold uppercase">INFERENCE</span>
            <strong className="text-fg font-bold text-xs">&lt; 18 ms</strong>
          </div>
        </div>

        <div className="flex items-center gap-2.5 p-2.5 bg-white border border-border/80 rounded-lg shadow-sm hover:border-fg/20 transition-all">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-red-50 text-red-500">
            <Cpu className="h-4 w-4" />
          </div>
          <div className="min-w-0">
            <span className="text-fg-tertiary block text-[0.625rem] font-semibold uppercase">ATTRIBUTION</span>
            <strong className="text-fg font-bold text-xs">Wav2Vec2</strong>
          </div>
        </div>
      </div>
    </div>
  );
};

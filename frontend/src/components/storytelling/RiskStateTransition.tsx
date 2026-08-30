import React from 'react';
import { AlertCircle, HelpCircle, ShieldAlert, ShieldCheck, ShieldX } from 'lucide-react';
import { bandTokens } from '../../lib/risk';
import { useSession } from '../../state/useSession';
import type { RiskBand } from '../../types/contracts';
import { cn } from '../../lib/cn';

export interface RiskStateTransitionProps {
  className?: string;
}

const ORDERED_BANDS: { band: RiskBand; title: string; subtitle: string; icon: React.FC<{ className?: string }> }[] = [
  {
    band: 'LOW',
    title: 'LOW RISK (0.00 — 0.40)',
    subtitle: 'Nominal baseline. No acoustic or behavioral anomalies detected.',
    icon: ShieldCheck,
  },
  {
    band: 'MEDIUM',
    title: 'MEDIUM ELEVATED (0.41 — 0.69)',
    subtitle: 'Elevated indicators. Secondary verification recommended.',
    icon: AlertCircle,
  },
  {
    band: 'HIGH',
    title: 'HIGH THREAT (0.70 — 0.89)',
    subtitle: 'Strong acoustic spoof probability or anomalous payee novelty.',
    icon: ShieldAlert,
  },
  {
    band: 'CRITICAL',
    title: 'CRITICAL THREAT (0.90 — 1.00)',
    subtitle: 'Definite synthetic voice or high-urgency unauthorized transfer.',
    icon: ShieldX,
  },
];

/**
 * Editorial Risk State Transition Component.
 *
 * Visualizes the 4 progressive threat levels: LOW → MEDIUM → HIGH → CRITICAL
 * with a dedicated, non-collapsed branch for UNCERTAIN.
 *
 * Strict rule: Never map UNCERTAIN into LOW or fabricate confidence when evidence is missing.
 */
export const RiskStateTransition: React.FC<RiskStateTransitionProps> = ({ className }) => {
  const { state } = useSession();
  const decision = state.decision;
  const currentBand = decision?.risk.risk_band ?? null;
  const isUncertain = currentBand === 'UNCERTAIN';

  return (
    <div className={cn('space-y-5 font-mono', className)}>
      {/* 4-Stage Progressive Risk Escalation Ladder */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-4">
        {ORDERED_BANDS.map((item, idx) => {
          const isCurrent = currentBand === item.band;
          const tokens = bandTokens[item.band];
          const Icon = item.icon;

          return (
            <div
              key={item.band}
              className={cn(
                'relative flex flex-col justify-between border p-4 transition-all duration-300',
                isCurrent
                  ? `${tokens.border} ${tokens.surface} ring-1 ring-fg-primary scale-[1.02]`
                  : 'border-border bg-surface opacity-60 hover:opacity-100',
              )}
            >
              <div>
                <div className="flex items-center justify-between text-micro-label text-fg-tertiary pb-2 border-b border-border/40">
                  <span>LEVEL 0{idx + 1}</span>
                  <Icon className={cn('h-4 w-4', isCurrent ? tokens.text : 'text-fg-muted')} />
                </div>

                <p className={cn('mt-2 text-xs font-bold uppercase tracking-wider', isCurrent ? tokens.text : 'text-fg')}>
                  {item.title}
                </p>
                <p className="mt-1 text-[0.6875rem] text-fg-secondary font-sans leading-relaxed">
                  {item.subtitle}
                </p>
              </div>

              <div className="mt-4 border-t border-border/40 pt-2 text-[0.625rem] uppercase">
                {isCurrent ? (
                  <span className={cn('font-bold', tokens.text)}>● ACTIVE SYSTEM LEVEL</span>
                ) : (
                  <span className="text-fg-muted">BAND CRITERIA READY</span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Dedicated UNCERTAIN Fail-Safe Branch (Never mapped into LOW) */}
      <div
        className={cn(
          'relative border p-5 transition-all',
          isUncertain
            ? 'border-purple-600 bg-purple-50 ring-1 ring-purple-600'
            : 'border-border bg-surface opacity-70',
        )}
      >
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-start gap-3.5">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center border border-purple-600 bg-purple-50 text-purple-600">
              <HelpCircle className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold uppercase tracking-wider text-purple-600">
                  UNCERTAIN STATE (DEGRADED CHANNEL / INSUFFICIENT EVIDENCE)
                </span>
                {isUncertain && (
                  <span className="border border-purple-600 bg-purple-50 px-2 py-0.5 text-[0.625rem] font-bold text-purple-700 uppercase">
                    ACTIVE DIRECTIVE
                  </span>
                )}
              </div>
              <p className="mt-1 text-xs text-fg-secondary font-sans">
                Evidence insufficient for a confident action. Triggers automatic fail-safe step-up verification without assuming benign authenticity.
              </p>
            </div>
          </div>

          <div className="shrink-0 text-right font-mono text-micro-label text-fg-tertiary">
            <span>FAIL-SAFE POLICY</span>
            <p className="font-bold text-purple-600">STEP_UP REQUIRED</p>
          </div>
        </div>
      </div>
    </div>
  );
};

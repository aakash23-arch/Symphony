import React from 'react';
import { ShieldAlert, ShieldCheck, ShieldX } from 'lucide-react';
import { NarrativeSection } from '../design-system/NarrativeSection';
import { scoreDisclaimer } from '../lib/risk';
import { useSession } from '../state/useSession';
import { cn } from '../lib/cn';

export const PolicyActionSection: React.FC = () => {
  const { state } = useSession();
  const decision = state.decision;

  const policyActions = [
    {
      action: 'ALLOW',
      band: 'LOW',
      meaning: 'Uncalibrated risk falls within baseline thresholds. Normal execution proceeds without interruption.',
      tone: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-400',
      icon: ShieldCheck,
    },
    {
      action: 'STEP_UP',
      band: 'UNCERTAIN',
      meaning: 'Acoustic or contextual signals require mandatory secondary out-of-band verification.',
      tone: 'border-purple-500/40 bg-purple-500/10 text-purple-300',
      icon: ShieldAlert,
    },
    {
      action: 'HOLD',
      band: 'HIGH',
      meaning: 'High spoof probability or anomalous payee detected. Transaction is halted pending manual human authorization.',
      tone: 'border-amber-500/40 bg-amber-500/10 text-amber-400',
      icon: ShieldAlert,
    },
    {
      action: 'TERMINATE',
      band: 'CRITICAL',
      meaning: 'Definite synthetic speech or known attack pattern detected. Call is severed and accounts are locked immediately.',
      tone: 'border-rose-500/40 bg-rose-500/10 text-rose-400',
      icon: ShieldX,
    },
  ];

  return (
    <NarrativeSection
      index="08"
      title="THE OUTPUT IS AN ACTION."
      subtitle="Detection is useless without deterministic execution. Symphony translates continuous multi-modal threat scores into enforceable policy directives."
      tag="L5 AUTOMATED POLICY"
    >
      <div className="space-y-6">
        {/* Supported Policy Actions Matrix */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {policyActions.map((p) => {
            const Icon = p.icon;
            const isCurrent = decision?.action === p.action;
            return (
              <div
                key={p.action}
                className={cn(
                  'flex flex-col justify-between rounded-2xl border p-5 transition-all',
                  p.tone,
                  isCurrent && 'ring-2 ring-accent scale-[1.02] shadow-xl',
                )}
              >
                <div>
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-technical-value font-bold tracking-wider uppercase">
                      {p.action}
                    </span>
                    <Icon className="h-5 w-5" />
                  </div>
                  <span className="mt-1 font-mono text-micro-label uppercase block opacity-80">
                    BAND: {p.band}
                  </span>
                  <p className="mt-3 text-xs leading-relaxed opacity-90">{p.meaning}</p>
                </div>

                <div className="mt-4 border-t border-current/20 pt-2 font-mono text-[0.625rem] uppercase">
                  {isCurrent ? '● CURRENT PIPELINE DIRECTIVE' : 'POLICY RULE READY'}
                </div>
              </div>
            );
          })}
        </div>

        {/* Disclaimer on Uncalibrated Score Semantics */}
        <div className="rounded-xl border border-border/80 bg-surface/90 p-4 font-mono text-xs text-fg-tertiary">
          <p className="font-bold text-fg-secondary uppercase text-micro-label mb-1">
            SCORE SEMANTICS DISCLOSURE
          </p>
          <p>
            {scoreDisclaimer('UNCALIBRATED_RISK_SCORE')} The numeric output ranks threat priority across calls; it does not estimate a probability of fraud.
          </p>
        </div>
      </div>
    </NarrativeSection>
  );
};

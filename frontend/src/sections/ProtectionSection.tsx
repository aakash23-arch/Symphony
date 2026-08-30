import React, { useState } from 'react';
import { ArrowRight } from 'lucide-react';
import { NarrativeSection } from '../design-system/NarrativeSection';
import { formatAmount } from '../lib/format';
import { useSession } from '../state/useSession';

export const ProtectionSection: React.FC = () => {
  const { state, holdTransaction, releaseTransaction, busy } = useSession();
  const tx = state.transaction;
  const [auditRef, setAuditRef] = useState('');

  const steps = [
    { name: 'VOICE', desc: 'Continuous telephony stream' },
    { name: 'RISK', desc: 'Composite multi-modal score' },
    { name: 'POLICY', desc: 'Rule match & action trigger' },
    { name: 'HOLD', desc: 'Automated disbursement freeze' },
    { name: 'VERIFY', desc: 'Out-of-band human audit' },
    { name: 'RESOLVE', desc: 'Release / Reject execution' },
  ];

  return (
    <NarrativeSection
      index="09"
      title="REAL-TIME TRANSACTION PROTECTION."
      subtitle="Financial loss is prevented before funds leave the building. Automated holds freeze disbursements pending out-of-band verification."
      tag="FINANCIAL DEFENSE"
    >
      <div className="space-y-6">
        {/* Step Progression Ribbon */}
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-6 font-mono text-xs">
          {steps.map((s, idx) => (
            <div
              key={s.name}
              className="rounded-xl border border-border/70 bg-surface/90 p-3.5 flex flex-col justify-between"
            >
              <div className="flex items-center justify-between text-micro-label text-fg-tertiary">
                <span>0{idx + 1}</span>
                {idx < steps.length - 1 ? <ArrowRight className="h-3 w-3 hidden sm:block" /> : null}
              </div>
              <p className="mt-2 font-bold text-fg uppercase">{s.name}</p>
              <p className="text-micro-label text-fg-tertiary mt-0.5">{s.desc}</p>
            </div>
          ))}
        </div>

        {/* Live Transaction Control Strip */}
        {tx ? (
          <div className="rounded-2xl border border-border/80 bg-surface-elevated/50 p-5 shadow-lg backdrop-blur-sm">
            <div className="flex flex-wrap items-center justify-between gap-4 border-b border-border/60 pb-4">
              <div>
                <span className="font-mono text-micro-label uppercase text-fg-tertiary">
                  PROTECTED TRANSACTION RECORD
                </span>
                <p className="font-mono text-lg font-bold text-fg">
                  {formatAmount(tx.amount, tx.currency)} → {tx.beneficiary}
                </p>
              </div>

              <div className="flex items-center gap-2">
                <span className="rounded bg-surface px-3 py-1 font-mono text-xs font-bold uppercase text-accent border border-border">
                  STATE: {tx.state}
                </span>
              </div>
            </div>

            {/* Operator Actions */}
            <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
              <p className="text-xs text-fg-secondary max-w-md">
                Operator can manually enforce an administrative hold or execute release after callback verification.
              </p>

              {tx.state === 'PENDING' && (
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => holdTransaction('Operator intervention from product narrative')}
                  className="rounded-xl border border-amber-500/40 bg-amber-500/10 px-4 py-2 font-mono text-xs font-bold text-amber-400 hover:bg-amber-500/20 disabled:opacity-50"
                >
                  Apply Immediate Hold
                </button>
              )}

              {tx.state === 'HELD' && (
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    placeholder="Audit Ref (e.g. CB-CFO-99)"
                    value={auditRef}
                    onChange={(e) => setAuditRef(e.target.value)}
                    className="rounded-lg border border-border bg-background px-3 py-1.5 font-mono text-xs text-fg focus:outline-none focus:border-accent"
                  />
                  <button
                    type="button"
                    disabled={busy || !auditRef.trim()}
                    onClick={() => releaseTransaction(auditRef, true)}
                    className="rounded-lg bg-emerald-600 px-3 py-1.5 font-mono text-xs font-bold text-white hover:bg-emerald-500 disabled:opacity-50"
                  >
                    Release
                  </button>
                  <button
                    type="button"
                    disabled={busy || !auditRef.trim()}
                    onClick={() => releaseTransaction(auditRef, false)}
                    className="rounded-lg bg-rose-600 px-3 py-1.5 font-mono text-xs font-bold text-white hover:bg-rose-500 disabled:opacity-50"
                  >
                    Reject
                  </button>
                </div>
              )}
            </div>
          </div>
        ) : null}
      </div>
    </NarrativeSection>
  );
};

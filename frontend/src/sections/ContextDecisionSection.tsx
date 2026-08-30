import React from 'react';
import { Plus } from 'lucide-react';
import { NarrativeSection } from '../design-system/NarrativeSection';
import { formatAmount } from '../lib/format';
import { useSession } from '../state/useSession';

export const ContextDecisionSection: React.FC = () => {
  const { state } = useSession();
  const tx = state.transaction;
  const decision = state.decision;

  const amountDisplay = tx ? formatAmount(tx.amount, tx.currency) : '₹25,00,000';
  const beneficiaryDisplay = tx?.beneficiary ?? 'Apex Industrial Suppliers Ltd';
  const noveltyDisplay = tx?.beneficiary_novelty ?? 'NEW';

  return (
    <NarrativeSection
      index="06"
      title="A DETECTOR ISN'T ENOUGH."
      subtitle="An acoustic classifier only measures spectral signals. Symphony fuses acoustic evidence with transaction stakes and caller context to make a defensible security decision."
      tag="MULTI-FACTOR FUSION"
    >
      <div className="space-y-6">
        {/* The Multi-Factor Fusion Equation */}
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-7 items-center font-mono">
          {/* Factor 1: Voice Evidence */}
          <div className="rounded-xl border border-border/80 bg-surface/90 p-4 lg:col-span-2">
            <div className="flex items-center gap-2 text-micro-label text-fg-tertiary uppercase pb-2 border-b border-border/50">
              <span className="h-1.5 w-1.5 rounded-full bg-accent" />
              <span>VOICE EVIDENCE</span>
            </div>
            <p className="mt-2 text-technical-value font-bold text-fg">L3 Expert Fused Output</p>
            <p className="mt-1 text-micro-label text-fg-secondary">
              P(inauth) = {decision ? decision.risk.risk_score.toFixed(3) : '0.860'}
            </p>
            <p className="mt-0.5 text-micro-label text-fg-tertiary">Acoustic, Waveform &amp; Speaker Cosine</p>
          </div>

          <div className="flex justify-center text-fg-tertiary lg:col-span-0">
            <Plus className="h-5 w-5" />
          </div>

          {/* Factor 2: Call Context */}
          <div className="rounded-xl border border-border/80 bg-surface/90 p-4 lg:col-span-2">
            <div className="flex items-center gap-2 text-micro-label text-fg-tertiary uppercase pb-2 border-b border-border/50">
              <span className="h-1.5 w-1.5 rounded-full bg-sky-400" />
              <span>CALL CONTEXT</span>
            </div>
            <p className="mt-2 text-technical-value font-bold text-fg">Caller Metadata &amp; Signals</p>
            <p className="mt-1 text-micro-label text-fg-secondary">
              CFO (Ananya Sharma) · ENROLLED
            </p>
            <p className="mt-0.5 text-micro-label text-fg-tertiary">Inbound PSTN · Urgency &amp; Secrecy Flags</p>
          </div>

          <div className="flex justify-center text-fg-tertiary lg:col-span-0">
            <Plus className="h-5 w-5" />
          </div>

          {/* Factor 3: Transaction Context */}
          <div className="rounded-xl border border-border/80 bg-surface/90 p-4 lg:col-span-2">
            <div className="flex items-center gap-2 text-micro-label text-fg-tertiary uppercase pb-2 border-b border-border/50">
              <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
              <span>TRANSACTION CONTEXT</span>
            </div>
            <p className="mt-2 text-technical-value font-bold text-fg">{amountDisplay}</p>
            <p className="mt-1 text-micro-label text-fg-secondary truncate">
              {beneficiaryDisplay}
            </p>
            <p className="mt-0.5 text-micro-label text-fg-tertiary">Beneficiary Novelty: {noveltyDisplay}</p>
          </div>
        </div>

        {/* Equals Resulting Decision Directive */}
        <div className="rounded-2xl border border-accent/40 bg-accent/10 p-5 backdrop-blur-sm">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <span className="font-mono text-micro-label uppercase tracking-widest text-accent font-bold">
                DEFENSIBLE DECISION RESULT
              </span>
              <p className="mt-1 text-lg font-bold text-fg">
                High stakes + High acoustic risk + Unverified payee = <span className="text-accent">MANDATED HOLD &amp; STEP-UP</span>
              </p>
              <p className="mt-1 text-xs text-fg-secondary">
                A benign check might pass low amounts, but ₹25,00,000 to an unverified beneficiary triggers hard out-of-band verification.
              </p>
            </div>

            <div className="shrink-0 rounded-xl border border-accent/50 bg-surface px-4 py-2 text-center font-mono">
              <span className="text-micro-label text-fg-tertiary uppercase block">MANDATED ACTION</span>
              <span className="text-base font-bold text-accent">{decision?.action ?? 'HOLD'}</span>
            </div>
          </div>
        </div>
      </div>
    </NarrativeSection>
  );
};

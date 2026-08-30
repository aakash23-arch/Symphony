import React from 'react';
import { formatAmount } from '../lib/format';
import { useSession } from '../state/useSession';

export const ContextDecisionSection: React.FC = () => {
  const { state } = useSession();
  const tx = state.transaction;
  const decision = state.decision;

  const amountDisplay = tx ? formatAmount(tx.amount, tx.currency) : '₹25,00,000';
  const beneficiaryDisplay = tx?.beneficiary ?? 'Nexus Holdings Offshore Ltd';
  const noveltyDisplay = tx?.beneficiary_novelty ?? 'NEW';

  return (
    <section id="context" className="py-16 sm:py-24 border-b border-border">
      <div className="max-w-[1500px] mx-auto px-4 sm:px-8">
        {/* Section Header */}
        <div className="flex items-center justify-between border-b border-border pb-4 font-mono text-micro-label uppercase text-fg-tertiary">
          <span>06 // MULTI-FACTOR SYNTHESIS</span>
          <span>VOICE + CONTEXT + TRANSACTION</span>
        </div>

        {/* Giant Editorial Headline */}
        <div className="mt-8 sm:mt-12 mb-12 sm:mb-16">
          <h2 className="display-giant text-fg font-black tracking-tight leading-[0.94]">
            A DETECTOR<br />
            <span className="serif-italic font-normal">ISN’T ENOUGH.</span>
          </h2>
          <p className="mt-5 text-lg sm:text-xl text-fg-secondary max-w-2xl font-normal leading-relaxed">
            An acoustic classifier only scores acoustic distortion. Symphony fuses acoustic evidence
            with caller behavior, transfer urgency, and beneficiary novelty into a definitive security action.
          </p>
        </div>

        {/* Multi-Factor Equation Summary */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-8 border-t border-b border-border py-8 mb-12 font-mono">
          <div className="space-y-1">
            <span className="text-micro-label text-fg-tertiary uppercase block">FACTOR 01</span>
            <p className="text-sm sm:text-base font-bold text-fg">VOICE ACOUSTIC EVIDENCE</p>
            <p className="text-xs text-fg-secondary">
              P(inauth) = {decision ? decision.risk.risk_score.toFixed(3) : '0.890'} (High Synthetic Probability)
            </p>
          </div>

          <div className="space-y-1">
            <span className="text-micro-label text-fg-tertiary uppercase block">FACTOR 02</span>
            <p className="text-sm sm:text-base font-bold text-fg">CALL BEHAVIOR &amp; CODEC</p>
            <p className="text-xs text-fg-secondary">
              PSTN Inbound · Executive Impersonation · Urgency Flag Active
            </p>
          </div>

          <div className="space-y-1">
            <span className="text-micro-label text-fg-tertiary uppercase block">FACTOR 03</span>
            <p className="text-sm sm:text-base font-bold text-amber-600">TRANSACTION NOVELTY</p>
            <p className="text-xs text-fg-secondary">
              {amountDisplay} Wire Transfer · {noveltyDisplay} Beneficiary
            </p>
          </div>
        </div>

        {/* CALL / TRANSACTION STATEMENT LEDGER (Phase 13) */}
        <div className="border border-border bg-surface p-8 sm:p-12 max-w-4xl mx-auto shadow-sm">
          <div className="flex items-center justify-between border-b border-border pb-4 font-mono text-micro-label text-fg-tertiary uppercase">
            <span>CALL &amp; TRANSACTION STATEMENT</span>
            <span>AUDIT DISPATCH RECEIPT</span>
          </div>

          <div className="divide-y divide-border font-mono text-xs sm:text-sm py-4">
            <div className="py-3 flex items-center justify-between">
              <span className="text-fg-tertiary uppercase">CLAIMED CALLER</span>
              <span className="font-bold text-fg">{state.callerRef ?? 'ANANYA SHARMA (CFO)'}</span>
            </div>

            <div className="py-3 flex items-center justify-between">
              <span className="text-fg-tertiary uppercase">TRANSFER REQUEST</span>
              <span className="font-bold text-fg">URGENT WIRE DISBURSEMENT</span>
            </div>

            <div className="py-3 flex items-center justify-between">
              <span className="text-fg-tertiary uppercase">AMOUNT</span>
              <span className="font-bold text-amber-600 text-base">{amountDisplay}</span>
            </div>

            <div className="py-3 flex items-center justify-between">
              <span className="text-fg-tertiary uppercase">BENEFICIARY</span>
              <span className="font-bold text-fg truncate max-w-[240px] sm:max-w-none">
                {beneficiaryDisplay} ({noveltyDisplay})
              </span>
            </div>

            <div className="py-3 flex items-center justify-between">
              <span className="text-fg-tertiary uppercase">CALLBACK STATUS</span>
              <span className="font-bold text-red-600">REFUSED / BYPASS ATTEMPTED</span>
            </div>

            <div className="py-3 flex items-center justify-between">
              <span className="text-fg-tertiary uppercase">VOICE EVIDENCE</span>
              <span className="font-bold text-fg-primary">
                {decision ? `Score ${decision.risk.risk_score.toFixed(2)} (${decision.risk.risk_band})` : 'HIGH ACOUSTIC RISK'}
              </span>
            </div>
          </div>

          {/* Resulting Symphony Decision Directive */}
          <div className="mt-6 pt-6 border-t-2 border-fg flex flex-col sm:flex-row sm:items-center justify-between gap-4 font-mono">
            <div>
              <span className="text-micro-label text-fg-primary uppercase font-bold block">
                MANDATED SYMPHONY POLICY DIRECTIVE
              </span>
              <p className="text-lg sm:text-xl font-black text-fg mt-0.5">
                {decision?.action ?? 'MANDATED HOLD'} (STEP-UP VERIFICATION REQUIRED)
              </p>
            </div>

            <span className="border border-fg bg-fg text-background px-4 py-2 text-xs font-bold uppercase tracking-widest text-center">
              FUNDS FROZEN
            </span>
          </div>
        </div>
      </div>
    </section>
  );
};

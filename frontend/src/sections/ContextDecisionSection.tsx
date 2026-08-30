import React from 'react';
import { formatAmount } from '../lib/format';
import { useSession } from '../state/useSession';
import { Lock } from 'lucide-react';

export const ContextDecisionSection: React.FC = () => {
  const { state } = useSession();
  const tx = state.transaction;
  const decision = state.decision;

  const amountDisplay = tx ? formatAmount(tx.amount, tx.currency) : '₹25,00,000';
  const beneficiaryDisplay = tx?.beneficiary ?? 'Nexus Holdings Offshore Ltd';
  const noveltyDisplay = tx?.beneficiary_novelty ?? 'NEW / UNREGISTERED';

  return (
    <section id="context" className="py-16 sm:py-24 border-b border-border">
      <div className="max-w-[1500px] mx-auto px-4 sm:px-8">
        {/* Section Header */}
        <div className="flex items-center justify-between border-b border-border pb-4 font-mono text-micro-label uppercase text-fg-tertiary">
          <span>04 // MULTI-FACTOR SYNTHESIS</span>
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
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 border-t border-b border-border py-8 mb-12 font-mono">
          <div className="space-y-1.5 border-l border-border pl-4">
            <span className="text-micro-label text-fg-tertiary uppercase block">FACTOR 01 // ACOUSTIC EVIDENCE</span>
            <p className="text-sm sm:text-base font-bold text-fg">NEURAL DISPERSION</p>
            <p className="text-xs text-fg-secondary">
              P(inauth) = {decision ? decision.risk.risk_score.toFixed(3) : '0.890'} (High Synthetic Probability)
            </p>
          </div>

          <div className="space-y-1.5 border-l border-border pl-4">
            <span className="text-micro-label text-fg-tertiary uppercase block">FACTOR 02 // CALL BEHAVIOR</span>
            <p className="text-sm sm:text-base font-bold text-fg">CONTEXT &amp; CODEC</p>
            <p className="text-xs text-fg-secondary">
              PSTN Inbound · Executive Impersonation · Urgency Flag Active
            </p>
          </div>

          <div className="space-y-1.5 border-l border-border pl-4">
            <span className="text-micro-label text-amber-600 uppercase block font-bold">FACTOR 03 // EXPOSURE</span>
            <p className="text-sm sm:text-base font-bold text-amber-600">DISBURSEMENT RISK</p>
            <p className="text-xs text-fg-secondary">
              {amountDisplay} Wire Transfer · {noveltyDisplay} Beneficiary
            </p>
          </div>
        </div>

        {/* INSTITUTIONAL BANK WIRE / TRANSACTION STATEMENT LEDGER */}
        <div className="border-2 border-fg bg-surface p-6 sm:p-10 max-w-4xl mx-auto shadow-md">
          <div className="flex items-center justify-between border-b border-border pb-4 font-mono text-micro-label text-fg-tertiary uppercase">
            <div className="flex items-center gap-2">
              <Lock className="h-3.5 w-3.5 text-fg" />
              <span className="font-bold text-fg">INSTITUTIONAL WIRE VERIFICATION STATEMENT</span>
            </div>
            <span>DISBURSEMENT DISPATCH REF #84920-IN</span>
          </div>

          <div className="divide-y divide-border font-mono text-xs sm:text-sm py-4">
            <div className="py-3 flex items-center justify-between">
              <span className="text-fg-tertiary uppercase">CLAIMED AUTHORIZER</span>
              <span className="font-bold text-fg">{state.callerRef ?? 'ANANYA SHARMA (CHIEF FINANCIAL OFFICER)'}</span>
            </div>

            <div className="py-3 flex items-center justify-between">
              <span className="text-fg-tertiary uppercase">SOURCE ACCOUNT</span>
              <span className="font-bold text-fg">CORP-TREASURY // **4819 (STATE BANK OF INDIA)</span>
            </div>

            <div className="py-3 flex items-center justify-between">
              <span className="text-fg-tertiary uppercase">TRANSACTION AMOUNT</span>
              <span className="font-bold text-amber-600 text-lg sm:text-xl">{amountDisplay}</span>
            </div>

            <div className="py-3 flex items-center justify-between">
              <span className="text-fg-tertiary uppercase">TARGET BENEFICIARY</span>
              <span className="font-bold text-fg truncate max-w-[220px] sm:max-w-none">
                {beneficiaryDisplay} ({noveltyDisplay})
              </span>
            </div>

            <div className="py-3 flex items-center justify-between">
              <span className="text-fg-tertiary uppercase">OUT-OF-BAND CALLBACK</span>
              <span className="font-bold text-red-600 bg-red-50 px-2 py-0.5 border border-red-200">
                REFUSED / BYPASS ATTEMPTED
              </span>
            </div>

            <div className="py-3 flex items-center justify-between">
              <span className="text-fg-tertiary uppercase">VOICE FORENSIC CONVERGENCE</span>
              <span className="font-bold text-red-600">
                {decision ? `Score ${decision.risk.risk_score.toFixed(2)} (${decision.risk.risk_band})` : 'HIGH SYNTHETIC CLONING RISK'}
              </span>
            </div>
          </div>

          {/* Resulting Symphony Decision Directive */}
          <div className="mt-6 pt-6 border-t-2 border-fg flex flex-col sm:flex-row sm:items-center justify-between gap-4 font-mono">
            <div className="space-y-0.5">
              <span className="text-micro-label text-red-600 uppercase font-bold block">
                MANDATED SYMPHONY POLICY DIRECTIVE
              </span>
              <p className="text-lg sm:text-xl font-black text-fg">
                {decision?.action ?? 'MANDATED HOLD'} (HARD OUT-OF-BAND STEP-UP)
              </p>
            </div>

            <span className="border border-fg bg-fg text-background px-4 py-2.5 text-xs font-bold uppercase tracking-widest text-center shadow-sm">
              FUNDS FROZEN ON LEDGER
            </span>
          </div>
        </div>
      </div>
    </section>
  );
};

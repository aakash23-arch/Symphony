import React from 'react';
import { NarrativeSection } from '../design-system/NarrativeSection';
import { RiskStateTransition } from '../components/storytelling/RiskStateTransition';
import { scoreDisclaimer } from '../lib/risk';

export const PolicyActionSection: React.FC = () => {
  return (
    <NarrativeSection
      index="08"
      title="THE OUTPUT IS AN ACTION."
      subtitle="Detection is useless without deterministic execution. Symphony translates continuous multi-modal threat scores into enforceable policy directives."
      tag="L5 AUTOMATED POLICY"
    >
      <div className="space-y-6">
        <RiskStateTransition />

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

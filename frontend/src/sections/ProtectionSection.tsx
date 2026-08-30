import React from 'react';
import { TransactionInterventionFlow } from '../components/storytelling/TransactionInterventionFlow';

export const ProtectionSection: React.FC = () => {
  return (
    <section id="protection" className="py-16 sm:py-24 border-b border-border">
      <div className="max-w-[1500px] mx-auto px-4 sm:px-8">
        {/* Section Header */}
        <div className="flex items-center justify-between border-b border-border pb-4 font-mono text-micro-label uppercase text-fg-tertiary">
          <span>07 // REAL-TIME INTERVENTION</span>
          <span>PROTECTIVE POLICY DIRECTIVES</span>
        </div>

        {/* Giant Section Headline */}
        <div className="mt-8 sm:mt-12 mb-12 sm:mb-16">
          <h2 className="display-giant text-fg font-black tracking-tight leading-[0.94]">
            CHALLENGE TRUST<br />
            <span className="serif-italic font-normal">BEFORE IT BECOMES A LOSS.</span>
          </h2>
          <p className="mt-5 text-lg sm:text-xl text-fg-secondary max-w-2xl font-normal leading-relaxed">
            When voice authenticity, caller identity, and disbursement novelty diverge,
            Symphony triggers hard out-of-band verification before high-risk funds leave the account.
          </p>
        </div>

        {/* Real-Time Financial Protection Intervention Surface */}
        <div className="border border-border bg-surface p-6 sm:p-10 shadow-sm">
          <TransactionInterventionFlow />
        </div>
      </div>
    </section>
  );
};

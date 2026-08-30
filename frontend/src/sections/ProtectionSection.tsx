import React from 'react';
import { NarrativeSection } from '../design-system/NarrativeSection';
import { TransactionInterventionFlow } from '../components/storytelling/TransactionInterventionFlow';

export const ProtectionSection: React.FC = () => {
  return (
    <NarrativeSection
      index="09"
      title="REAL-TIME TRANSACTION PROTECTION."
      subtitle="Financial loss is prevented before funds leave the building. Automated holds freeze disbursements pending out-of-band verification."
      tag="FINANCIAL DEFENSE"
    >
      <TransactionInterventionFlow />
    </NarrativeSection>
  );
};

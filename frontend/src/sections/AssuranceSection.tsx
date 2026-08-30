import React, { useState } from 'react';
import { NarrativeSection } from '../design-system/NarrativeSection';
import { EvidenceChainAudit } from '../components/storytelling/EvidenceChainAudit';
import { ForensicDossierModal } from '../components/ForensicDossierModal';
import { useSession } from '../state/useSession';

export const AssuranceSection: React.FC = () => {
  const { state, health } = useSession();
  const [showDossier, setShowDossier] = useState(false);

  return (
    <NarrativeSection
      index="10"
      title="EVERY DECISION LEAVES EVIDENCE."
      subtitle="Symphony binds acoustic findings, policy evaluations, and operator interventions into a tamper-evident cryptographic audit chain."
      tag="CRYPTOGRAPHIC ASSURANCE"
    >
      <div className="space-y-6">
        <EvidenceChainAudit onOpenDossier={() => setShowDossier(true)} />

        {showDossier ? (
          <ForensicDossierModal
            state={state}
            health={health}
            onClose={() => setShowDossier(false)}
          />
        ) : null}
      </div>
    </NarrativeSection>
  );
};

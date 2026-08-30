import React from 'react';
import { NarrativeSection } from '../design-system/NarrativeSection';
import { ForensicExpertMatrix } from '../components/storytelling/ForensicExpertMatrix';

export const ForensicLayerSection: React.FC = () => {
  return (
    <div id="forensics">
      <NarrativeSection
        index="04"
        title="ONE SIGNAL. MULTIPLE QUESTIONS."
        subtitle="A single audio turn is analyzed simultaneously across six orthogonal neural forensic dimensions."
        tag="L3 EXPERT ENSEMBLE"
      >
        <div className="space-y-6">
          <ForensicExpertMatrix />

          {/* Runtime Model Availability Inventory Notice */}
          <div className="rounded-xl border border-border/70 bg-surface-elevated/40 p-3.5 flex flex-wrap items-center justify-between gap-3 font-mono text-micro-label text-fg-tertiary">
            <span>
              MODEL INVENTORY SOURCE: <strong className="text-fg">/health &amp; /evidence contracts</strong>
            </span>
            <span>ENSEMBLE REQUIRES AT LEAST ONE LIVE ACOUSTIC EXPERT</span>
          </div>
        </div>
      </NarrativeSection>
    </div>
  );
};

import React from 'react';
import { NarrativeSection } from '../design-system/NarrativeSection';
import { DecisionPipelineFlow } from '../components/storytelling/DecisionPipelineFlow';
import { PipelineArchitectureFlow } from '../components/visualizations/PipelineArchitectureFlow';

export const PipelineSection: React.FC = () => {
  return (
    <div id="pipeline">
      <NarrativeSection
        index="03"
        title="THE FIVE-LAYER SYMPHONY PIPELINE."
        subtitle="From raw audio ingestion to auditable decision assurance, each architectural stage enforces strict separation of concerns."
        tag="SYSTEM ARCHITECTURE"
      >
        <div className="space-y-8">
          <DecisionPipelineFlow />
          <PipelineArchitectureFlow />
        </div>
      </NarrativeSection>
    </div>
  );
};

import React from 'react';
import { NarrativeSection } from '../design-system/NarrativeSection';
import { EditorialBeliefTrajectory } from '../components/storytelling/EditorialBeliefTrajectory';

export const BeliefTrajectorySection: React.FC = () => {
  return (
    <NarrativeSection
      index="05"
      title="THE SIGNAL IS IN THE PATTERN."
      subtitle="A single isolated frame cannot prove impersonation. Symphony tracks the temporal belief trajectory as evidence accumulates over time."
      tag="TEMPORAL CONVERGENCE"
    >
      <EditorialBeliefTrajectory />
    </NarrativeSection>
  );
};

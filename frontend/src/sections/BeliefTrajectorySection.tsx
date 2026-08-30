import React from 'react';
import { ArrowRight } from 'lucide-react';
import { EditorialBeliefTrajectory } from '../components/storytelling/EditorialBeliefTrajectory';

export const BeliefTrajectorySection: React.FC = () => {
  return (
    <section id="pattern" className="py-16 sm:py-24 border-b border-border">
      <div className="max-w-[1500px] mx-auto px-4 sm:px-8">
        {/* Section Header */}
        <div className="flex items-center justify-between border-b border-border pb-4 font-mono text-micro-label uppercase text-fg-tertiary">
          <span>05 // TEMPORAL EVIDENCE ACCUMULATION</span>
          <span>BAYESIAN BELIEF TRAJECTORY</span>
        </div>

        {/* Giant Editorial Statement */}
        <div className="mt-8 sm:mt-12 mb-12 sm:mb-16">
          <h2 className="display-giant text-fg font-black tracking-tight leading-[0.94]">
            THE SIGNAL IS IN<br />
            <span className="serif-italic font-normal">THE PATTERN.</span>
          </h2>
          <p className="mt-5 text-lg sm:text-xl text-fg-secondary max-w-2xl font-normal leading-relaxed">
            A single isolated frame cannot prove impersonation. Symphony tracks the temporal belief
            trajectory (P_spoof) across conversational time to observe asymptotic convergence.
          </p>
        </div>

        {/* Temporal Accumulation Narrative Ribbon */}
        <div className="flex flex-wrap items-center justify-between gap-4 border-t border-b border-border py-4 mb-10 font-mono text-xs text-fg-secondary uppercase">
          <span className="text-fg-tertiary">0.0s // NOMINAL BASELINE</span>
          <ArrowRight className="h-3.5 w-3.5 text-border-strong hidden sm:block" />
          <span className="text-fg-tertiary">0.8s // SPECTRAL ANOMALY</span>
          <ArrowRight className="h-3.5 w-3.5 text-border-strong hidden sm:block" />
          <span className="text-amber-600 font-bold">1.6s // EVIDENCE ACCUMULATION</span>
          <ArrowRight className="h-3.5 w-3.5 text-border-strong hidden sm:block" />
          <span className="text-fg-primary font-bold">2.4s // CONVERGED SPOOF BELIEF</span>
        </div>

        {/* Belief Trajectory Graph Surface */}
        <div className="border border-border bg-surface p-6 sm:p-10 shadow-sm">
          <EditorialBeliefTrajectory />
        </div>
      </div>
    </section>
  );
};

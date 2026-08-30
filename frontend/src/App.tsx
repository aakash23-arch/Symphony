import React, { useState } from 'react';

import { ScrollProgress } from './design-system/ScrollProgress';
import { HeaderBar } from './panels/HeaderBar';
import {
  HeroSection,
  ProblemSection,
  RawSignalSection,
  PipelineSection,
  ForensicLayerSection,
  BeliefTrajectorySection,
  SignalTransitionSection,
  ContextDecisionSection,
  ProtectionSection,
  AssuranceSection,
  LiveDetectionSection,
  TechnicalArchitectureSection,
  FaqSection,
  ClosingSection,
  NarrativeFooter,
} from './sections';
import { SessionProvider } from './state/SessionProvider';

/**
 * Symphony — SignalIQ Visual Reconstruction & Operational Testing Suite.
 *
 * Provides:
 *  - Narrative Mode: High-impact editorial storytelling landing experience
 *  - Console Mode: Dedicated full-screen operational testing & scenario terminal
 */
const Dashboard: React.FC = () => {
  const [viewMode, setViewMode] = useState<'narrative' | 'console'>('narrative');

  return (
    <div className="flex min-h-screen flex-col bg-background text-fg selection:bg-fg selection:text-background">
      <ScrollProgress />
      <HeaderBar viewMode={viewMode} onToggleView={setViewMode} />

      <main className="flex-1 w-full mx-auto">
        {viewMode === 'narrative' ? (
          <>
            <HeroSection onScrollToLive={() => setViewMode('console')} />
            <ProblemSection />
            <RawSignalSection />
            <PipelineSection />
            <ForensicLayerSection />
            <BeliefTrajectorySection />
            <SignalTransitionSection />
            <ContextDecisionSection />
            <ProtectionSection />
            <AssuranceSection />
            <LiveDetectionSection />
            <TechnicalArchitectureSection />
            <FaqSection />
            <ClosingSection />
          </>
        ) : (
          <div className="max-w-[1500px] mx-auto px-4 sm:px-8 py-8 space-y-8">
            <LiveDetectionSection />
          </div>
        )}
      </main>

      <NarrativeFooter />
    </div>
  );
};

export const App: React.FC = () => (
  <SessionProvider>
    <Dashboard />
  </SessionProvider>
);

import React, { useState } from 'react';

import { ScrollProgress } from './design-system/ScrollProgress';
import { HeaderBar } from './panels/HeaderBar';
import { ConsoleView } from './panels/ConsoleView';
import { Interactive3DBackground } from './components/3d';
import {
  HeroSection,
  ProblemSection,
  RawSignalSection,
  HowItWorksSection,
  ContextDecisionSection,
  ProtectionSection,
  LiveDetectionSection,
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
    <div className="flex min-h-screen flex-col bg-background text-fg selection:bg-fg selection:text-background relative">
      <Interactive3DBackground visible={viewMode === 'narrative'} />
      <ScrollProgress />
      <HeaderBar viewMode={viewMode} onToggleView={setViewMode} />

      <main className="flex-1 w-full mx-auto">
        {viewMode === 'narrative' ? (
          <>
            <HeroSection onScrollToLive={() => setViewMode('console')} />
            <ProblemSection />
            <RawSignalSection />
            <HowItWorksSection />
            <ContextDecisionSection />
            <ProtectionSection />
            <LiveDetectionSection />
            <FaqSection />
            <ClosingSection />
          </>
        ) : (
          <ConsoleView />
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

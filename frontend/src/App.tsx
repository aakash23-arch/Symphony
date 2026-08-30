import React from 'react';

import { ErrorState } from './components/PanelStates';
import { CallPanel } from './panels/CallPanel';
import { DemoControl } from './panels/DemoControl';
import { EvidencePanel } from './panels/EvidencePanel';
import { HeaderBar } from './panels/HeaderBar';
import { RecommendationPanel } from './panels/RecommendationPanel';
import { RiskPanel } from './panels/RiskPanel';
import { TimelinePanel } from './panels/TimelinePanel';
import { TransactionPanel } from './panels/TransactionPanel';
import { SessionProvider } from './state/SessionProvider';
import { useSession } from './state/useSession';

/**
 * Editorial Dashboard Layout.
 *
 * Storytelling Flow:
 *  - Section 00: Scenario Matrix & Live Audio Ingress
 *  - Section 01: Intake & Context (Call & Transaction)
 *  - Section 02: Composite Risk & Policy Directives (Risk & Recommendation)
 *  - Section 03: Forensic Evidence & Neural Scorecard (Evidence & Dossier)
 *  - Section 04: Forensic Event History (Timeline)
 *
 * Column order preserves strict accessibility and mobile priority:
 * Risk & Recommendation come first in DOM order so operators see decisions first on small screens.
 */
const Dashboard: React.FC = () => {
  const { state } = useSession();

  return (
    <div className="flex min-h-screen flex-col bg-background text-fg selection:bg-accent/30 selection:text-white">
      <HeaderBar />

      <main className="flex-1 space-y-6 px-4 py-6 sm:px-6 lg:px-8 max-w-[1600px] w-full mx-auto">
        <DemoControl />

        {state.error ? (
          <div className="rounded-2xl border border-red-500/40 bg-red-500/10 p-4 shadow-lg shadow-red-500/5">
            <ErrorState code={state.error.code} message={state.error.message} />
          </div>
        ) : null}

        {/* 3-Column Editorial Grid */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-12 items-start">
          {/* Decision & Intelligence Column: Leads in DOM order for mobile operators */}
          <div className="order-1 space-y-6 lg:order-2 lg:col-span-6">
            <RiskPanel />
            <RecommendationPanel />
            <EvidencePanel />
          </div>

          {/* Context & Telemetry Column */}
          <div className="order-2 space-y-6 lg:order-1 lg:col-span-3">
            <CallPanel />
            <TransactionPanel />
          </div>

          {/* Event History Ledger Column */}
          <div className="order-3 lg:order-3 lg:col-span-3">
            <TimelinePanel />
          </div>
        </div>
      </main>

      <footer className="border-t border-border/80 bg-surface/90 px-6 py-3.5 backdrop-blur-sm mt-8">
        <div className="max-w-[1600px] mx-auto flex flex-wrap items-center justify-between gap-2">
          <p className="font-mono text-micro uppercase tracking-wider text-fg-tertiary">
            Raw audio is confined to the ingestion boundary — no PCM is exposed through this interface.
          </p>
          <p className="font-mono text-micro text-fg-tertiary">
            Symphony VoiceShield Defense Architecture
          </p>
        </div>
      </footer>
    </div>
  );
};

export const App: React.FC = () => (
  <SessionProvider>
    <Dashboard />
  </SessionProvider>
);


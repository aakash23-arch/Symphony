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
 * Dashboard layout.
 *
 * Column order matters on small screens: Risk and Recommendation come first
 * because they are the decision. Call and Transaction are the context for it,
 * and Timeline is the history — useful, but never the thing an operator needs
 * in the first two seconds.
 */
const Dashboard: React.FC = () => {
  const { state } = useSession();

  return (
    <div className="flex min-h-screen flex-col bg-background text-fg">
      <HeaderBar />

      <main className="flex-1 space-y-5 px-5 py-5 lg:px-6">
        <DemoControl />

        {state.error ? (
          <ErrorState code={state.error.code} message={state.error.message} />
        ) : null}

        <div className="grid grid-cols-1 gap-5 lg:grid-cols-12">
          {/* Decision column: first in DOM order so it leads on mobile. */}
          <div className="order-1 space-y-5 lg:order-2 lg:col-span-6">
            <RiskPanel />
            <RecommendationPanel />
            <EvidencePanel />
          </div>

          {/* Context column. */}
          <div className="order-2 space-y-5 lg:order-1 lg:col-span-3">
            <CallPanel />
            <TransactionPanel />
          </div>

          {/* History column. */}
          <div className="order-3 lg:order-3 lg:col-span-3">
            <TimelinePanel />
          </div>
        </div>
      </main>

      <footer className="border-t border-border bg-surface px-6 py-2.5">
        <p className="font-mono text-micro uppercase text-fg-tertiary">
          Raw audio is confined to the ingestion boundary — no PCM is exposed through this
          interface.
        </p>
      </footer>
    </div>
  );
};

export const App: React.FC = () => (
  <SessionProvider>
    <Dashboard />
  </SessionProvider>
);

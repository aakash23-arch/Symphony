import React from 'react';
import { NarrativeSection } from '../design-system/NarrativeSection';
import { DemoControl } from '../panels/DemoControl';
import { CallPanel } from '../panels/CallPanel';
import { TransactionPanel } from '../panels/TransactionPanel';
import { RiskPanel } from '../panels/RiskPanel';
import { RecommendationPanel } from '../panels/RecommendationPanel';
import { EvidencePanel } from '../panels/EvidencePanel';
import { TimelinePanel } from '../panels/TimelinePanel';
import { ErrorState } from '../components/PanelStates';
import { useSession } from '../state/useSession';

export const LiveDetectionSection: React.FC = () => {
  const { state } = useSession();

  return (
    <div id="live-console">
      <NarrativeSection
        index="07"
        title="DETECT IT WHILE IT IS HAPPENING."
        subtitle="The operational Symphony Live Console evaluating real-time streaming audio, Bayesian threat belief, and automated policy enforcement."
        tag="LIVE OPERATIONAL CONSOLE"
      >
        <div className="space-y-6">
          {/* Scenario Ingestion Matrix & Mic Controls */}
          <DemoControl />

          {state.error ? (
            <div className="rounded-2xl border border-red-500/40 bg-red-500/10 p-4 shadow-lg shadow-red-500/5">
              <ErrorState code={state.error.code} message={state.error.message} />
            </div>
          ) : null}

          {/* 3-Column Live Dashboard Grid */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-12 items-start">
            {/* Decision & Forensic Intelligence Column */}
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

            {/* Event Audit Ledger Column */}
            <div className="order-3 lg:order-3 lg:col-span-3">
              <TimelinePanel />
            </div>
          </div>
        </div>
      </NarrativeSection>
    </div>
  );
};

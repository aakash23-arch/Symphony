import React from 'react';
import { NarrativeSection } from '../design-system/NarrativeSection';
import { SignalVisualizer } from '../components/storytelling/SignalVisualizer';
import { DemoControl } from '../panels/DemoControl';
import { CallPanel } from '../panels/CallPanel';
import { TransactionPanel } from '../panels/TransactionPanel';
import { RiskPanel } from '../panels/RiskPanel';
import { RecommendationPanel } from '../panels/RecommendationPanel';
import { EvidencePanel } from '../panels/EvidencePanel';
import { TimelinePanel } from '../panels/TimelinePanel';
import { ErrorState } from '../components/PanelStates';
import { bandLabel, bandTokens, formatScore } from '../lib/risk';
import { NONE } from '../lib/format';
import { useSession } from '../state/useSession';
import { cn } from '../lib/cn';

export const LiveDetectionSection: React.FC = () => {
  const { state } = useSession();
  const isStreaming = Boolean(state.sessionId && state.sourceType);
  const decision = state.decision;
  const risk = decision?.risk;
  const band = risk ? bandTokens[risk.risk_band] : null;

  return (
    <div id="live-detection" className="space-y-8 pt-8">
      <NarrativeSection
        index="06"
        title="DETECT IT WHILE IT IS HAPPENING."
        subtitle="This is the real system, not a mockup. Pick a scenario below and watch Symphony evaluate a live call end to end."
        tag="LIVE OPERATIONAL CONSOLE"
      >
        <div className="space-y-6">
          {/* PRIMARY SECURITY STATE HERO STRIP */}
          <div
            className={cn(
              'relative transition-all duration-300 border-y py-8',
              band
                ? `${band.border} bg-surface`
                : 'border-border bg-surface',
            )}
          >
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
              {/* Left State Summary */}
              <div className="space-y-2">
                <div className="flex items-center gap-2.5 font-mono text-micro-label uppercase text-fg-tertiary">
                  <span
                    className={cn(
                      'h-2 w-2 rounded-full',
                      isStreaming
                        ? 'bg-fg-primary animate-pulse-dot'
                        : decision
                        ? 'bg-emerald-600'
                        : 'bg-fg-muted',
                    )}
                  />
                  <span>
                    {isStreaming
                      ? 'IN-PROGRESS REAL-TIME INGESTION'
                      : decision
                      ? 'ANALYSIS COMPLETE // VERDICT CONFIRMED'
                      : 'STANDBY // AWAITING AUDIO INGRESS'}
                  </span>
                  <span className="text-border-strong">/</span>
                  <span className="text-fg-secondary">
                    {state.callerRef ? `CALLER: ${state.callerRef}` : 'TELEPHONY PIPELINE'}
                  </span>
                </div>

                <div className="flex flex-wrap items-baseline gap-4">
                  <h3 className="display-md text-fg tracking-tight">
                    {risk
                      ? bandLabel(risk.risk_band)
                      : isStreaming
                      ? 'EVALUATING SIGNAL...'
                      : 'SYSTEM READY'}
                  </h3>

                  {decision && (
                    <span className="font-mono text-xs font-bold uppercase text-fg-primary bg-surface px-2.5 py-1 border border-border">
                      ACTION: {decision.action}
                    </span>
                  )}
                </div>

                <p className="body text-fg-secondary max-w-2xl text-xs sm:text-sm">
                  {decision
                    ? band?.meaning ?? 'Decision produced by L1–L5 defense engine.'
                    : 'Select a scenario below or initiate a live microphone call to stream audio through the 6 neural forensic models.'}
                </p>
              </div>

              {/* Right Score Numerical Display */}
              <div className="flex items-center gap-6 border-t border-border pt-4 lg:border-t-0 lg:pt-0 lg:border-l lg:pl-8 shrink-0">
                <div>
                  <span className="font-mono text-micro uppercase text-fg-tertiary block">
                    {risk ? risk.score_label : 'COMPOSITE RISK SCALAR'}
                  </span>
                  <p
                    className={cn(
                      'font-mono tnum text-5xl sm:text-6xl font-bold tracking-tight',
                      band ? band.text : 'text-fg-tertiary',
                    )}
                  >
                    {risk ? formatScore(risk.risk_score) : NONE}
                  </p>
                  <span className="font-mono text-[0.625rem] text-fg-tertiary block mt-1">
                    SCALE 0.00 — 1.00 (UNCALIBRATED)
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Scenario Ingestion Matrix & Mic Controls */}
          <DemoControl />

          {/* Live Signal Telemetry Visualizer */}
          <SignalVisualizer />

          {state.error ? (
            <div className="border border-red-500 bg-surface p-4 text-red-600">
              <ErrorState code={state.error.code} message={state.error.message} />
            </div>
          ) : null}

          {/* Responsive Command-Center Layout Grid */}
          {/* On Mobile: 1. Risk, 2. Evidence, 3. Recommendation, 4. Call, 5. Transaction, 6. Timeline */}
          {/* On Tablet: 2-column */}
          {/* On Desktop: 3-column command center */}
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-12 items-start">
            {/* Column 1 (Decision & Recommendation): Desktop col-span-4 */}
            <div className="space-y-6 md:col-span-1 lg:col-span-4 order-1 md:order-1 lg:order-1">
              <RiskPanel />
              <RecommendationPanel />
            </div>

            {/* Column 2 (Forensic Evidence): Desktop col-span-5 */}
            <div className="space-y-6 md:col-span-1 lg:col-span-5 order-2 md:order-2 lg:order-2">
              <EvidencePanel />
            </div>

            {/* Column 3 (Context & Timeline): Desktop col-span-3 */}
            <div className="space-y-6 md:col-span-2 lg:col-span-3 order-3 md:order-3 lg:order-3">
              <CallPanel />
              <TransactionPanel />
              <TimelinePanel />
            </div>
          </div>
        </div>
      </NarrativeSection>
    </div>
  );
};

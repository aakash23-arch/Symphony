import React from 'react';
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
    <section id="live-detection" className="w-full bg-background pt-12 pb-24">
      <div className="font-mono text-micro-label uppercase tracking-widest text-fg-tertiary mb-12">
        <span>06 // LIVE DETECTION CONSOLE</span>
      </div>

      <div className="space-y-8">
        {/* PRIMARY SECURITY STATE HERO STRIP */}
        <div
          className={cn(
            'relative transition-all duration-300 border-y py-8',
            band
              ? `${band.border} bg-surface`
              : 'border-border bg-surface',
          )}
        >
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 px-4 sm:px-8">
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
              </div>
            </div>
          </div>
        </div>

        <div className="px-4 sm:px-8 space-y-8">
          {/* Scenario Ingestion Matrix & Mic Controls */}
          <DemoControl />

          {/* Live Signal Telemetry Visualizer */}
          <SignalVisualizer />

          {state.error && (
            <div className="border border-red-500 bg-surface p-4 text-red-600">
              <ErrorState code={state.error.code} message={state.error.message} />
            </div>
          )}

          {/* Responsive Command-Center Layout Grid */}
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-12 items-start">
            {/* Column 1 (Decision & Recommendation) */}
            <div className="space-y-6 md:col-span-1 lg:col-span-4 order-1 md:order-1 lg:order-1">
              <RiskPanel />
              <RecommendationPanel />
            </div>

            {/* Column 2 (Forensic Evidence) */}
            <div className="space-y-6 md:col-span-1 lg:col-span-5 order-2 md:order-2 lg:order-2">
              <EvidencePanel />
            </div>

            {/* Column 3 (Context & Timeline) */}
            <div className="space-y-6 md:col-span-2 lg:col-span-3 order-3 md:order-3 lg:order-3">
              <CallPanel />
              <TransactionPanel />
              <TimelinePanel />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};


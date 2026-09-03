import React from 'react';
import { SignalVisualizer } from '../components/storytelling/SignalVisualizer';
import { DemoControl } from '../panels/DemoControl';
import { ErrorState } from '../components/PanelStates';
import { bandLabel, bandTokens, formatUnit } from '../lib/risk';
import { useSession } from '../state/useSession';
import { cn } from '../lib/cn';
import { motion, AnimatePresence } from 'framer-motion';
import { MagneticButton } from '../design-system/MagneticButton';
import { EvidencePanel } from '../panels/EvidencePanel';
import { RiskPanel } from '../panels/RiskPanel';
import { TransactionPanel } from '../panels/TransactionPanel';
import type { TimelineEntry } from '../types/contracts';

export const LiveDetectionSection: React.FC = () => {
  const { state, reset, audioPlaying } = useSession();
  const [activeTab, setActiveTab] = React.useState<'overview' | 'dossier'>('overview');
  
  const isStreaming = Boolean(state.sessionId && state.sourceType);
  const decision = state.decision;
  const risk = decision?.risk;
  const band = risk ? bandTokens[risk.risk_band] : null;
  const liveBelief = state.beliefLive;

  // Real live timeline entries from session state
  const timelineEntries = (state.timeline || []).slice(-6);

  // Active models & live forensic metrics
  const activeExpertCount = state.evidence?.experts.filter(e => e.status === 'OK').length ?? (isStreaming ? 1 : 0);
  const liveConfidence = liveBelief?.confidence ?? risk?.risk_confidence ?? null;
  const liveSpoofProb = liveBelief?.P_spoof ?? (risk?.risk_score ?? null);

  return (
    <section id="live-detection" className="w-full min-h-screen bg-background pb-24 relative overflow-hidden">
      
      {/* Instrumentation Room Grid Background */}
      <div className="absolute inset-0 pointer-events-none opacity-5 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:40px_40px]" />

      <div className="max-w-[1400px] mx-auto px-4 sm:px-6 pt-12 lg:pt-16 space-y-12 relative z-10">
        
        {/* Scenario Selection Matrix Header */}
        <DemoControl />

        {/* Live Audio Ingestion & Telemetry Section */}
        <AnimatePresence mode="wait">
          {isStreaming && (
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              className="space-y-8"
            >
              {/* Top Readout Indicators (100% Bound to Live Telemetry) */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 font-mono text-micro-label uppercase">
                <div className="border border-border p-4 bg-surface shadow-sm">
                  <div className="text-fg-tertiary mb-2">SIGNAL STREAM</div>
                  <div className="text-fg font-bold flex items-center gap-2">
                    {isStreaming && (audioPlaying || state.isAnalyzing) && (
                      <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                    )}
                    {isStreaming
                      ? audioPlaying || state.isAnalyzing
                        ? 'ACTIVE STREAMING'
                        : 'STREAM COMPLETE'
                      : 'OFFLINE'}
                  </div>
                </div>

                <div className="border border-border p-4 bg-surface shadow-sm">
                  <div className="text-fg-tertiary mb-2">NEURAL EXPERTS</div>
                  <div className="text-fg font-bold">
                    {activeExpertCount > 0 ? `${activeExpertCount} ACTIVE` : 'ANALYSING'}
                  </div>
                </div>

                <div className="border border-border p-4 bg-surface shadow-sm">
                  <div className="text-fg-tertiary mb-2">EVIDENCE CONFIDENCE</div>
                  <div className="text-fg font-bold">
                    {liveConfidence !== null ? `${Math.round(liveConfidence * 100)}%` : 'COMPUTING'}
                  </div>
                </div>

                <div className="border border-border p-4 bg-surface shadow-sm">
                  <div className="text-fg-tertiary mb-2">INFERRED RISK</div>
                  <div className={cn("font-bold", band?.text || 'text-fg')}>
                    {risk ? bandLabel(risk.risk_band) : (liveBelief?.band ?? 'EVALUATING')}
                  </div>
                </div>
              </div>

              {/* View Selector Tabs */}
              <div className="flex items-center gap-2 border-b border-border pb-2">
                <button
                  type="button"
                  onClick={() => setActiveTab('overview')}
                  className={cn(
                    "px-4 py-2 font-mono text-xs font-bold uppercase transition-all border",
                    activeTab === 'overview'
                      ? "border-fg bg-fg text-background"
                      : "border-transparent text-fg-secondary hover:border-border hover:bg-surface"
                  )}
                >
                  Live Spectrogram & Signal Flow
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab('dossier')}
                  className={cn(
                    "px-4 py-2 font-mono text-xs font-bold uppercase transition-all border",
                    activeTab === 'dossier'
                      ? "border-fg bg-fg text-background"
                      : "border-transparent text-fg-secondary hover:border-border hover:bg-surface"
                  )}
                >
                  Full Forensic Dossier & Policy Matrix
                </button>
              </div>

              {activeTab === 'overview' ? (
                <>
                  {/* Real-time Spectrogram & Signal Processing Visualizer with live frames and result */}
                  <div className="border border-border bg-surface p-6 shadow-sm">
                    <SignalVisualizer />
                  </div>

                  {/* Real-time Evidence Stream & Live Decision Card */}
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                    {/* Live Event Stream from Analysis Loop */}
                    <div className="border border-border bg-surface p-6 font-mono text-xs shadow-sm">
                      <div className="text-fg-tertiary uppercase mb-4 tracking-widest border-b border-border pb-3 flex justify-between items-center">
                        <span>LIVE AUDIT TIMELINE</span>
                        <span className="text-micro text-fg-secondary">{timelineEntries.length} EVENTS</span>
                      </div>
                      <div className="space-y-3 max-h-[280px] overflow-y-auto">
                        {timelineEntries.length > 0 ? (
                          timelineEntries.map((ev: TimelineEntry, i: number) => (
                            <div key={i} className="flex gap-3 items-start border-b border-border/40 pb-2">
                              <span className="text-fg-tertiary shrink-0 font-bold">[{ev.kind}]</span>
                              <span className="text-fg-secondary">{ev.label} — {ev.detail || 'Processed'}</span>
                            </div>
                          ))
                        ) : (
                          <div className="text-fg-tertiary py-8 text-center italic">
                            Streaming audio into forensic neural pipeline...
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Independent Pipeline Decision Card */}
                    <div className="border border-border bg-surface p-6 flex flex-col justify-between shadow-sm">
                      <div>
                        <div className="text-fg-tertiary uppercase mb-4 tracking-widest border-b border-border pb-3 font-mono text-xs">
                          INFERRED POLICY VERDICT
                        </div>
                        {decision ? (
                          <div className="space-y-4">
                            <div className={cn("text-3xl font-black uppercase tracking-wider", band?.text)}>
                              {bandLabel(risk?.risk_band || 'LOW')}
                            </div>
                            <div className="font-mono text-xs text-fg-secondary space-y-1">
                              <div>POLICY ACTION: <strong className="text-fg font-bold">{decision.action}</strong></div>
                              <div>MATCHED RULE: <span className="text-fg-tertiary">{decision.matched_policy || 'Standard Baseline'}</span></div>
                              {liveSpoofProb !== null && (
                                <div>P(SPOOF): <strong className="text-fg font-mono">{formatUnit(liveSpoofProb)}</strong></div>
                              )}
                            </div>
                            <p className="text-xs text-fg-secondary mt-2 border-t border-border pt-3">
                              {decision.reason_codes?.length
                                ? `Policy rule [${decision.matched_policy}] evaluated: ${decision.reason_codes.join(', ')}.`
                                : `Inference complete. Forensic signals processed with ${decision.action} action enforcement.`}
                            </p>
                          </div>
                        ) : (
                          <div className="py-12 text-center text-fg-tertiary font-mono text-xs">
                            <span className="inline-block animate-pulse">Running PyTorch neural acoustic inference...</span>
                          </div>
                        )}
                      </div>

                      <div className="mt-6 pt-4 border-t border-border flex items-center justify-end gap-3">
                        <MagneticButton 
                          onClick={() => setActiveTab('dossier')} 
                          className="border border-border bg-surface px-4 py-2 font-mono text-micro-label uppercase font-bold text-fg hover:bg-border/50"
                        >
                          OPEN DOSSIER
                        </MagneticButton>
                        <MagneticButton 
                          onClick={reset} 
                          className="border border-fg bg-fg px-4 py-2 font-mono text-micro-label uppercase font-bold text-background hover:bg-fg/90"
                        >
                          RESET / TEST ANOTHER
                        </MagneticButton>
                      </div>
                    </div>
                  </div>
                </>
              ) : (
                /* Full Production Forensic & Risk Panels */
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                  <EvidencePanel />
                  <div className="space-y-8">
                    <RiskPanel />
                    <TransactionPanel />
                  </div>
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        {state.error && (
          <div className="border border-red-500 bg-surface p-4 text-red-600 font-mono text-sm max-w-2xl mx-auto mt-8">
            <ErrorState code={state.error.code} message={state.error.message} />
            <button onClick={reset} className="mt-4 border border-red-500 px-3 py-1 hover:bg-red-50 font-bold">
              TRY AGAIN
            </button>
          </div>
        )}

      </div>
    </section>
  );
};

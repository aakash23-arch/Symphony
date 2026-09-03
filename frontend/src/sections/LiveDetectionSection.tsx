import React, { useState, useRef, useEffect } from 'react';
import {
  PhoneCall,
  ShieldCheck,
  Building2,
  Languages,
  FileCheck,
  RotateCcw,
  Volume2,
  VolumeX,
  Play,
  Square,
  Activity,
  Layers,
} from 'lucide-react';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, ReferenceLine, Tooltip } from 'recharts';

import { useSession } from '../state/useSession';
import { cn } from '../lib/cn';
import { bandLabel, bandTokens, formatUnit } from '../lib/risk';
import { formatClock, formatDuration } from '../lib/format';
import { isTerminal } from '../state/sessionReducer';
import type { TimelineEntry } from '../types/contracts';

import { RiskGauge } from '../components/RiskGauge';
import { PipelineFlow } from '../components/PipelineFlow';
import { EvidenceCards } from '../components/EvidenceCards';
import { SignalVisualizer } from '../components/storytelling/SignalVisualizer';
import { DemoControl, MANDATED_SCENARIOS } from '../panels/DemoControl';
import { EvidencePanel } from '../panels/EvidencePanel';
import { RiskPanel } from '../panels/RiskPanel';
import { TransactionPanel } from '../panels/TransactionPanel';
import { ErrorState, Spinner } from '../components/PanelStates';
import { ForensicDossierModal } from '../components/ForensicDossierModal';

export const LiveDetectionSection: React.FC = () => {
  const {
    state,
    health,
    reset,
    startDemo,
    stopSession,
    busy,
    audioPlaying,
    audioMuted,
    toggleMute,
    audioCurrentTime,
    audioDuration,
  } = useSession();

  const sectionRef = useRef<HTMLElement>(null);
  const [activeTab, setActiveTab] = useState<'visualizer' | 'dossier' | 'matrix'>('visualizer');
  const [showDossierModal, setShowDossierModal] = useState(false);
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>(MANDATED_SCENARIOS[0].id);

  const isStreaming = Boolean(state.sessionId && state.sourceType);
  const isCurrentlyActive = audioPlaying || state.isAnalyzing;
  const isComplete = Boolean(state.sessionId && !isCurrentlyActive && (state.decision || isTerminal(state)));
  const decision = state.decision;
  const risk = decision?.risk;
  const liveBelief = state.beliefLive;

  const currentScenario =
    MANDATED_SCENARIOS.find((s) => s.id === (state.scenarioId || selectedScenarioId)) ||
    MANDATED_SCENARIOS[0];

  // Active risk & decision scores (prefer live streaming belief during active call)
  const score = isCurrentlyActive
    ? (liveBelief?.P_spoof ?? risk?.risk_score ?? null)
    : (risk?.risk_score ?? liveBelief?.P_spoof ?? null);

  // Dynamic band derived directly from live score so title updates instantaneously with oscillation
  const scoreBand = score != null
    ? (score >= 0.75 ? 'CRITICAL' : score >= 0.60 ? 'HIGH' : score >= 0.35 ? 'UNCERTAIN' : 'LOW')
    : null;

  const band = isCurrentlyActive
    ? ((liveBelief?.band as any) || scoreBand || risk?.risk_band || null)
    : (risk?.risk_band ?? (liveBelief?.band as any) ?? scoreBand ?? null);

  const action = decision?.action ?? (band === 'CRITICAL' || band === 'HIGH' ? 'ESCALATE' : band === 'UNCERTAIN' ? 'STEP_UP' : 'ALLOW');
  const confidence = isCurrentlyActive
    ? (liveBelief?.confidence ?? risk?.risk_confidence ?? null)
    : (risk?.risk_confidence ?? liveBelief?.confidence ?? null);

  // Timeline entries (most recent 8)
  const timelineEntries = (state.timeline || []).slice(-8);

  // Live real-time analysis points from streaming WebSocket frames
  const livePoints = (state.liveAnalysisPoints || []).map((p) => ({
    t: Number(p.tEnd.toFixed(1)),
    p_spoof: p.spoofProbability ?? 0,
    confidence: p.confidence ?? 0.8,
  }));

  // Trajectory points from REST evidence
  const restTrajectory = (state.evidence?.belief_trajectory ?? state.belief?.trajectory ?? [])
    .slice(-60)
    .map((p) => ({
      t: Number(p.t.toFixed(1)),
      p_spoof: p.p_spoof,
      confidence: p.confidence,
    }));

  // Trajectory dataset for the line graph
  const chartData =
    livePoints.length > 0
      ? livePoints
      : restTrajectory.length > 0
        ? restTrajectory
        : score !== null
          ? [{ t: 0, p_spoof: score, confidence: confidence ?? 0.8 }]
          : [];

  // High-performance pointer tracking for subtle ambient spotlight
  useEffect(() => {
    const el = sectionRef.current;
    if (!el || typeof window === 'undefined') return;

    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReducedMotion) return;

    let rafId: number | null = null;
    const handlePointerMove = (e: PointerEvent) => {
      if (e.pointerType === 'touch') return;
      if (rafId) cancelAnimationFrame(rafId);
      rafId = requestAnimationFrame(() => {
        const rect = el.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        el.style.setProperty('--mouse-x', `${x}px`);
        el.style.setProperty('--mouse-y', `${y}px`);
      });
    };

    el.addEventListener('pointermove', handlePointerMove, { passive: true });
    return () => {
      el.removeEventListener('pointermove', handlePointerMove);
      if (rafId) cancelAnimationFrame(rafId);
    };
  }, []);

  const handleStartScenario = (scenarioId: string) => {
    setSelectedScenarioId(scenarioId);
    const scen = MANDATED_SCENARIOS.find((s) => s.id === scenarioId) ?? MANDATED_SCENARIOS[0];
    void startDemo({
      fixture: scen.fixture,
      callerRef: scen.callerRef,
      scenarioId: scen.id,
      context: scen.context,
      transaction: scen.transaction,
    });
  };

  return (
    <section
      ref={sectionRef}
      id="live-detection"
      className="w-full min-h-screen bg-background pb-24 relative overflow-hidden transition-colors duration-500"
    >
      {/* Background Instrumentation Grid */}
      <div className="absolute inset-0 pointer-events-none opacity-5 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:40px_40px]" />

      {/* Subtle Mouse-Following Ambient Spotlight Overlay (VoiceShield Aura) */}
      <div
        className="absolute inset-0 pointer-events-none opacity-60 transition-opacity duration-700"
        style={{
          background: `radial-gradient(650px circle at var(--mouse-x, 50%) var(--mouse-y, 50%), rgba(0, 226, 138, 0.035), rgba(10, 10, 10, 0.015) 40%, transparent 75%)`,
        }}
      />

      <div className="max-w-[1400px] mx-auto px-4 sm:px-6 pt-8 lg:pt-12 space-y-6 relative z-10">
        {/* =========================================================================
            1. INCOMING CALL CONTEXT & DEMO CONTROL STRIP
            ========================================================================= */}
        <div className="group relative border border-border/80 bg-white rounded-xl shadow-xs hover:border-fg/20 hover:shadow-md transition-all duration-300 overflow-hidden">
          <div className="p-4 sm:p-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
            {/* Left: Caller Identity & Verification Badges */}
            <div className="flex items-center gap-4 min-w-0">
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-rose-50/80 border border-rose-100 text-fg">
                <PhoneCall className="h-5 w-5" />
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-[0.625rem] uppercase tracking-widest text-fg-tertiary">
                    INCOMING EXECUTIVE CALL
                  </span>
                </div>
                <div className="flex items-center gap-2.5 mt-0.5">
                  <h2 className="text-base font-bold text-fg-primary truncate">
                    {currentScenario.callerName}
                  </h2>
                  <span className="text-xs text-fg-secondary font-mono truncate hidden sm:inline">
                    {state.callerRef || currentScenario.callerRef}
                  </span>
                </div>
                <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                  <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[0.625rem] font-mono font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200/60">
                    <ShieldCheck className="h-3 w-3" />
                    Registered Contact
                  </span>
                  <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[0.625rem] font-mono font-semibold bg-gray-50 text-gray-600 border border-gray-200/60">
                    <Building2 className="h-3 w-3" />
                    Enterprise Voice
                  </span>
                </div>
              </div>
            </div>

            {/* Middle: Language & Code-Switching Detection */}
            <div className="hidden lg:flex flex-col items-center justify-center px-8 border-x border-border/60 text-center">
              <div className="flex items-center gap-1.5 font-mono text-sm font-bold text-fg">
                <Languages className="h-4 w-4 text-fg-secondary" />
                <span>
                  {state.languages.length > 0
                    ? state.languages.join(' / ')
                    : currentScenario.language}
                </span>
              </div>
              <span className="font-mono text-xs text-fg-tertiary mt-0.5">
                {currentScenario.languageDetail}
              </span>
            </div>

            {/* Right: Transaction Context & Live Stream Status */}
            <div className="flex items-center justify-between md:justify-end gap-6 w-full md:w-auto pt-4 md:pt-0 border-t md:border-t-0 border-border/60">
              <div>
                <span className="font-mono text-[0.625rem] uppercase tracking-widest text-fg-tertiary block">
                  TRANSACTION AMOUNT
                </span>
                <div className="font-mono text-xl font-bold text-fg tracking-tight tnum mt-0.5">
                  {currentScenario.transaction?.amount
                    ? `₹ ${Number(currentScenario.transaction.amount).toLocaleString('en-IN')}`
                    : '₹ 25,00,000'}
                </div>
                <span className="font-mono text-xs text-fg-tertiary block truncate max-w-[220px]">
                  Beneficiary:{' '}
                  <strong className="text-fg-secondary font-medium">
                    {currentScenario.transaction?.beneficiary || 'Apex Infrastructure & ...'}
                  </strong>
                </span>
              </div>

              {/* Status Pill */}
              <div className="flex flex-col items-end gap-1.5">
                {isStreaming ? (
                  isComplete ? (
                    <span className="inline-flex items-center gap-1.5 px-3.5 py-1 font-mono text-xs font-bold rounded-full bg-emerald-50 text-emerald-700 border border-emerald-300 shadow-xs">
                      <span className="h-2 w-2 rounded-full bg-emerald-500" />
                      ANALYSIS COMPLETE
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1.5 px-3.5 py-1 font-mono text-xs font-bold rounded-full bg-emerald-50 text-emerald-700 border border-emerald-300 shadow-xs animate-pulse">
                      <span className="h-2 w-2 rounded-full bg-emerald-500" />
                      LIVE / ANALYZING
                    </span>
                  )
                ) : (
                  <span className="inline-flex items-center gap-1.5 px-3.5 py-1 font-mono text-xs font-semibold rounded-full bg-surface-elevated text-fg-tertiary border border-border">
                    IDLE READY
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Quick Demo Switcher & Audio Controls Strip */}
          <div className="bg-surface-subtle/70 px-4 sm:px-6 py-3 border-t border-border/60 flex flex-wrap items-center justify-between gap-3 font-mono text-xs">
            <div className="flex items-center gap-2.5 flex-wrap">
              <span className="text-fg-tertiary text-xs uppercase font-semibold">
                DEMO RECORDINGS:
              </span>
              <div className="flex gap-2 flex-wrap">
                {MANDATED_SCENARIOS.map((scen) => (
                  <button
                    key={scen.id}
                    type="button"
                    disabled={isCurrentlyActive && busy}
                    onClick={() => handleStartScenario(scen.id)}
                    className={cn(
                      'px-3.5 py-1.5 text-xs font-bold uppercase transition-all duration-200 rounded-md flex items-center gap-1.5 border',
                      (state.scenarioId === scen.id || (!state.scenarioId && selectedScenarioId === scen.id))
                        ? 'border-red-500/50 bg-[#111827] text-white shadow-md shadow-red-500/20'
                        : 'border-gray-200 bg-white text-gray-700 hover:border-gray-400 hover:text-fg'
                    )}
                  >
                    <span>DEMO {scen.sectionIndex}</span>
                    <span className="opacity-90">({scen.badge})</span>
                  </button>
                ))}
              </div>
            </div>

            <div className="flex items-center gap-3">
              {audioPlaying && (
                <button
                  type="button"
                  onClick={toggleMute}
                  className="inline-flex items-center gap-1 text-xs font-bold text-emerald-700 hover:text-emerald-800 transition-colors"
                >
                  {audioMuted ? <VolumeX className="h-3.5 w-3.5" /> : <Volume2 className="h-3.5 w-3.5" />}
                  <span>{audioMuted ? 'MUTED' : 'MUTED'}</span>
                </button>
              )}

              {isCurrentlyActive ? (
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void stopSession()}
                  className="inline-flex items-center gap-1.5 px-4 py-1.5 bg-[#DC2626] hover:bg-[#B91C1C] text-white text-xs font-bold rounded-md transition-all shadow-md shadow-red-500/30"
                >
                  {busy ? <Spinner /> : <Square className="h-3 w-3 fill-current" />}
                  STOP CALL
                </button>
              ) : (
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => handleStartScenario(selectedScenarioId)}
                  className="inline-flex items-center gap-1.5 px-4 py-1.5 bg-fg hover:bg-fg/90 text-white text-xs font-bold rounded-md transition-all shadow-md shadow-black/10"
                >
                  {busy ? <Spinner /> : <Play className="h-3 w-3 fill-current" />}
                  PLAY RECORDING
                </button>
              )}

              <button
                type="button"
                onClick={reset}
                className="inline-flex items-center gap-1 px-3 py-1.5 border border-gray-200 bg-white hover:bg-gray-50 text-gray-700 text-xs font-medium rounded-md transition-all"
              >
                <RotateCcw className="h-3 w-3" />
                RESET
              </button>
            </div>
          </div>

          {/* Interactive Live Audio Waveform & Equalizer Playback Bar */}
          {isStreaming && (
            <div className="bg-white border-t border-border/80 px-4 sm:px-6 py-2.5 flex items-center justify-between gap-4 font-mono text-xs">
              <div className="flex items-center gap-3 min-w-0 flex-1">
                <div className="flex items-end gap-1 h-3.5 text-red-500 font-bold shrink-0">
                  <span className={cn("w-0.5 bg-red-500 rounded-full transition-all", isCurrentlyActive ? "h-3 animate-[pulse_0.6s_ease-in-out_infinite]" : "h-1.5")} />
                  <span className={cn("w-0.5 bg-red-500 rounded-full transition-all", isCurrentlyActive ? "h-4 animate-[pulse_0.9s_ease-in-out_infinite_0.1s]" : "h-2")} />
                  <span className={cn("w-0.5 bg-red-500 rounded-full transition-all", isCurrentlyActive ? "h-2.5 animate-[pulse_0.5s_ease-in-out_infinite_0.2s]" : "h-1")} />
                  <span className={cn("w-0.5 bg-red-500 rounded-full transition-all", isCurrentlyActive ? "h-3.5 animate-[pulse_0.75s_ease-in-out_infinite_0.15s]" : "h-2")} />
                  <span className="ml-1.5 text-xs uppercase tracking-wider text-fg-primary font-bold">
                    PCM STREAM INGESTION ACTIVE
                  </span>
                </div>

                {/* Red Progress Track */}
                <div className="relative flex-1 h-2 bg-gray-100 rounded-full overflow-hidden mx-3">
                  <div
                    className="h-full bg-red-600 transition-all duration-150 rounded-full"
                    style={{
                      width: `${audioDuration > 0 ? Math.min(100, (audioCurrentTime / audioDuration) * 100) : (isCurrentlyActive ? 45 : 100)}%`,
                    }}
                  />
                </div>

                <span className="text-xs text-fg-tertiary tnum shrink-0 font-medium">
                  {formatDuration(audioCurrentTime)} / {formatDuration(audioDuration || (currentScenario.fixture.includes('03') ? 29.5 : 32.5))}
                </span>
              </div>
            </div>
          )}
        </div>

        {/* =========================================================================
            2. CENTRAL COMPOSITE RISK GAUGE CARD
            ========================================================================= */}
        <div
          className={cn(
            'group relative border border-border/80 bg-white rounded-xl shadow-xs transition-all duration-500 hover:border-fg/20 hover:shadow-md overflow-hidden',
            isCurrentlyActive && 'ring-1 ring-red-500/20 shadow-[0_0_30px_rgba(220,38,38,0.06)]'
          )}
        >
          <RiskGauge
            score={score}
            band={band}
            label={band ? bandLabel(band, score) : undefined}
            action={action}
            confidence={confidence}
            isEvaluating={isCurrentlyActive && score === null}
            detail={
              isCurrentlyActive
                ? score !== null && score >= 0.60
                  ? 'SYNTHETIC SIGNATURE DETECTED'
                  : 'LIVE ACOUSTIC EVALUATION'
                : band === 'CRITICAL' || band === 'HIGH'
                  ? 'SYNTHETIC SIGNATURE DETECTED'
                  : 'NOMINAL AUTHENTIC VOICE'
            }
          />
        </div>

        {/* =========================================================================
            3. SYSTEM PIPELINE (6-Stage Horizontal Flow)
            ========================================================================= */}
        <div className="rounded-xl border border-border/80 bg-white shadow-xs overflow-hidden">
          <PipelineFlow
            isStreaming={isCurrentlyActive}
            framesPublished={state.framesPublished}
            framesScored={state.framesScored}
            hasEvidence={Boolean(state.evidence)}
            hasDecision={Boolean(state.decision)}
            isComplete={isComplete}
          />
        </div>

        {/* =========================================================================
            4. INDEPENDENT EVIDENCE SOURCE CARDS (Acoustic, Prosody, Speaker, Context)
            ========================================================================= */}
        <EvidenceCards
          experts={state.evidence?.experts ?? []}
          contributions={state.decision?.risk?.contributions ?? []}
          isLoading={isStreaming && !state.evidence}
        />

        {/* =========================================================================
            5. FORENSIC DUAL PANE: RISK TRAJECTORY & LIVE EVENT STREAM
            ========================================================================= */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left: Voice Risk Trajectory Line Chart */}
          <div className="group relative lg:col-span-7 border border-border bg-surface p-5 shadow-[0_1px_3px_rgba(0,0,0,0.02)] hover:border-fg/20 hover:shadow-[0_4px_24px_rgba(0,0,0,0.035)] transition-all duration-300 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between pb-3 border-b border-border/80">
                <div>
                  <span className="font-mono text-micro-label uppercase tracking-widest text-fg-tertiary block">
                    TEMPORAL FORENSIC BELIEF
                  </span>
                  <h3 className="text-sm font-bold text-fg mt-0.5">
                    Voice Risk Trajectory
                  </h3>
                </div>
                <div className="flex items-center gap-3 font-mono text-[0.625rem] text-fg-tertiary">
                  <div className="flex items-center gap-1">
                    <span className="h-2 w-2 rounded-full bg-fg" />
                    <span>P(Spoof)</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <span className="h-0.5 w-3 bg-red-500 inline-block" />
                    <span>Policy Threshold (0.70)</span>
                  </div>
                </div>
              </div>

              {/* Chart Container */}
              <div className="h-56 mt-4 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                    <CartesianGrid stroke="#EBEBEA" strokeDasharray="3 3" vertical={false} />
                    <XAxis
                      dataKey="t"
                      tickFormatter={(v: number) => `${v}s`}
                      stroke="#888888"
                      fontSize={10}
                      fontFamily="monospace"
                      tickLine={false}
                    />
                    <YAxis
                      domain={[0, 1]}
                      ticks={[0, 0.25, 0.5, 0.75, 1.0]}
                      stroke="#888888"
                      fontSize={10}
                      fontFamily="monospace"
                      tickLine={false}
                    />
                    <Tooltip
                      content={({ active, payload }) => {
                        if (active && payload && payload.length) {
                          const data = payload[0].payload;
                          return (
                            <div className="border border-border bg-surface p-2 font-mono text-xs shadow-lg">
                              <div>Time: {data.t}s</div>
                              <div className="font-bold text-fg">
                                P(Spoof): {formatUnit(data.p_spoof)}
                              </div>
                            </div>
                          );
                        }
                        return null;
                      }}
                    />
                    {/* Policy Threshold Reference Line */}
                    <ReferenceLine
                      y={0.70}
                      stroke="#DC2626"
                      strokeDasharray="4 4"
                      strokeWidth={1.5}
                      label={{
                        value: 'THRESHOLD 0.70',
                        position: 'right',
                        fill: '#DC2626',
                        fontSize: 9,
                        fontFamily: 'monospace',
                      }}
                    />
                    <Line
                      type="monotone"
                      dataKey="p_spoof"
                      stroke="#0A0A0A"
                      strokeWidth={2}
                      dot={false}
                      isAnimationActive={false}
                      connectNulls={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="mt-3 pt-3 border-t border-border/60 flex items-center justify-between font-mono text-[0.6875rem] text-fg-tertiary">
              <span>ACCUMULATED FRAMES: {state.framesScored}</span>
              <span>SCALE: 0.00–1.00 UNCALIBRATED</span>
            </div>
          </div>

          {/* Right: Live Event Stream Audit Log */}
          <div className="group relative lg:col-span-5 border border-border bg-surface p-5 shadow-[0_1px_3px_rgba(0,0,0,0.02)] hover:border-fg/20 hover:shadow-[0_4px_24px_rgba(0,0,0,0.035)] transition-all duration-300 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between pb-3 border-b border-border/80">
                <span className="font-mono text-micro-label uppercase tracking-widest text-fg-tertiary">
                  LIVE EVENT STREAM
                </span>
                <span className="font-mono text-[0.625rem] text-fg-secondary">
                  {timelineEntries.length} EVENTS RECORDED
                </span>
              </div>

              <div className="mt-3 space-y-2.5 max-h-[230px] overflow-y-auto pr-1">
                {timelineEntries.length > 0 ? (
                  timelineEntries.map((ev: TimelineEntry, idx: number) => (
                    <div
                      key={ev.seq ?? idx}
                      className="flex items-start gap-2.5 text-xs font-mono border-b border-border/40 pb-2 last:border-0"
                    >
                      <span className="text-fg-tertiary shrink-0 text-[0.6875rem]">
                        [{formatClock(ev.timestamp) || `+${ev.t_offset_s ?? 0}s`}]
                      </span>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-1.5">
                          <span className="font-bold text-fg-primary text-[0.6875rem]">
                            {ev.kind}
                          </span>
                          {ev.risk_band && (
                            <span className={cn('text-[0.625rem] font-bold px-1 rounded', bandTokens[ev.risk_band]?.text)}>
                              {ev.risk_band}
                            </span>
                          )}
                        </div>
                        <p className="text-fg-secondary text-[0.6875rem] truncate mt-0.5">
                          {ev.label} {ev.detail ? `· ${ev.detail}` : ''}
                        </p>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="py-12 text-center text-fg-tertiary font-mono text-xs">
                    <span className="inline-block animate-pulse">
                      Awaiting live acoustic stream telemetry...
                    </span>
                  </div>
                )}
              </div>
            </div>

            <div className="mt-3 pt-3 border-t border-border/60 flex items-center justify-between">
              <span className="font-mono text-[0.6875rem] text-fg-tertiary">
                SHA-256 HASH CHAIN: {state.evidence?.hash_chained ? 'VERIFIED' : 'PENDING'}
              </span>
              <button
                type="button"
                onClick={() => setShowDossierModal(true)}
                className="font-mono text-[0.6875rem] font-bold text-fg hover:underline inline-flex items-center gap-1 transition-colors"
              >
                <FileCheck className="h-3.5 w-3.5" />
                EXPORT DOSSIER
              </button>
            </div>
          </div>
        </div>

        {/* =========================================================================
            6. INTERACTIVE SPECTROGRAM, FULL DOSSIER & SCENARIO MATRIX ACCORDION
            ========================================================================= */}
        <div className="group relative border border-border bg-surface shadow-[0_1px_3px_rgba(0,0,0,0.02)] hover:border-fg/20 hover:shadow-[0_4px_24px_rgba(0,0,0,0.035)] transition-all duration-300">
          {/* Tab Selector Bar */}
          <div className="flex items-center border-b border-border px-4 py-2 gap-2 bg-surface-elevated/40">
            <button
              type="button"
              onClick={() => setActiveTab('visualizer')}
              className={cn(
                'inline-flex items-center gap-1.5 px-3.5 py-1.5 font-mono text-xs font-bold uppercase transition-all duration-200 border',
                activeTab === 'visualizer'
                  ? 'border-fg bg-fg text-background shadow-sm'
                  : 'border-transparent text-fg-secondary hover:border-border hover:bg-surface'
              )}
            >
              <Activity className="h-3.5 w-3.5" />
              Harmonic Spectrogram & Signal Flow
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('dossier')}
              className={cn(
                'inline-flex items-center gap-1.5 px-3.5 py-1.5 font-mono text-xs font-bold uppercase transition-all duration-200 border',
                activeTab === 'dossier'
                  ? 'border-fg bg-fg text-background shadow-sm'
                  : 'border-transparent text-fg-secondary hover:border-border hover:bg-surface'
              )}
            >
              <FileCheck className="h-3.5 w-3.5" />
              Full Forensic Dossier & Policy Matrix
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('matrix')}
              className={cn(
                'inline-flex items-center gap-1.5 px-3.5 py-1.5 font-mono text-xs font-bold uppercase transition-all duration-200 border',
                activeTab === 'matrix'
                  ? 'border-fg bg-fg text-background shadow-sm'
                  : 'border-transparent text-fg-secondary hover:border-border hover:bg-surface'
              )}
            >
              <Layers className="h-3.5 w-3.5" />
              Detailed Scenario Matrix Inspector
            </button>
          </div>

          <div className="p-5 sm:p-6">
            {activeTab === 'visualizer' && (
              <div className="space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-border/80">
                  <div>
                    <span className="font-mono text-micro-label uppercase tracking-widest text-fg-tertiary block">
                      SPECTRAL DENSITY & HARMONIC OSCILLOSCOPE
                    </span>
                    <h3 className="text-sm font-bold text-fg mt-0.5">
                      Real-Time Voice Signal & Progressive Frame Ingestion
                    </h3>
                  </div>
                  <span className="font-mono text-micro text-fg-tertiary">
                    32 FREQUENCY BINS (0–8000 HZ)
                  </span>
                </div>
                <SignalVisualizer />
              </div>
            )}

            {activeTab === 'dossier' && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <EvidencePanel />
                <div className="space-y-8">
                  <RiskPanel />
                  <TransactionPanel />
                </div>
              </div>
            )}

            {activeTab === 'matrix' && (
              <DemoControl />
            )}
          </div>
        </div>

        {/* Global Error Notice */}
        {state.error && (
          <div className="border border-red-500 bg-surface p-4 text-red-600 font-mono text-sm max-w-2xl mx-auto mt-6 shadow-sm">
            <ErrorState code={state.error.code} message={state.error.message} />
            <button
              type="button"
              onClick={reset}
              className="mt-4 border border-red-500 px-3 py-1 hover:bg-red-50 font-bold transition-colors"
            >
              RESET AND RETRY
            </button>
          </div>
        )}
      </div>

      {/* Full-Screen Forensic Dossier Modal */}
      {showDossierModal && (
        <ForensicDossierModal
          state={state}
          health={health}
          onClose={() => setShowDossierModal(false)}
        />
      )}
    </section>
  );
};

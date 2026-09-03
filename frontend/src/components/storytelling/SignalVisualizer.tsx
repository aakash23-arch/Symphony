import React, { useEffect, useRef, useState } from 'react';
import { Activity, CheckCircle2, Radio, Volume2, WifiOff } from 'lucide-react';
import { cn } from '../../lib/cn';
import { actionTokens, bandLabel, bandTokens, formatScore } from '../../lib/risk';
import { useSession } from '../../state/useSession';

export type SignalVisualizerState =
  | 'IDLE'
  | 'LISTENING'
  | 'PROCESSING'
  | 'COMPLETE'
  | 'DISCONNECTED';

export interface SignalVisualizerProps {
  overrideState?: SignalVisualizerState;
  className?: string;
  showTelemetry?: boolean;
}

interface CrestParticle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  alpha: number;
  size: number;
}

/**
 * Editorial Signal Visualizer Component with Fluid Multi-Harmonic Voice Line Animations.
 *
 * Visually communicates VOICE → SIGNAL → INGESTION:
 *  - Canvas-driven high-definition oscilloscope waveform with harmonic formants
 *  - Oscillating laser scan line with glowing phosphor trail
 *  - Glowing particle crest sparks riding the audio wave peaks
 *  - 32-band spectral density equalizer with decaying peak-hold markers
 *  - Pauses render loop when offscreen using IntersectionObserver for battery/CPU efficiency
 */
export const SignalVisualizer: React.FC<SignalVisualizerProps> = ({
  overrideState,
  className,
  showTelemetry = true,
}) => {
  const {
    state,
    audioAnalyserRef,
    audioPlaying,
    audioCurrentTime,
    audioDuration,
  } = useSession();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const animFrameRef = useRef<number | null>(null);
  const [isVisible, setIsVisible] = useState(true);

  // Peak hold state for spectral EQ bars
  const peakHoldRef = useRef<number[]>(new Array(32).fill(0));
  const peakDecayRef = useRef<number[]>(new Array(32).fill(0));

  // Particle sparks on wave peaks
  const particlesRef = useRef<CrestParticle[]>([]);

  // Derive active system state from live session if not overridden.
  const isAudioActive = audioPlaying || state.isAnalyzing;
  const activeState: SignalVisualizerState =
    overrideState ??
    (state.connection === 'failed'
      ? 'DISCONNECTED'
      : isAudioActive
      ? 'PROCESSING'
      : (state.sessionState === 'STOPPED' || state.sessionState === 'FAILED' || !state.isAnalyzing) && state.decision
      ? 'COMPLETE'
      : state.sourceType
      ? 'LISTENING'
      : 'IDLE');

  // Pause canvas when off-screen
  useEffect(() => {
    const el = containerRef.current;
    if (!el || typeof IntersectionObserver === 'undefined') return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        setIsVisible(entry.isIntersecting);
      },
      { threshold: 0.1 },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  // Continuous Waveform & Voice Line Rendering Loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !isVisible) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const prefersReducedMotion =
      typeof window !== 'undefined' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    let phase = 0;
    let scanHead = 0;

    const render = () => {
      const width = canvas.clientWidth;
      const height = canvas.clientHeight;
      if (canvas.width !== width || canvas.height !== height) {
        canvas.width = width;
        canvas.height = height;
      }

      ctx.clearRect(0, 0, width, height);

      // -----------------------------------------------------------------------
      // 1. Subtle Infrastructure Grid & Graduation Ticks
      // -----------------------------------------------------------------------
      ctx.strokeStyle = 'rgba(0, 0, 0, 0.04)';
      ctx.lineWidth = 1;
      const vLines = 8;
      for (let i = 1; i < vLines; i++) {
        const x = (width / vLines) * i;
        ctx.beginPath();
        ctx.setLineDash([2, 4]);
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
        ctx.stroke();
      }

      // Horizontal calibration intervals
      const hLines = 4;
      for (let i = 1; i < hLines; i++) {
        const y = (height / hLines) * i;
        ctx.beginPath();
        ctx.setLineDash([1, 6]);
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
      }
      ctx.setLineDash([]);

      // -----------------------------------------------------------------------
      // 2. Zero-Axis Baseline
      // -----------------------------------------------------------------------
      const midY = height / 2;
      ctx.strokeStyle = 'rgba(0, 0, 0, 0.12)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(0, midY);
      ctx.lineTo(width, midY);
      ctx.stroke();

      // -----------------------------------------------------------------------
      // 3. Multi-Harmonic Waveform Curves
      // -----------------------------------------------------------------------
      const isDynamic = activeState === 'LISTENING' || activeState === 'PROCESSING';
      const points = 200;

      const mainColor =
        activeState === 'PROCESSING'
          ? '#0A0A0A' // Obsidian primary
          : activeState === 'LISTENING'
          ? '#0284C7' // Sky blue
          : activeState === 'COMPLETE'
          ? '#059669' // Emerald green
          : activeState === 'DISCONNECTED'
          ? '#DC2626' // Rose error
          : '#94A3B8'; // Slate idle

      const glowColor =
        activeState === 'PROCESSING'
          ? 'rgba(16, 185, 129, 0.35)' // Emerald glow
          : activeState === 'LISTENING'
          ? 'rgba(2, 132, 199, 0.35)'
          : activeState === 'COMPLETE'
          ? 'rgba(5, 150, 105, 0.4)'
          : 'rgba(0, 0, 0, 0)';

      // Sample live frequency energy from audio/microphone AnalyserNode
      let liveAudioGain = 1.0;
      if (audioAnalyserRef.current) {
        const freqData = new Uint8Array(32);
        audioAnalyserRef.current.getByteFrequencyData(freqData);
        let sum = 0;
        for (let k = 0; k < freqData.length; k++) sum += freqData[k];
        const avg = sum / (freqData.length * 255);
        if (audioPlaying) {
          liveAudioGain = Math.max(0.2, Math.min(1.5, avg * 2.2));
        }
      }

      // Calculate Waveform Coordinates
      const wavePoints: { x: number; y: number; amplitude: number }[] = [];
      for (let i = 0; i <= points; i++) {
        const x = (width / points) * i;
        const norm = (i / points) * Math.PI * 4;
        const envelope = Math.sin((i / points) * Math.PI); // Window tapering

        let amplitude = 0;
        if (activeState === 'PROCESSING') {
          // Complex vocal harmonics: F0 fundamental + F1 formant + F2 resonance + micro-jitter
          const fundamental = Math.sin(norm + phase * 1.2);
          const formant1 = Math.sin(norm * 2.8 - phase * 1.8) * 0.45;
          const formant2 = Math.sin(norm * 5.2 + phase * 2.4) * 0.22;
          const jitter = (Math.random() - 0.5) * 0.08;
          amplitude = (fundamental + formant1 + formant2 + jitter) * envelope * (height * 0.38) * liveAudioGain;
        } else if (activeState === 'LISTENING') {
          // Smooth breathing vocal tone
          const fundamental = Math.sin(norm + phase * 0.7);
          const subHarmonic = Math.sin(norm * 2.1 - phase * 0.5) * 0.25;
          amplitude = (fundamental + subHarmonic) * envelope * (height * 0.2) * liveAudioGain;
        } else if (activeState === 'COMPLETE') {
          // Locked tranquil sine wave
          amplitude = Math.sin(norm * 0.75 + phase * 0.3) * envelope * (height * 0.09);
        } else if (activeState === 'DISCONNECTED') {
          amplitude = (Math.random() - 0.5) * 4;
        }

        wavePoints.push({ x, y: midY + amplitude, amplitude });
      }

      // --- 3A. Translucent Ethereal Secondary Wave (Phase Offset) ---
      if (isDynamic || activeState === 'COMPLETE') {
        ctx.beginPath();
        ctx.strokeStyle =
          activeState === 'PROCESSING'
            ? 'rgba(16, 185, 129, 0.28)'
            : 'rgba(2, 132, 199, 0.2)';
        ctx.lineWidth = 1.5;

        for (let i = 0; i < wavePoints.length; i++) {
          const wp = wavePoints[i];
          const shadowY = midY + (wp.y - midY) * 0.7 + Math.sin(i * 0.2 - phase) * 6;
          if (i === 0) ctx.moveTo(wp.x, shadowY);
          else ctx.lineTo(wp.x, shadowY);
        }
        ctx.stroke();
      }

      // --- 3B. Primary Crisp Voice Signal Line with Glow ---
      ctx.save();
      ctx.beginPath();
      ctx.strokeStyle = mainColor;
      ctx.lineWidth = isDynamic ? 2.5 : 1.5;
      ctx.shadowColor = glowColor;
      ctx.shadowBlur = isDynamic ? 10 : 0;

      for (let i = 0; i < wavePoints.length; i++) {
        const wp = wavePoints[i];
        if (i === 0) ctx.moveTo(wp.x, wp.y);
        else ctx.lineTo(wp.x, wp.y);
      }
      ctx.stroke();
      ctx.restore();

      // --- 3C. Dynamic Gradient Fill Below Waveform ---
      if (isDynamic || activeState === 'COMPLETE') {
        ctx.beginPath();
        ctx.moveTo(wavePoints[0].x, wavePoints[0].y);
        for (let i = 1; i < wavePoints.length; i++) {
          ctx.lineTo(wavePoints[i].x, wavePoints[i].y);
        }
        ctx.lineTo(width, height);
        ctx.lineTo(0, height);
        ctx.closePath();

        const grad = ctx.createLinearGradient(0, midY, 0, height);
        grad.addColorStop(
          0,
          activeState === 'PROCESSING'
            ? 'rgba(16, 185, 129, 0.12)'
            : activeState === 'COMPLETE'
            ? 'rgba(5, 150, 105, 0.1)'
            : 'rgba(2, 132, 199, 0.08)',
        );
        grad.addColorStop(1, 'rgba(0, 0, 0, 0)');
        ctx.fillStyle = grad;
        ctx.fill();
      }

      // -----------------------------------------------------------------------
      // 4. Oscilloscope Scan Head & Phosphor Sweep
      // -----------------------------------------------------------------------
      if (isDynamic) {
        scanHead = (scanHead + width * 0.0035) % width;

        // Laser scan line
        const scanGrad = ctx.createLinearGradient(scanHead - 40, 0, scanHead, 0);
        scanGrad.addColorStop(0, 'rgba(16, 185, 129, 0)');
        scanGrad.addColorStop(1, 'rgba(16, 185, 129, 0.45)');

        ctx.fillStyle = scanGrad;
        ctx.fillRect(scanHead - 40, 0, 40, height);

        ctx.strokeStyle = '#10B981';
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.moveTo(scanHead, 0);
        ctx.lineTo(scanHead, height);
        ctx.stroke();

        // Spawn crest sparks along the scan head
        if (Math.random() > 0.6 && particlesRef.current.length < 24) {
          const nearestPt = wavePoints[Math.floor((scanHead / width) * points)];
          if (nearestPt && Math.abs(nearestPt.amplitude) > 8) {
            particlesRef.current.push({
              x: nearestPt.x,
              y: nearestPt.y,
              vx: (Math.random() - 0.5) * 1.5,
              vy: (Math.random() - 0.5) * 2 - (nearestPt.amplitude > 0 ? 1 : -1),
              alpha: 0.9,
              size: Math.random() * 2.5 + 1.5,
            });
          }
        }
      }

      // -----------------------------------------------------------------------
      // 5. Animate & Render Wave Peak Spark Particles
      // -----------------------------------------------------------------------
      for (let i = particlesRef.current.length - 1; i >= 0; i--) {
        const p = particlesRef.current[i];
        p.x += p.vx;
        p.y += p.vy;
        p.alpha -= 0.025;

        if (p.alpha <= 0) {
          particlesRef.current.splice(i, 1);
          continue;
        }

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(16, 185, 129, ${p.alpha})`;
        ctx.fill();
      }

      // Continuous time advance: runs while audio is playing or visualizer is active
      if (!prefersReducedMotion && (isAudioActive || isDynamic || activeState === 'COMPLETE')) {
        phase += activeState === 'PROCESSING' ? 0.055 : 0.022;
        animFrameRef.current = requestAnimationFrame(render);
      }
    };

    render();

    return () => {
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    };
  }, [activeState, isVisible, isAudioActive, audioPlaying]);

  return (
    <div
      ref={containerRef}
      className={cn(
        'relative overflow-hidden border border-border bg-surface p-5 transition-all shadow-sm',
        className,
      )}
    >
      {/* Telemetry Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border/60 pb-3 font-mono text-micro-label uppercase text-fg-tertiary">
        <div className="flex items-center gap-2">
          {activeState === 'PROCESSING' && (
            <Activity className="h-4 w-4 text-emerald-600 animate-pulse-dot" />
          )}
          {activeState === 'LISTENING' && (
            <Radio className="h-4 w-4 text-sky-500 animate-pulse" />
          )}
          {activeState === 'COMPLETE' && (
            <CheckCircle2 className="h-4 w-4 text-emerald-600" />
          )}
          {activeState === 'DISCONNECTED' && (
            <WifiOff className="h-4 w-4 text-rose-500" />
          )}
          {activeState === 'IDLE' && (
            <Volume2 className="h-4 w-4 text-fg-muted" />
          )}

          <span className="font-bold text-fg">VOICE INTAKE SIGNAL</span>
          <span className="text-border-strong">/</span>
          <span
            className={cn(
              'font-semibold transition-colors duration-200',
              activeState === 'PROCESSING' && 'text-emerald-600 font-bold',
              activeState === 'LISTENING' && 'text-sky-600',
              activeState === 'COMPLETE' && 'text-emerald-600',
              activeState === 'DISCONNECTED' && 'text-rose-600',
              activeState === 'IDLE' && 'text-fg-tertiary',
            )}
          >
            {activeState}
          </span>
        </div>

        {showTelemetry && (
          <div className="flex items-center gap-3">
            {audioPlaying || state.isAnalyzing ? (
              <span className="font-mono text-xs text-emerald-600 font-bold bg-emerald-50 border border-emerald-200 px-2.5 py-0.5 animate-pulse">
                Analyzing {audioCurrentTime.toFixed(1)}s / {(audioDuration || 18.0).toFixed(1)}s
              </span>
            ) : (
              <>
                <span>16.0 kHz PCM</span>
                <span className="text-border-strong">/</span>
                <span>MONO</span>
                <span className="text-border-strong">/</span>
                <span className="text-fg font-bold">16-BIT LINEAR</span>
              </>
            )}
          </div>
        )}
      </div>

      {/* Primary Oscilloscope Surface with Animated Voice Line */}
      <div className="relative mt-4 h-44 sm:h-52 w-full">
        <canvas ref={canvasRef} className="h-full w-full block" />

        {/* Framing Markers */}
        <div className="pointer-events-none absolute inset-0 flex items-end justify-between px-3 pb-2 font-mono text-[0.625rem] text-fg-tertiary">
          <span>t = {audioCurrentTime.toFixed(1)}s</span>
          <span className="hidden sm:inline">25ms FRAME WINDOW (10ms HOP)</span>
          <span>t = {(audioDuration || 18.0).toFixed(1)}s</span>
        </div>
      </div>

      {/* Bottom Spectral Distribution Strip with Dynamic Equalizer */}
      <div className="mt-3.5 border-t border-border/60 pt-3">
        <div className="flex items-center justify-between font-mono text-micro-label text-fg-tertiary mb-1.5">
          <span>SPECTRAL ENERGY DENSITY</span>
          <span>0 Hz — 8000 Hz</span>
        </div>
        <div className="flex items-end gap-1 h-7 w-full">
          {Array.from({ length: 32 }).map((_, i) => {
            let realFreqPct = 0;
            if (audioAnalyserRef.current && audioPlaying) {
              const freqData = new Uint8Array(32);
              audioAnalyserRef.current.getByteFrequencyData(freqData);
              realFreqPct = (freqData[i] / 255) * 100;
            }

            const heightPct =
              realFreqPct > 5
                ? Math.max(12, Math.min(100, realFreqPct))
                : activeState === 'PROCESSING'
                ? Math.max(15, Math.min(100, Math.sin((i / 32) * Math.PI) * 82 + ((i * 13) % 24)))
                : activeState === 'LISTENING'
                ? Math.max(10, Math.sin((i / 32) * Math.PI) * 38 + ((i * 7) % 15))
                : activeState === 'COMPLETE'
                ? 14
                : 4;

            // Decay peak hold
            if (heightPct > peakHoldRef.current[i]) {
              peakHoldRef.current[i] = heightPct;
              peakDecayRef.current[i] = 0;
            } else {
              peakDecayRef.current[i] += 1;
              if (peakDecayRef.current[i] > 10) {
                peakHoldRef.current[i] = Math.max(heightPct, peakHoldRef.current[i] - 1.5);
              }
            }

            return (
              <div
                key={i}
                className="flex-1 bg-surface-elevated overflow-hidden relative"
                style={{ height: '100%' }}
              >
                {/* Peak hold indicator */}
                {activeState === 'PROCESSING' && (
                  <div
                    className="absolute left-0 right-0 h-[2px] bg-emerald-500 transition-all duration-75 z-10"
                    style={{
                      bottom: `${peakHoldRef.current[i]}%`,
                    }}
                  />
                )}

                {/* Primary frequency energy bar */}
                <div
                  className={cn(
                    'w-full transition-all duration-150',
                    activeState === 'PROCESSING'
                      ? i > 24
                        ? 'bg-rose-500/85'
                        : i > 14
                        ? 'bg-amber-500/85'
                        : 'bg-emerald-600/90'
                      : activeState === 'LISTENING'
                      ? 'bg-sky-500/70'
                      : activeState === 'COMPLETE'
                      ? 'bg-emerald-500/60'
                      : 'bg-fg-muted/20',
                  )}
                  style={{
                    height: `${heightPct}%`,
                    marginTop: `${100 - heightPct}%`,
                  }}
                />
              </div>
            );
          })}
        </div>
      </div>

      {/* ----------------------------------------------------------------------- */}
      {/* PROGRESSIVE LIVE ANALYSIS STREAM (Appears as audio evaluates)           */}
      {/* ----------------------------------------------------------------------- */}
      {(state.liveAnalysisPoints.length > 0 || isAudioActive) && (
        <div className="mt-5 border-t border-border pt-4 space-y-3">
          <div className="flex items-center justify-between font-mono text-xs">
            <div className="flex items-center gap-2">
              <span
                className={cn(
                  'h-2 w-2 rounded-full',
                  isAudioActive ? 'bg-emerald-500 animate-pulse' : 'bg-emerald-600',
                )}
              />
              <span className="font-bold uppercase tracking-wider text-fg-primary">
                {isAudioActive ? 'LIVE / ANALYZING' : 'FINAL / ANALYSIS COMPLETE'}
              </span>
            </div>
            <span className="text-micro text-fg-tertiary">
              {state.liveAnalysisPoints.length} FRAMES EVALUATED
            </span>
          </div>

          {/* Chronological Progressive Timeline Stream */}
          <div className="max-h-52 overflow-y-auto border border-border bg-surface-elevated/40 p-2 space-y-1.5 font-mono text-xs text-fg-secondary">
            {state.liveAnalysisPoints.map((pt, idx) => {
              const isLatest = idx === state.liveAnalysisPoints.length - 1;
              const spoofPct =
                pt.spoofProbability !== null && pt.spoofProbability !== undefined
                  ? `${Math.round(pt.spoofProbability * 100)}%`
                  : '—';
              const confPct = `${Math.round(pt.confidence * 100)}%`;
              const tFormatted = `${pt.tEnd.toFixed(2)}s`;

              return (
                <div
                  key={pt.frameId}
                  className={cn(
                    'flex items-center justify-between px-2.5 py-1.5 border transition-all duration-200',
                    isLatest
                      ? 'border-emerald-500/50 bg-emerald-500/10 text-fg-primary shadow-sm'
                      : 'border-border/40 bg-surface/50 text-fg-secondary',
                  )}
                >
                  <div className="flex items-center gap-3">
                    <span className="text-fg-tertiary text-micro font-semibold">{tFormatted}</span>
                    <span className="font-bold text-fg-primary">
                      P(SPOOF){' '}
                      <span
                        className={
                          pt.spoofProbability && pt.spoofProbability > 0.5
                            ? 'text-rose-600'
                            : 'text-emerald-600'
                        }
                      >
                        {spoofPct}
                      </span>
                    </span>
                    <span className="text-fg-tertiary text-micro">CONF {confPct}</span>
                  </div>

                  <div className="flex items-center gap-2">
                    {pt.riskScore !== undefined && (
                      <span className="text-micro text-fg-tertiary">
                        SCALAR {pt.riskScore.toFixed(2)}
                      </span>
                    )}
                    <span
                      className={cn(
                        'px-2 py-0.5 text-[0.625rem] font-bold uppercase border',
                        pt.band === 'LOW'
                          ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-700'
                          : pt.band === 'MEDIUM'
                          ? 'border-amber-500/40 bg-amber-500/10 text-amber-700'
                          : pt.band === 'HIGH' || pt.band === 'CRITICAL'
                          ? 'border-rose-500/50 bg-rose-500/10 text-rose-700'
                          : 'border-purple-500/40 bg-purple-500/10 text-purple-700',
                      )}
                    >
                      {pt.band}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ----------------------------------------------------------------------- */}
      {/* AUTHORITATIVE FINAL RESULT CARD (Appears when audio finishes playing)   */}
      {/* ----------------------------------------------------------------------- */}
      {!isAudioActive && state.decision && (
        <div className="mt-5 border-t border-border pt-4 animate-slide-up">
          <div className="flex items-center justify-between mb-3 font-mono text-xs">
            <span className="font-bold uppercase tracking-widest text-emerald-600 flex items-center gap-1.5">
              <CheckCircle2 className="h-4 w-4" /> FINAL AUTHORITATIVE RESULT
            </span>
            <span className="text-micro text-fg-tertiary">CONFIRMED BY L1–L5 ENGINE</span>
          </div>

          <div
            className={cn(
              'border p-4 transition-all duration-300 bg-surface shadow-sm',
              bandTokens[state.decision.risk.risk_band]?.border ?? 'border-border',
              bandTokens[state.decision.risk.risk_band]?.surface ?? 'bg-surface',
            )}
          >
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-micro uppercase tracking-widest text-fg-tertiary">
                    {state.decision.risk.risk_band === 'LOW'
                      ? 'AUTHENTIC / LOW RISK'
                      : state.decision.risk.risk_band === 'HIGH' || state.decision.risk.risk_band === 'CRITICAL'
                      ? 'AI / VOICE-CLONED ATTACK'
                      : state.decision.risk.risk_band === 'UNCERTAIN'
                      ? 'CHANNEL DEGRADED / UNCERTAIN'
                      : 'ELEVATED ANOMALY'}
                  </span>
                </div>
                <h4 className={cn('text-2xl font-bold tracking-tight mt-0.5', bandTokens[state.decision.risk.risk_band]?.text)}>
                  {bandLabel(state.decision.risk.risk_band)}
                </h4>
                <p className="text-xs text-fg-secondary mt-1">
                  {bandTokens[state.decision.risk.risk_band]?.meaning}
                </p>
              </div>

              <div className="flex items-center gap-4 border-t sm:border-t-0 sm:border-l border-border/60 pt-3 sm:pt-0 sm:pl-4">
                <div className="text-right">
                  <span className="font-mono text-micro text-fg-tertiary block">COMPOSITE RISK SCALAR</span>
                  <span className="font-mono text-3xl font-bold text-fg-primary">
                    {formatScore(state.decision.risk.risk_score)}
                  </span>
                </div>
                <div>
                  <span
                    className={cn(
                      'px-3 py-1.5 font-mono text-xs font-bold uppercase border shadow-sm block text-center',
                      actionTokens[state.decision.action]?.border ?? 'border-border',
                      actionTokens[state.decision.action]?.surface ?? 'bg-surface',
                      actionTokens[state.decision.action]?.text ?? 'text-fg-primary',
                    )}
                  >
                    ACTION: {state.decision.action}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};


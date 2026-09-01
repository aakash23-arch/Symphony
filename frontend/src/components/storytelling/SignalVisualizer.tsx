import React, { useEffect, useRef, useState } from 'react';
import { Activity, CheckCircle2, Radio, Volume2, WifiOff } from 'lucide-react';
import { cn } from '../../lib/cn';
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
  const { state } = useSession();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const animFrameRef = useRef<number | null>(null);
  const [isVisible, setIsVisible] = useState(true);

  // Peak hold state for spectral EQ bars
  const peakHoldRef = useRef<number[]>(new Array(32).fill(0));
  const peakDecayRef = useRef<number[]>(new Array(32).fill(0));

  // Particle sparks on wave peaks
  const particlesRef = useRef<CrestParticle[]>([]);

  // Derive active system state from live session if not overridden
  const activeState: SignalVisualizerState =
    overrideState ??
    (state.connection === 'failed'
      ? 'DISCONNECTED'
      : state.decision
      ? 'COMPLETE'
      : state.sourceType
      ? state.framesSeen > 0
        ? 'PROCESSING'
        : 'LISTENING'
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
          amplitude = (fundamental + formant1 + formant2 + jitter) * envelope * (height * 0.38);
        } else if (activeState === 'LISTENING') {
          // Smooth breathing vocal tone
          const fundamental = Math.sin(norm + phase * 0.7);
          const subHarmonic = Math.sin(norm * 2.1 - phase * 0.5) * 0.25;
          amplitude = (fundamental + subHarmonic) * envelope * (height * 0.2);
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

      // Continuous time advance
      if (!prefersReducedMotion && (isDynamic || activeState === 'COMPLETE')) {
        phase += activeState === 'PROCESSING' ? 0.055 : 0.022;
        animFrameRef.current = requestAnimationFrame(render);
      }
    };

    render();

    return () => {
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    };
  }, [activeState, isVisible]);

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
            <span>16.0 kHz PCM</span>
            <span className="text-border-strong">/</span>
            <span>MONO</span>
            <span className="text-border-strong">/</span>
            <span className="text-fg font-bold">16-BIT LINEAR</span>
          </div>
        )}
      </div>

      {/* Primary Oscilloscope Surface with Animated Voice Line */}
      <div className="relative mt-4 h-44 sm:h-52 w-full">
        <canvas ref={canvasRef} className="h-full w-full block" />

        {/* Framing Markers */}
        <div className="pointer-events-none absolute inset-0 flex items-end justify-between px-3 pb-2 font-mono text-[0.625rem] text-fg-tertiary">
          <span>t = 0.00s</span>
          <span className="hidden sm:inline">25ms FRAME WINDOW (10ms HOP)</span>
          <span>t = 4.00s</span>
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
            const heightPct =
              activeState === 'PROCESSING'
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
    </div>
  );
};

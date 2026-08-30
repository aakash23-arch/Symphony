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

/**
 * Editorial Signal Visualizer Component.
 *
 * Visually communicates VOICE → SIGNAL → INGESTION:
 *  - Supports 5 discrete system states: IDLE, LISTENING, PROCESSING, COMPLETE, DISCONNECTED
 *  - Canvas-driven real-time oscilloscope waveform with spectral harmonics
 *  - Pauses render loop when offscreen using IntersectionObserver for battery/CPU efficiency
 *  - Detects `prefers-reduced-motion` to render a clean static state
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

  // Waveform rendering loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !isVisible) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const prefersReducedMotion =
      typeof window !== 'undefined' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    let phase = 0;

    const render = () => {
      const width = canvas.clientWidth;
      const height = canvas.clientHeight;
      if (canvas.width !== width || canvas.height !== height) {
        canvas.width = width;
        canvas.height = height;
      }

      ctx.clearRect(0, 0, width, height);

      // 1. Draw subtle background grid lines
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.04)';
      ctx.lineWidth = 1;
      const vLines = 8;
      for (let i = 1; i < vLines; i++) {
        const x = (width / vLines) * i;
        ctx.beginPath();
        ctx.setLineDash([2, 4]);
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
        ctx.stroke();
        ctx.setLineDash([]);
      }

      // 2. Center baseline
      const midY = height / 2;
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.12)';
      ctx.beginPath();
      ctx.moveTo(0, midY);
      ctx.lineTo(width, midY);
      ctx.stroke();

      // 3. Render waveform based on state
      const isDynamic = activeState === 'LISTENING' || activeState === 'PROCESSING';
      const points = 160;
      ctx.beginPath();

      const strokeColor =
        activeState === 'PROCESSING'
          ? '#818CF8'
          : activeState === 'LISTENING'
          ? '#38BDF8'
          : activeState === 'COMPLETE'
          ? '#34D399'
          : activeState === 'DISCONNECTED'
          ? '#EF4444'
          : '#64748B';

      ctx.strokeStyle = strokeColor;
      ctx.lineWidth = isDynamic ? 2.5 : 1.5;

      for (let i = 0; i <= points; i++) {
        const x = (width / points) * i;
        const norm = (i / points) * Math.PI * 4;
        const envelope = Math.sin((i / points) * Math.PI);

        let amplitude = 0;
        if (activeState === 'PROCESSING') {
          const fundamental = Math.sin(norm + phase);
          const harmonic = Math.sin(norm * 2.5 - phase * 1.5) * 0.4;
          const jitter = (Math.random() - 0.5) * 0.1;
          amplitude = (fundamental + harmonic + jitter) * envelope * (height * 0.38);
        } else if (activeState === 'LISTENING') {
          const fundamental = Math.sin(norm + phase * 0.5);
          amplitude = fundamental * envelope * (height * 0.18);
        } else if (activeState === 'COMPLETE') {
          amplitude = Math.sin(norm * 0.5) * envelope * (height * 0.08);
        } else if (activeState === 'DISCONNECTED') {
          amplitude = (Math.random() - 0.5) * 4;
        }

        const y = midY + amplitude;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();

      // Draw subtle gradient fill beneath wave
      if (isDynamic || activeState === 'COMPLETE') {
        ctx.lineTo(width, height);
        ctx.lineTo(0, height);
        ctx.closePath();
        const grad = ctx.createLinearGradient(0, midY, 0, height);
        grad.addColorStop(
          0,
          activeState === 'PROCESSING'
            ? 'rgba(99, 102, 241, 0.15)'
            : activeState === 'COMPLETE'
            ? 'rgba(52, 211, 153, 0.12)'
            : 'rgba(56, 189, 248, 0.10)',
        );
        grad.addColorStop(1, 'transparent');
        ctx.fillStyle = grad;
        ctx.fill();
      }

      if (!prefersReducedMotion && isDynamic) {
        phase += activeState === 'PROCESSING' ? 0.06 : 0.02;
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
        'relative overflow-hidden rounded-2xl border border-border/80 bg-surface/95 p-5 shadow-2xl backdrop-blur-md transition-all',
        className,
      )}
    >
      {/* Telemetry Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border/60 pb-3 font-mono text-micro-label uppercase text-fg-tertiary">
        <div className="flex items-center gap-2">
          {activeState === 'PROCESSING' && (
            <Activity className="h-4 w-4 text-accent animate-pulse-dot" />
          )}
          {activeState === 'LISTENING' && (
            <Radio className="h-4 w-4 text-sky-400 animate-pulse" />
          )}
          {activeState === 'COMPLETE' && (
            <CheckCircle2 className="h-4 w-4 text-emerald-400" />
          )}
          {activeState === 'DISCONNECTED' && (
            <WifiOff className="h-4 w-4 text-rose-400" />
          )}
          {activeState === 'IDLE' && (
            <Volume2 className="h-4 w-4 text-fg-muted" />
          )}

          <span className="font-bold text-fg">VOICE INTAKE SIGNAL</span>
          <span className="text-border-strong">/</span>
          <span
            className={cn(
              'font-semibold',
              activeState === 'PROCESSING' && 'text-accent',
              activeState === 'LISTENING' && 'text-sky-400',
              activeState === 'COMPLETE' && 'text-emerald-400',
              activeState === 'DISCONNECTED' && 'text-rose-400',
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
            <span className="text-accent font-bold">16-BIT LINEAR</span>
          </div>
        )}
      </div>

      {/* Primary Oscilloscope Surface */}
      <div className="relative mt-4 h-44 sm:h-52 w-full">
        <canvas ref={canvasRef} className="h-full w-full block" />

        {/* Framing Markers */}
        <div className="pointer-events-none absolute inset-0 flex items-end justify-between px-3 pb-2 font-mono text-[0.625rem] text-fg-tertiary">
          <span>t = 0.00s</span>
          <span className="hidden sm:inline">25ms FRAME WINDOW (10ms HOP)</span>
          <span>t = 4.00s</span>
        </div>
      </div>

      {/* Bottom Spectral Distribution Strip */}
      <div className="mt-3.5 border-t border-border/60 pt-3">
        <div className="flex items-center justify-between font-mono text-micro-label text-fg-tertiary mb-1.5">
          <span>SPECTRAL ENERGY DENSITY</span>
          <span>0 Hz — 8000 Hz</span>
        </div>
        <div className="flex items-end gap-1 h-7 w-full">
          {Array.from({ length: 32 }).map((_, i) => {
            const heightPct =
              activeState === 'PROCESSING'
                ? Math.max(15, Math.min(100, Math.sin((i / 32) * Math.PI) * 80 + ((i * 11) % 25)))
                : activeState === 'LISTENING'
                ? Math.max(10, Math.sin((i / 32) * Math.PI) * 35)
                : activeState === 'COMPLETE'
                ? 12
                : 4;

            return (
              <div
                key={i}
                className="flex-1 rounded-t-sm bg-surface-elevated overflow-hidden"
                style={{ height: '100%' }}
              >
                <div
                  className={cn(
                    'w-full transition-all duration-150',
                    activeState === 'PROCESSING'
                      ? i > 22
                        ? 'bg-rose-500/80'
                        : i > 12
                        ? 'bg-amber-400/80'
                        : 'bg-accent'
                      : activeState === 'LISTENING'
                      ? 'bg-sky-400/60'
                      : activeState === 'COMPLETE'
                      ? 'bg-emerald-400/50'
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

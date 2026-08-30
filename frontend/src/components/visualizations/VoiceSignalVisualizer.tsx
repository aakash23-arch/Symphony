import React, { useEffect, useRef } from 'react';
import { Activity } from 'lucide-react';
import { cn } from '../../lib/cn';

export interface VoiceSignalVisualizerProps {
  isStreaming?: boolean;
  sampleRate?: number;
  channelCount?: number;
  className?: string;
}

/**
 * Technical Voice Signal Visualizer.
 * Communicates the transition from VOICE → SIGNAL → ANALYSIS:
 * - Oscilloscope waveform canvas
 * - Spectrogram-inspired multi-band frequency levels
 * - Frame division markers and technical telemetry timecode
 */
export const VoiceSignalVisualizer: React.FC<VoiceSignalVisualizerProps> = ({
  isStreaming = false,
  sampleRate = 16000,
  channelCount = 1,
  className,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animFrameRef = useRef<number | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let phase = 0;

    const render = () => {
      // Dynamic canvas resolution
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

      // Horizontal division lines
      const hLines = 6;
      for (let i = 1; i < hLines; i++) {
        const y = (height / hLines) * i;
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
      }

      // Vertical timecode frame lines
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

      // 2. Draw Center Equilibrium Axis
      const midY = height / 2;
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.12)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(0, midY);
      ctx.lineTo(width, midY);
      ctx.stroke();

      // 3. Draw Synthetic/Real Waveform Curve
      const points = 180;
      ctx.beginPath();
      ctx.strokeStyle = isStreaming ? '#818CF8' : '#64748B';
      ctx.lineWidth = 2;

      for (let i = 0; i <= points; i++) {
        const x = (width / points) * i;
        const normalizedX = (i / points) * Math.PI * 6;

        // Modulate with speech-like harmonics
        const envelope = Math.sin((i / points) * Math.PI); // Windowing envelope
        const fundamental = Math.sin(normalizedX + phase);
        const harmonic1 = Math.sin(normalizedX * 2.3 - phase * 1.5) * 0.45;
        const harmonic2 = Math.sin(normalizedX * 4.7 + phase * 2.1) * 0.25;
        const jitter = isStreaming ? (Math.random() - 0.5) * 0.08 : 0;

        const amplitude = (fundamental + harmonic1 + harmonic2 + jitter) * envelope * (height * 0.38);
        const y = midY + amplitude;

        if (i === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      }
      ctx.stroke();

      // 4. Draw Spectral Gradient Area beneath curve
      ctx.lineTo(width, height);
      ctx.lineTo(0, height);
      ctx.closePath();
      const grad = ctx.createLinearGradient(0, midY, 0, height);
      grad.addColorStop(0, isStreaming ? 'rgba(99, 102, 241, 0.15)' : 'rgba(100, 116, 139, 0.05)');
      grad.addColorStop(1, 'transparent');
      ctx.fillStyle = grad;
      ctx.fill();

      // Advance animation phase
      phase += isStreaming ? 0.06 : 0.02;
      animFrameRef.current = requestAnimationFrame(render);
    };

    render();

    return () => {
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    };
  }, [isStreaming]);

  return (
    <div
      className={cn(
        'relative overflow-hidden rounded-2xl border border-border/80 bg-surface/90 p-5 shadow-2xl backdrop-blur-md',
        className,
      )}
    >
      {/* Header telemetry tags */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border/60 pb-3 font-mono text-micro-label uppercase text-fg-tertiary">
        <div className="flex items-center gap-2">
          <Activity className={cn('h-4 w-4', isStreaming ? 'text-accent animate-pulse-dot' : 'text-fg-muted')} />
          <span className="font-semibold text-fg">VOICE SIGNAL INTAKE</span>
          <span className="text-border-strong">/</span>
          <span>{isStreaming ? 'STREAMING ACTIVE' : 'TELEMETRY STANDBY'}</span>
        </div>

        <div className="flex items-center gap-3">
          <span>{sampleRate / 1000} kHz PCM</span>
          <span className="text-border-strong">/</span>
          <span>{channelCount === 1 ? 'MONO' : 'STEREO'}</span>
          <span className="text-border-strong">/</span>
          <span className="text-accent font-bold">16-BIT SIGNED</span>
        </div>
      </div>

      {/* Primary Oscilloscope Canvas */}
      <div className="relative mt-4 h-48 sm:h-56 w-full">
        <canvas ref={canvasRef} className="h-full w-full block" />

        {/* Framing & Analysis Markers Overlay */}
        <div className="pointer-events-none absolute inset-0 flex items-end justify-between px-3 pb-2 font-mono text-[0.625rem] text-fg-tertiary">
          <span>t = 0.00s</span>
          <span className="hidden sm:inline">FRAME WINDOW: 25ms (400 SAMPLES)</span>
          <span className="hidden sm:inline">HOP LENGTH: 10ms</span>
          <span>t = 4.00s</span>
        </div>
      </div>

      {/* Bottom Spectral Frequency Energy Strip */}
      <div className="mt-4 border-t border-border/60 pt-3">
        <div className="flex items-center justify-between font-mono text-micro-label text-fg-tertiary mb-2">
          <span>SPECTRAL ENERGY DISTRIBUTION</span>
          <span>0 Hz — 8000 Hz</span>
        </div>
        <div className="flex items-end gap-1 h-8 w-full">
          {Array.from({ length: 32 }).map((_, i) => {
            const heightPct = Math.max(12, Math.min(100, Math.sin((i / 32) * Math.PI) * 85 + ((i * 7) % 25)));
            return (
              <div
                key={i}
                className="flex-1 rounded-t-sm bg-surface-elevated overflow-hidden"
                style={{ height: '100%' }}
              >
                <div
                  className={cn(
                    'w-full transition-all duration-150',
                    isStreaming
                      ? i > 22
                        ? 'bg-rose-500/80'
                        : i > 12
                        ? 'bg-amber-400/80'
                        : 'bg-accent'
                      : 'bg-fg-muted/40',
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

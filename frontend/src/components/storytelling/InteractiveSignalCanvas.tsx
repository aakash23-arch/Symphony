import React, { useEffect, useRef, useState } from 'react';
import { cn } from '../../lib/cn';

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  size: number;
  baseX: number;
  baseY: number;
  alpha: number;
}

export interface InteractiveSignalCanvasProps {
  className?: string;
  height?: number;
}

/**
 * Interactive Signal Canvas with Cursor Tracking & Draggable Waveform Particles.
 *
 * Implements:
 *  1. Mouse/Touch cursor attraction & following particle swarm
 *  2. Drag-to-displace interactive audio waveform physics
 *  3. Dynamic real-time coordinate & frequency telemetry tracking
 */
export const InteractiveSignalCanvas: React.FC<InteractiveSignalCanvasProps> = ({
  className,
  height = 280,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const animFrameRef = useRef<number | null>(null);

  const [cursorPos, setCursorPos] = useState<{ x: number; y: number } | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const dragOffsetRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });
  const mouseRef = useRef<{ x: number; y: number; active: boolean }>({ x: -1000, y: -1000, active: false });

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let width = (canvas.width = canvas.clientWidth * window.devicePixelRatio || 800);
    let h = (canvas.height = height * window.devicePixelRatio || 280);

    const handleResize = () => {
      if (!canvas) return;
      width = canvas.width = canvas.clientWidth * window.devicePixelRatio;
      h = canvas.height = height * window.devicePixelRatio;
    };

    window.addEventListener('resize', handleResize);

    // Initialize 60 acoustic particles
    const particleCount = 50;
    const particles: Particle[] = [];
    for (let i = 0; i < particleCount; i++) {
      const x = Math.random() * width;
      const y = Math.random() * h;
      particles.push({
        x,
        y,
        baseX: x,
        baseY: y,
        vx: (Math.random() - 0.5) * 0.8,
        vy: (Math.random() - 0.5) * 0.8,
        size: Math.random() * 2 + 1,
        alpha: Math.random() * 0.5 + 0.2,
      });
    }

    let phase = 0;

    const render = () => {
      ctx.clearRect(0, 0, width, h);

      const dpr = window.devicePixelRatio || 1;
      const midY = h / 2 + dragOffsetRef.current.y * dpr;

      // 1. Grid Lines
      ctx.strokeStyle = 'rgba(0, 0, 0, 0.04)';
      ctx.lineWidth = 1 * dpr;
      for (let x = 0; x < width; x += 40 * dpr) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, h);
        ctx.stroke();
      }

      // 2. Cursor Proximity Field Ring
      if (mouseRef.current.active) {
        ctx.strokeStyle = 'rgba(10, 10, 10, 0.15)';
        ctx.lineWidth = 1 * dpr;
        ctx.beginPath();
        ctx.arc(mouseRef.current.x * dpr, mouseRef.current.y * dpr, 40 * dpr, 0, Math.PI * 2);
        ctx.stroke();

        ctx.strokeStyle = 'rgba(10, 10, 10, 0.06)';
        ctx.beginPath();
        ctx.arc(mouseRef.current.x * dpr, mouseRef.current.y * dpr, 80 * dpr, 0, Math.PI * 2);
        ctx.stroke();
      }

      // 3. Update & Draw Particles (Magnetic attraction to cursor)
      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];

        // Cursor attraction physics
        if (mouseRef.current.active) {
          const dx = mouseRef.current.x * dpr - p.x;
          const dy = mouseRef.current.y * dpr - p.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 180 * dpr && dist > 10) {
            const force = (180 * dpr - dist) / (180 * dpr);
            p.x += (dx / dist) * force * 2.5 * dpr;
            p.y += (dy / dist) * force * 2.5 * dpr;
          }
        }

        // Ambient Brownian float
        p.x += p.vx * dpr;
        p.y += p.vy * dpr;

        if (p.x < 0) p.x = width;
        if (p.x > width) p.x = 0;
        if (p.y < 0) p.y = h;
        if (p.y > h) p.y = 0;

        ctx.fillStyle = `rgba(10, 10, 10, ${p.alpha})`;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size * dpr, 0, Math.PI * 2);
        ctx.fill();
      }

      // 4. Draw Interactive Voice Waveform
      const points = 160;
      ctx.beginPath();
      ctx.strokeStyle = '#0A0A0A';
      ctx.lineWidth = 2.5 * dpr;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';

      for (let i = 0; i <= points; i++) {
        const x = (width / points) * i;
        const norm = (i / points) * Math.PI * 4;
        const envelope = Math.sin((i / points) * Math.PI);

        let waveDisp =
          (Math.sin(norm + phase) * 0.6 +
            Math.sin(norm * 2.5 - phase * 1.2) * 0.3 +
            Math.sin(norm * 4 + phase * 2) * 0.1) *
          envelope *
          (h * 0.28);

        // Mouse proximity wave displacement
        if (mouseRef.current.active) {
          const mouseNormX = (mouseRef.current.x * dpr) / width;
          const distFromMouse = Math.abs(i / points - mouseNormX);
          if (distFromMouse < 0.25) {
            const mouseEffect = (1 - distFromMouse / 0.25) * Math.sin(phase * 4);
            waveDisp += mouseEffect * 30 * dpr;
          }
        }

        const y = midY + waveDisp;

        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();

      // Subtle gradient beneath waveform
      ctx.lineTo(width, h);
      ctx.lineTo(0, h);
      ctx.closePath();
      const grad = ctx.createLinearGradient(0, midY, 0, h);
      grad.addColorStop(0, 'rgba(10, 10, 10, 0.05)');
      grad.addColorStop(1, 'transparent');
      ctx.fillStyle = grad;
      ctx.fill();

      // Continuous phase increment
      phase += 0.04;
      animFrameRef.current = requestAnimationFrame(render);
    };

    render();

    return () => {
      window.removeEventListener('resize', handleResize);
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    };
  }, [height]);

  // Mouse / Touch Interaction Handlers
  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return;
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    mouseRef.current = { x, y, active: true };
    setCursorPos({ x: Math.round(x), y: Math.round(y) });

    if (isDragging) {
      dragOffsetRef.current = {
        x: dragOffsetRef.current.x,
        y: Math.max(-60, Math.min(60, y - rect.height / 2)),
      };
    }
  };

  const handleMouseEnter = () => {
    mouseRef.current.active = true;
  };

  const handleMouseLeave = () => {
    mouseRef.current.active = false;
    setCursorPos(null);
    setIsDragging(false);
    dragOffsetRef.current = { x: 0, y: 0 };
  };

  const handleMouseDown = () => {
    setIsDragging(true);
  };

  const handleMouseUp = () => {
    setIsDragging(false);
    dragOffsetRef.current = { x: 0, y: 0 };
  };

  return (
    <div
      ref={containerRef}
      onMouseMove={handleMouseMove}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onMouseDown={handleMouseDown}
      onMouseUp={handleMouseUp}
      className={cn(
        'relative overflow-hidden border border-border bg-surface select-none cursor-crosshair transition-all',
        className,
      )}
      style={{ height }}
    >
      {/* Real-Time Cursor Tracking Readout Badge */}
      <div className="pointer-events-none absolute top-3 left-3 z-10 flex items-center gap-3 font-mono text-micro-label uppercase text-fg-tertiary">
        <span className="flex items-center gap-1.5 font-bold text-fg">
          <span className="h-1.5 w-1.5 rounded-full bg-fg animate-pulse-dot" />
          INTERACTIVE SIGNAL APERTURE
        </span>
        <span className="text-border-strong">/</span>
        <span>DRAG TO MODULATE</span>
        {cursorPos && (
          <>
            <span className="text-border-strong">/</span>
            <span className="text-fg font-bold">
              X:{cursorPos.x} Y:{cursorPos.y} · {((cursorPos.x / 400) * 8).toFixed(1)} kHz
            </span>
          </>
        )}
      </div>

      <canvas ref={canvasRef} className="w-full h-full block" />

      {/* Axis markers */}
      <div className="pointer-events-none absolute bottom-2 inset-x-3 flex items-center justify-between font-mono text-[0.625rem] text-fg-tertiary">
        <span>0.00s // 16.0 kHz</span>
        <span className="hidden sm:inline">MAGNETIC PARTICLE SWARM ACTIVE</span>
        <span>4.00s // TELEPHONY PCM</span>
      </div>
    </div>
  );
};

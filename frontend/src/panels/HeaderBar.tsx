import React from 'react';
import { Activity, Radio, Shield } from 'lucide-react';

import { ConnectionDot } from '../components/ConnectionDot';
import { cn } from '../lib/cn';
import { useSession } from '../state/useSession';

/**
 * Editorial Header Bar.
 *
 * Carries the product identity, real-time connection status, backend health telemetry,
 * and the mandated demo environment disclaimer strip.
 */
export const HeaderBar: React.FC = () => {
  const { state, health, healthError, stopSession, reset, busy } = useSession();

  const isStreaming = Boolean(state.sessionId && state.sourceType);

  const scrollTo = (id: string) => {
    const el = document.getElementById(id);
    el?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <header className="sticky top-0 z-40 border-b border-border/80 bg-surface/95 backdrop-blur-md">
      <div className="flex flex-wrap items-center justify-between gap-4 px-4 sm:px-6 lg:px-8 py-3">
        {/* Product Brand & Identity */}
        <div className="flex items-center gap-3.5">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent/15 text-accent ring-1 ring-accent/30 shadow-inner">
            <Shield className="h-5 w-5" aria-hidden="true" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs font-bold tracking-widest text-accent uppercase">
                SYMPHONY
              </span>
              <span className="text-border-strong">/</span>
              <h1 className="text-sm font-bold tracking-tight text-fg">
                VoiceShield
              </h1>
              <span className="rounded bg-accent/10 px-2 py-0.5 font-mono text-[0.625rem] font-medium text-accent ring-1 ring-accent/20">
                L1–L5 ENGINE
              </span>
            </div>
            <p className="font-mono text-[0.6875rem] text-fg-tertiary uppercase tracking-wider">
              REAL-TIME VOICE SECURITY &amp; IMPERSONATION DEFENSE
            </p>
          </div>
        </div>

        {/* Quick Section Navigation Links */}
        <nav className="hidden xl:flex items-center gap-1 font-mono text-micro-label uppercase text-fg-tertiary">
          <button
            type="button"
            onClick={() => scrollTo('hero')}
            className="px-2.5 py-1.5 rounded-lg hover:text-fg hover:bg-surface-elevated transition-colors"
          >
            Overview
          </button>
          <button
            type="button"
            onClick={() => scrollTo('problem')}
            className="px-2.5 py-1.5 rounded-lg hover:text-fg hover:bg-surface-elevated transition-colors"
          >
            Threat
          </button>
          <button
            type="button"
            onClick={() => scrollTo('pipeline')}
            className="px-2.5 py-1.5 rounded-lg hover:text-fg hover:bg-surface-elevated transition-colors"
          >
            Pipeline
          </button>
          <button
            type="button"
            onClick={() => scrollTo('forensics')}
            className="px-2.5 py-1.5 rounded-lg hover:text-fg hover:bg-surface-elevated transition-colors"
          >
            Forensics
          </button>
          <button
            type="button"
            onClick={() => scrollTo('live-console')}
            className="px-3 py-1.5 rounded-lg bg-accent/15 text-accent font-bold hover:bg-accent/25 transition-colors border border-accent/30"
          >
            Live Console
          </button>
          <button
            type="button"
            onClick={() => scrollTo('scenarios')}
            className="px-2.5 py-1.5 rounded-lg hover:text-fg hover:bg-surface-elevated transition-colors"
          >
            Scenarios
          </button>
          <button
            type="button"
            onClick={() => scrollTo('architecture')}
            className="px-2.5 py-1.5 rounded-lg hover:text-fg hover:bg-surface-elevated transition-colors"
          >
            Architecture
          </button>
        </nav>

        {/* Live Diagnostics & Quick Controls */}
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
          {/* Connection Status Indicator */}
          <ConnectionDot connection={state.connection} attempt={state.reconnectAttempt} />

          {/* Session Status Pill */}
          <div className="flex items-center gap-1.5 rounded-md bg-surface-elevated/70 px-2.5 py-1 font-mono text-micro uppercase text-fg-secondary ring-1 ring-border/50">
            <span
              className={cn(
                'h-1.5 w-1.5 rounded-full',
                isStreaming
                  ? 'bg-accent animate-pulse-dot'
                  : state.sessionId
                  ? 'bg-emerald-400'
                  : 'bg-fg-muted',
              )}
            />
            <span>
              {isStreaming ? 'STREAMING' : state.sessionId ? 'SESSION READY' : 'STANDBY'}
            </span>
          </div>

          {/* Backend Health Diagnostics */}
          <div className="hidden sm:flex items-center gap-1.5 font-mono text-micro uppercase tracking-wider text-fg-tertiary">
            <Activity className="h-3.5 w-3.5 text-fg-tertiary" aria-hidden="true" />
            <span>Backend: </span>
            {healthError ? (
              <span className="font-bold text-band-high">unreachable</span>
            ) : health ? (
              <span
                className={
                  health.status === 'healthy'
                    ? 'font-bold text-band-low'
                    : 'font-bold text-band-medium'
                }
              >
                {health.status}
              </span>
            ) : (
              <span className="text-fg-tertiary">checking</span>
            )}
          </div>

          {/* Quick Active Session Reset / Stop */}
          {state.sessionId && (
            <div className="flex items-center gap-1.5">
              {isStreaming ? (
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void stopSession()}
                  className="rounded-lg border border-red-500/40 bg-red-500/10 px-2.5 py-1 font-mono text-micro uppercase font-bold text-red-400 hover:bg-red-500/20 disabled:opacity-50"
                >
                  Stop
                </button>
              ) : (
                <button
                  type="button"
                  onClick={reset}
                  className="rounded-lg border border-border bg-surface-elevated px-2.5 py-1 font-mono text-micro uppercase font-bold text-fg-secondary hover:text-fg"
                >
                  Reset
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Mandatory Demo Environment Banner */}
      <div className="flex items-center justify-between border-t border-amber-500/25 bg-amber-500/[0.08] px-4 sm:px-6 lg:px-8 py-1.5 font-mono text-micro uppercase tracking-wider text-amber-300">
        <p>
          Demo mode — controlled test audio, simulated transaction context. Not a real call and not a
          real banking integration.
        </p>
        <span className="hidden sm:inline-flex items-center gap-1.5 text-[0.625rem] text-amber-400/80">
          <Radio className="h-3 w-3 animate-pulse" />
          <span>SIH26104 DEFENSE SPEC</span>
        </span>
      </div>
    </header>
  );
};


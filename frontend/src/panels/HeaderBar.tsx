import React from 'react';
import { Activity, Radio, Shield, Terminal } from 'lucide-react';

import { ConnectionDot } from '../components/ConnectionDot';
import { useSession } from '../state/useSession';

/**
 * Editorial Header Bar.
 *
 * Carries the product identity, real-time connection status, backend health telemetry,
 * and the mandated demo environment disclaimer strip.
 */
export const HeaderBar: React.FC = () => {
  const { state, health, healthError } = useSession();

  const scrollTo = (id: string) => {
    const el = document.getElementById(id);
    el?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <header className="sticky top-0 z-40 border-b border-border/80 bg-surface/95 backdrop-blur-md">
      <div className="flex flex-wrap items-center justify-between gap-4 px-6 py-3.5">
        {/* Product Brand & Mission */}
        <div className="flex items-center gap-3.5">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent/15 text-accent ring-1 ring-accent/30 shadow-inner">
            <Shield className="h-5 w-5" aria-hidden="true" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-bold tracking-tight text-fg">
                VoiceShield
              </h1>
              <span className="rounded bg-accent/10 px-2 py-0.5 font-mono text-[0.625rem] font-medium text-accent ring-1 ring-accent/20">
                L1–L5 ENGINE
              </span>
            </div>
            <p className="text-xs text-fg-secondary">
              Real-Time Voice Integrity &amp; Impersonation Defense
            </p>
          </div>
        </div>

        {/* Quick Section Navigation Links */}
        <nav className="hidden lg:flex items-center gap-1 font-mono text-micro-label uppercase text-fg-tertiary">
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

        {/* Live System Diagnostics */}
        <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
          <ConnectionDot connection={state.connection} attempt={state.reconnectAttempt} />

          <div className="flex items-center gap-1.5 font-mono text-micro uppercase tracking-wider text-fg-tertiary">
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

          {health ? (
            <div className="flex items-center gap-1.5 rounded-md bg-surface-elevated/70 px-2.5 py-1 font-mono text-micro uppercase text-fg-secondary ring-1 ring-border/50">
              <Terminal className="h-3 w-3 text-fg-tertiary" aria-hidden="true" />
              <span>v{health.version}</span>
              <span className="text-fg-tertiary">·</span>
              <span className="text-fg-tertiary">{health.environment}</span>
            </div>
          ) : null}
        </div>
      </div>

      {/* Mandatory Demo Environment Banner */}
      <div className="flex items-center justify-between border-t border-amber-500/25 bg-amber-500/[0.08] px-6 py-1.5 font-mono text-micro uppercase tracking-wider text-amber-300">
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


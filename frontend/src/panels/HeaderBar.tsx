import React from 'react';
import { Shield } from 'lucide-react';

import { ConnectionDot } from '../components/ConnectionDot';
import { useSession } from '../state/useSession';

/**
 * The header carries the product identity, the live indicator, and the demo
 * disclaimer.
 *
 * The DEMO MODE strip is not decoration. The audio is a controlled fixture and
 * the transaction environment is simulated; without the strip, a screenshot of
 * this dashboard would read as a claim about a real call.
 */
export const HeaderBar: React.FC = () => {
  const { state, health, healthError } = useSession();

  return (
    <header className="border-b border-border bg-surface">
      <div className="flex flex-wrap items-center justify-between gap-4 px-6 py-3.5">
        <div className="flex items-center gap-3">
          <span className="rounded-lg border border-accent/30 bg-accent/10 p-2 text-accent">
            <Shield className="h-5 w-5" aria-hidden />
          </span>
          <div>
            <h1 className="text-base font-semibold leading-tight tracking-tight text-fg">
              VoiceShield
            </h1>
            <p className="text-xs leading-tight text-fg-secondary">
              Real-Time Voice Integrity &amp; Impersonation Defense
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-x-5 gap-y-2">
          <ConnectionDot connection={state.connection} attempt={state.reconnectAttempt} />

          <span className="font-mono text-micro uppercase text-fg-tertiary">
            Backend{' '}
            {healthError ? (
              <span className="text-band-high">unreachable</span>
            ) : health ? (
              <span className={health.status === 'healthy' ? 'text-band-low' : 'text-band-medium'}>
                {health.status}
              </span>
            ) : (
              <span className="text-fg-tertiary">checking</span>
            )}
          </span>

          {health ? (
            <span className="font-mono text-micro uppercase text-fg-tertiary">
              v{health.version} · {health.environment}
            </span>
          ) : null}
        </div>
      </div>

      <p className="border-t border-band-medium/25 bg-band-medium/10 px-6 py-1.5 font-mono text-micro uppercase tracking-wider text-band-medium">
        Demo mode — controlled test audio, simulated transaction context. Not a real call and not a
        real banking integration.
      </p>
    </header>
  );
};

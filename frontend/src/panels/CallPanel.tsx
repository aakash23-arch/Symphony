import React, { useEffect, useState } from 'react';

import { Metric } from '../components/Metric';
import { EmptyState } from '../components/PanelStates';
import { Panel } from '../components/Panel';
import { elapsedSeconds, formatAmount, formatClock, formatDuration } from '../lib/format';
import { isStale } from '../state/sessionReducer';
import { useSession } from '../state/useSession';

/** Ticks once a second while the call runs; freezes at stopped_at. */
function useCallDuration(startedAt: string | null, stoppedAt: string | null): number | null {
  const [seconds, setSeconds] = useState<number | null>(() => elapsedSeconds(startedAt, stoppedAt));

  useEffect(() => {
    setSeconds(elapsedSeconds(startedAt, stoppedAt));
    if (!startedAt || stoppedAt) return;
    const timer = window.setInterval(() => {
      setSeconds(elapsedSeconds(startedAt, null));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [startedAt, stoppedAt]);

  return seconds;
}

export const CallPanel: React.FC = () => {
  const { state } = useSession();
  const duration = useCallDuration(state.startedAt, state.stoppedAt);
  const stale = isStale(state);

  if (!state.sessionId) {
    return (
      <Panel
        title="Call"
        sectionNumber="01"
        tag="L1 Intake"
        subtitle="Telecom & Stream Ingestion"
      >
        <EmptyState message="No active session." hint="Start a demo call to begin monitoring." />
      </Panel>
    );
  }

  const transaction = state.transaction;
  const language =
    state.languages.length > 0
      ? state.languages.join(' → ')
      : state.framesSeen > 0
        ? null
        : null;

  return (
    <Panel
      title="Call"
      sectionNumber="01"
      tag="L1 Intake"
      subtitle="Telecom & Stream Ingestion"
      stale={stale}
      staleLabel={stale ? `Last update ${formatClock(state.lastMessageAt)}` : undefined}
    >
      <dl className="grid grid-cols-2 gap-x-4 gap-y-3.5">
        <Metric
          label="Caller"
          value={transaction?.caller_identity ?? state.callerRef}
          nullLabel="not identified"
          mono={false}
        />
        <Metric
          label="Number"
          value={state.callerRef}
          nullLabel="not supplied"
        />
        <Metric label="Duration" value={formatDuration(duration)} nullLabel="not started" />
        <Metric
          label="Language"
          value={language}
          nullLabel={state.framesSeen > 0 ? 'detecting...' : 'no audio yet'}
        />
        <Metric
          label="Call source"
          value={state.sourceType ? state.sourceType.toUpperCase() : null}
          nullLabel="unknown"
        />
        <Metric
          label="Session state"
          value={state.sessionState}
          nullLabel="unknown"
        />
      </dl>

      {/* Transaction Association Strip */}
      <div className="mt-4 rounded-xl border border-border/80 bg-surface-elevated/40 p-3">
        <div className="flex items-center justify-between">
          <span className="font-mono text-micro uppercase tracking-wider text-fg-tertiary">
            Linked Disbursement Context
          </span>
          <span className="font-mono text-[0.625rem] text-accent">L4 ASSOC</span>
        </div>
        {transaction ? (
          <p className="mt-1.5 text-xs text-fg-secondary">
            <span className="font-mono font-bold tnum text-fg">
              {formatAmount(transaction.amount, transaction.currency)}
            </span>
            {transaction.transaction_type ? ` · ${transaction.transaction_type}` : ''} · payee{' '}
            <span className="font-medium text-fg">{transaction.beneficiary_novelty.toLowerCase()}</span>
          </p>
        ) : (
          <p className="mt-1 text-xs text-fg-tertiary">
            No transaction linked to this call.
          </p>
        )}
      </div>

      {/* Frame Telemetry Counters */}
      <div className="mt-3.5 flex flex-wrap items-center justify-between gap-2 border-t border-border/70 pt-2.5 font-mono text-micro text-fg-tertiary">
        <div className="flex items-center gap-3">
          <span>frames <strong className="text-fg-secondary">{state.framesSeen}</strong></span>
          <span>scored <strong className="text-fg-secondary">{state.framesScored}</strong></span>
        </div>
        {state.framesSkipped > 0 ? (
          <span className="rounded bg-amber-500/10 px-1.5 py-0.5 text-band-medium">
            dropped {state.framesSkipped}
          </span>
        ) : (
          <span className="text-emerald-400/80">0 dropped</span>
        )}
      </div>
    </Panel>
  );
};


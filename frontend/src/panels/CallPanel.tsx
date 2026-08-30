import React, { useEffect, useState } from 'react';

import { Metric } from '../components/Metric';
import { EmptyState } from '../components/PanelStates';
import { Panel } from '../components/Panel';
import { elapsedSeconds, formatAmount, formatDuration } from '../lib/format';
import { isStale } from '../state/sessionReducer';
import { useSession } from '../state/useSession';
import { formatClock } from '../lib/format';

/** Ticks once a second while the call runs; freezes at stopped_at. */
function useCallDuration(startedAt: string | null, stoppedAt: string | null): number | null {
  const [seconds, setSeconds] = useState<number | null>(() => elapsedSeconds(startedAt, stoppedAt));

  useEffect(() => {
    setSeconds(elapsedSeconds(startedAt, stoppedAt));
    // Nothing to tick if the call never started or has already ended.
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
      <Panel title="Call" tag="L1 Session">
        <EmptyState message="No active session." hint="Start a demo call to begin monitoring." />
      </Panel>
    );
  }

  const transaction = state.transaction;
  // Language comes only from frame.processed telemetry, so it is genuinely
  // unknown until the first frame lands - not "en" by default.
  const language =
    state.languages.length > 0
      ? state.languages.join(' → ')
      : state.framesSeen > 0
        ? null
        : null;

  return (
    <Panel
      title="Call"
      tag="L1 Session"
      stale={stale}
      staleLabel={stale ? `Last update ${formatClock(state.lastMessageAt)}` : undefined}
    >
      <dl className="grid grid-cols-2 gap-x-4 gap-y-4">
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
          nullLabel={state.framesSeen > 0 ? 'detecting' : 'no audio yet'}
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

      <div className="mt-4 border-t border-border pt-3">
        <p className="font-mono text-micro uppercase text-fg-tertiary">Transaction context</p>
        {transaction ? (
          <p className="mt-1 text-[0.8125rem] text-fg-secondary">
            <span className="font-mono tnum text-fg">
              {formatAmount(transaction.amount, transaction.currency)}
            </span>
            {transaction.transaction_type ? ` · ${transaction.transaction_type}` : ''} · beneficiary{' '}
            {transaction.beneficiary_novelty.toLowerCase()}
          </p>
        ) : (
          <p className="mt-1 text-[0.8125rem] text-fg-tertiary">
            No transaction linked to this call.
          </p>
        )}
      </div>

      <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 font-mono text-micro text-fg-tertiary">
        <span>frames {state.framesSeen}</span>
        <span>scored {state.framesScored}</span>
        {state.framesSkipped > 0 ? (
          <span className="text-band-medium">dropped {state.framesSkipped}</span>
        ) : null}
      </div>
    </Panel>
  );
};

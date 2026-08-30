import React, { useEffect, useRef } from 'react';
import { AlertCircle } from 'lucide-react';

import { EmptyState } from '../components/PanelStates';
import { Panel } from '../components/Panel';
import { cn } from '../lib/cn';
import { formatClock, formatDuration } from '../lib/format';
import { severityTone } from '../lib/risk';
import { isStale } from '../state/sessionReducer';
import { useSession } from '../state/useSession';

export const TimelinePanel: React.FC = () => {
  const { state } = useSession();
  const scrollRef = useRef<HTMLOListElement>(null);
  const pinnedToTop = useRef(true);
  const stale = isStale(state);

  // Newest first, so the most recent event is the one in view.
  const entries = [...state.timeline].reverse();

  useEffect(() => {
    const node = scrollRef.current;
    if (node && pinnedToTop.current) node.scrollTop = 0;
  }, [entries.length]);

  const onScroll = (): void => {
    const node = scrollRef.current;
    if (node) pinnedToTop.current = node.scrollTop <= 8;
  };

  return (
    <Panel
      title="Timeline"
      sectionNumber="04"
      tag={`${state.timeline.length} events`}
      subtitle="Forensic Event Ledger"
      stale={stale}
      staleLabel={stale ? `Last update ${formatClock(state.lastMessageAt)}` : undefined}
      bodyClassName="flex min-h-0 flex-col"
    >
      {state.seqGapDetected ? (
        <div className="mb-2.5 flex items-center gap-1.5 rounded-lg border border-band-medium/40 bg-band-medium/10 px-2.5 py-1.5 font-mono text-micro uppercase text-band-medium">
          <AlertCircle className="h-3.5 w-3.5 shrink-0" />
          <span>Event gap detected — resyncing from server</span>
        </div>
      ) : null}

      {entries.length === 0 ? (
        <EmptyState
          message="No events yet."
          hint={state.sessionId ? 'Events appear dynamically as the call progresses.' : undefined}
        />
      ) : (
        <ol
          ref={scrollRef}
          onScroll={onScroll}
          className="scroll-slim -mr-2 max-h-[34rem] min-h-0 flex-1 space-y-2.5 overflow-y-auto pr-2"
        >
          {entries.map((entry) => (
            <li
              key={entry.seq}
              className={cn(
                'rounded-lg border border-border/60 bg-surface-elevated/30 p-2.5 border-l-4 transition-all hover:bg-surface-elevated/60',
                severityTone(entry.severity),
              )}
            >
              <div className="flex items-baseline justify-between gap-2">
                <p className="min-w-0 font-semibold text-xs text-fg leading-snug truncate">
                  {entry.label}
                </p>
                <span className="shrink-0 font-mono tnum text-micro text-fg-tertiary">
                  {entry.t_offset_s !== null
                    ? formatDuration(entry.t_offset_s)
                    : formatClock(entry.timestamp)}
                </span>
              </div>
              {entry.detail ? (
                <p className="mt-1 text-[0.75rem] leading-relaxed text-fg-secondary">
                  {entry.detail}
                </p>
              ) : null}
              <div className="mt-1.5 flex items-center justify-between font-mono text-[0.625rem] text-fg-tertiary uppercase">
                <span>{entry.kind.replace(/_/g, ' ').toLowerCase()}</span>
                <span>SEQ #{entry.seq}</span>
              </div>
            </li>
          ))}
        </ol>
      )}

      {state.timeline.length > 0 ? (
        <p className="mt-3 shrink-0 border-t border-border/70 pt-2 font-mono text-micro text-fg-tertiary text-right">
          Newest entries pinned to top
        </p>
      ) : null}
    </Panel>
  );
};


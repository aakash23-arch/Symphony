import React, { useEffect, useRef } from 'react';

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

  // Auto-scroll only when the reader is already at the top. Yanking the view
  // back while someone is reading history is worse than missing an entry.
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
      tag={`${state.timeline.length} events`}
      stale={stale}
      staleLabel={stale ? `Last update ${formatClock(state.lastMessageAt)}` : undefined}
      bodyClassName="flex min-h-0 flex-col"
    >
      {state.seqGapDetected ? (
        <p className="mb-2 rounded border border-band-medium/40 bg-band-medium/10 px-2 py-1 font-mono text-micro uppercase text-band-medium">
          Event gap detected — resyncing from the server
        </p>
      ) : null}

      {entries.length === 0 ? (
        <EmptyState
          message="No events yet."
          hint={state.sessionId ? 'Events appear as the call progresses.' : undefined}
        />
      ) : (
        <ol
          ref={scrollRef}
          onScroll={onScroll}
          className="scroll-slim -mr-2 max-h-[32rem] min-h-0 flex-1 space-y-2 overflow-y-auto pr-2"
        >
          {entries.map((entry) => (
            <li
              key={entry.seq}
              className={cn('border-l-2 pl-3', severityTone(entry.severity))}
            >
              <div className="flex items-baseline justify-between gap-2">
                <p className="min-w-0 text-[0.8125rem] leading-snug text-fg">{entry.label}</p>
                <span className="shrink-0 font-mono tnum text-micro text-fg-tertiary">
                  {entry.t_offset_s !== null
                    ? formatDuration(entry.t_offset_s)
                    : formatClock(entry.timestamp)}
                </span>
              </div>
              {entry.detail ? (
                <p className="mt-0.5 text-xs leading-snug text-fg-secondary">{entry.detail}</p>
              ) : null}
              <p className="mt-0.5 font-mono text-micro uppercase text-fg-tertiary/70">
                {entry.kind.replace(/_/g, ' ').toLowerCase()}
              </p>
            </li>
          ))}
        </ol>
      )}

      {state.timeline.length > 0 ? (
        <p className="mt-2 shrink-0 border-t border-border pt-2 font-mono text-micro text-fg-tertiary">
          Newest first
        </p>
      ) : null}
    </Panel>
  );
};

import React from 'react';
import { cn } from '../lib/cn';
import type { ConnectionState } from '../state/sessionReducer';

interface Tone {
  dot: string;
  text: string;
  label: string;
  animate: boolean;
}

/**
 * Connection tones.
 *
 * `closed_terminal` is grey and reads "Call ended" rather than red: the server
 * closing after a finished session is the normal path, and painting it as an
 * error would train operators to ignore the indicator.
 */
function toneFor(connection: ConnectionState, attempt: number): Tone {
  switch (connection) {
    case 'open':
      return { dot: 'bg-band-low', text: 'text-band-low', label: 'Live', animate: true };
    case 'connecting':
      return { dot: 'bg-accent', text: 'text-accent', label: 'Connecting', animate: true };
    case 'reconnecting':
      return {
        dot: 'bg-band-medium',
        text: 'text-band-medium',
        label: `Reconnecting ${attempt}/8`,
        animate: true,
      };
    case 'closed_terminal':
      return { dot: 'bg-fg-tertiary', text: 'text-fg-tertiary', label: 'Call ended', animate: false };
    case 'failed':
      return { dot: 'bg-band-high', text: 'text-band-high', label: 'Disconnected', animate: false };
    default:
      return { dot: 'bg-fg-tertiary', text: 'text-fg-tertiary', label: 'Idle', animate: false };
  }
}

export const ConnectionDot: React.FC<{ connection: ConnectionState; attempt: number }> = ({
  connection,
  attempt,
}) => {
  const tone = toneFor(connection, attempt);
  return (
    <span
      className="inline-flex items-center gap-2"
      role="status"
      aria-label={`Connection: ${tone.label}`}
      data-testid="connection-status"
    >
      <span
        className={cn('h-1.5 w-1.5 rounded-full', tone.dot, tone.animate && 'animate-pulse-dot')}
        aria-hidden
      />
      <span className={cn('font-mono text-micro uppercase', tone.text)}>{tone.label}</span>
    </span>
  );
};

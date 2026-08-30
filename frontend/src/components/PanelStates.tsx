import React from 'react';
import { AlertTriangle, CircleSlash, Loader2, WifiOff } from 'lucide-react';
import { cn } from '../lib/cn';

/** Skeleton bars while a request is in flight. */
export const LoadingState: React.FC<{ rows?: number }> = ({ rows = 3 }) => (
  <div className="space-y-2.5" role="status" aria-label="Loading">
    {Array.from({ length: rows }).map((_, index) => (
      <div
        key={index}
        className="h-3 animate-pulse rounded bg-surface-elevated"
        style={{ width: `${72 - index * 12}%` }}
      />
    ))}
  </div>
);

/** Request succeeded; there is genuinely nothing to show. */
export const EmptyState: React.FC<{ message: string; hint?: string }> = ({ message, hint }) => (
  <div className="flex flex-col items-start gap-1 py-2">
    <p className="flex items-center gap-2 text-[0.8125rem] text-fg-tertiary">
      <CircleSlash className="h-3.5 w-3.5" aria-hidden />
      {message}
    </p>
    {hint ? <p className="pl-5.5 text-xs text-fg-tertiary/70">{hint}</p> : null}
  </div>
);

/**
 * The backend has explicitly said "not yet" (the /risk 409).
 *
 * Violet and dashed, deliberately matching the UNCERTAIN band rather than the
 * neutral empty state: an absent assessment is a thing the operator must act
 * on, not an absence of news.
 */
export const AwaitingState: React.FC<{
  message: string;
  detail?: string;
  className?: string;
}> = ({ message, detail, className }) => (
  <div
    className={cn(
      'rounded-lg border border-dashed border-band-uncertain/50 bg-band-uncertain/5 px-4 py-3',
      className,
    )}
  >
    <p className="font-mono text-micro uppercase text-band-uncertain">{message}</p>
    {detail ? <p className="mt-1.5 text-[0.8125rem] text-fg-secondary">{detail}</p> : null}
  </div>
);

/** The live feed is gone; whatever is on screen is last-known, not current. */
export const DisconnectedState: React.FC<{ at: string; attempt?: number }> = ({ at, attempt }) => (
  <div className="flex items-start gap-2 rounded-lg border-l-2 border-band-medium bg-band-medium/10 px-3 py-2">
    <WifiOff className="mt-0.5 h-3.5 w-3.5 shrink-0 text-band-medium" aria-hidden />
    <div>
      <p className="text-[0.8125rem] text-band-medium">Live feed lost — showing last known state</p>
      <p className="font-mono text-micro text-fg-tertiary">
        as of {at}
        {attempt ? ` · reconnect attempt ${attempt}/8` : ''}
      </p>
    </div>
  </div>
);

/** A non-retriable failure, with the backend's own code so it is diagnosable. */
export const ErrorState: React.FC<{
  code: string;
  message: string;
  onRetry?: () => void;
}> = ({ code, message, onRetry }) => (
  <div className="rounded-lg border-l-2 border-band-high bg-band-high/10 px-3 py-2.5">
    <p className="flex items-center gap-2 font-mono text-micro uppercase text-band-high">
      <AlertTriangle className="h-3.5 w-3.5" aria-hidden />
      {code}
    </p>
    <p className="mt-1 text-[0.8125rem] text-fg-secondary">{message}</p>
    {onRetry ? (
      <button
        type="button"
        onClick={onRetry}
        className="mt-2 rounded border border-border-strong px-2.5 py-1 text-xs text-fg-secondary transition-colors hover:bg-surface-elevated hover:text-fg"
      >
        Retry
      </button>
    ) : null}
  </div>
);

/** Inline spinner for buttons mid-action. */
export const Spinner: React.FC<{ className?: string }> = ({ className }) => (
  <Loader2 className={cn('h-3.5 w-3.5 animate-spin', className)} aria-hidden />
);

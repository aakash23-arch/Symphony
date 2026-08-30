import React, { useState } from 'react';

import { Badge } from '../components/Badge';
import { Metric } from '../components/Metric';
import { EmptyState, Spinner } from '../components/PanelStates';
import { Panel } from '../components/Panel';
import { cn } from '../lib/cn';
import { formatAmount, formatClock } from '../lib/format';
import { isStale } from '../state/sessionReducer';
import { useSession } from '../state/useSession';
import type { TransactionStateValue } from '../types/contracts';

const stateTone: Record<TransactionStateValue, string> = {
  PENDING: 'text-fg-secondary border-border',
  APPROVED: 'text-band-low border-band-low/45 bg-band-low/10',
  HELD: 'text-band-high border-band-high/55 bg-band-high/12',
  REJECTED: 'text-band-critical border-band-critical-edge bg-band-critical-field/40',
  CANCELLED: 'text-fg-tertiary border-border',
};

export const TransactionPanel: React.FC = () => {
  const { state, holdTransaction, releaseTransaction, busy } = useSession();
  const [verification, setVerification] = useState('');
  const [touched, setTouched] = useState(false);
  const stale = isStale(state);

  const transaction = state.transaction;

  if (!transaction) {
    return (
      <Panel title="Transaction" tag="Demo environment">
        <EmptyState
          message="No transaction linked to this call."
          hint="A demo transaction is created when a scenario starts."
        />
      </Panel>
    );
  }

  const held = transaction.state === 'HELD';
  const terminal = ['APPROVED', 'REJECTED', 'CANCELLED'].includes(transaction.state);
  // The backend requires a non-blank reference; validating here avoids a
  // guaranteed 422 round-trip and explains the requirement in place.
  const verificationValid = verification.trim().length > 0;

  return (
    <Panel
      title="Transaction"
      tag="Demo environment"
      stale={stale}
      staleLabel={stale ? `Last update ${formatClock(state.lastMessageAt)}` : undefined}
    >
      <dl className="grid grid-cols-2 gap-x-4 gap-y-4">
        <Metric
          label="Amount"
          value={formatAmount(transaction.amount, transaction.currency)}
          valueClassName="text-base"
        />
        <Metric label="Beneficiary" value={transaction.beneficiary} mono={false} />
        <Metric
          label="Beneficiary status"
          value={transaction.beneficiary_novelty}
          nullLabel="unknown"
        />
        <div>
          <dt className="font-mono text-micro uppercase text-fg-tertiary">Status</dt>
          <dd className="mt-1">
            <Badge className={stateTone[transaction.state]} title={transaction.hold_reason ?? undefined}>
              <span data-testid="transaction-state">{transaction.state}</span>
            </Badge>
          </dd>
        </div>
      </dl>

      <div className="mt-4 border-t border-border pt-3">
        <p className="font-mono text-micro uppercase text-fg-tertiary">Security action</p>
        {transaction.risk_actions.length > 0 ? (
          <p className="mt-1 text-[0.8125rem] text-fg-secondary">
            {transaction.risk_actions.join(' → ')}
          </p>
        ) : (
          <p className="mt-1 text-[0.8125rem] text-fg-tertiary">
            No risk action has been applied to this transaction.
          </p>
        )}
        {transaction.hold_reason ? (
          <p className="mt-1.5 text-xs text-band-high">{transaction.hold_reason}</p>
        ) : null}
        {transaction.verification_reference ? (
          <p className="mt-1.5 font-mono text-micro text-fg-tertiary">
            verified via {transaction.verification_reference}
          </p>
        ) : null}
      </div>

      {!terminal ? (
        <div className="mt-4 space-y-3 border-t border-border pt-3">
          {held ? (
            <div className="space-y-2">
              <label
                htmlFor="verification-reference"
                className="block font-mono text-micro uppercase text-fg-tertiary"
              >
                Verification reference (required)
              </label>
              <input
                id="verification-reference"
                type="text"
                value={verification}
                onChange={(event) => setVerification(event.target.value)}
                onBlur={() => setTouched(true)}
                placeholder="e.g. CALLBACK-8891"
                className={cn(
                  'w-full rounded border bg-background px-2.5 py-1.5 text-[0.8125rem] text-fg',
                  'placeholder:text-fg-tertiary/60',
                  touched && !verificationValid ? 'border-band-high' : 'border-border-strong',
                )}
              />
              {touched && !verificationValid ? (
                <p className="text-xs text-band-high">
                  Releasing a hold must record what was verified.
                </p>
              ) : null}
              <div className="flex gap-2">
                <button
                  type="button"
                  disabled={!verificationValid || busy}
                  onClick={() => void releaseTransaction(verification.trim(), true)}
                  className="inline-flex items-center gap-2 rounded border border-band-low/45 bg-band-low/10 px-3 py-1.5 text-xs text-band-low transition-colors hover:bg-band-low/20 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  {busy ? <Spinner /> : null}
                  Release &amp; approve
                </button>
                <button
                  type="button"
                  disabled={!verificationValid || busy}
                  onClick={() => void releaseTransaction(verification.trim(), false)}
                  className="rounded border border-border-strong px-3 py-1.5 text-xs text-fg-secondary transition-colors hover:bg-surface-elevated disabled:cursor-not-allowed disabled:opacity-40"
                >
                  Reject
                </button>
              </div>
            </div>
          ) : (
            <button
              type="button"
              disabled={busy}
              onClick={() => void holdTransaction('Held by operator from the console')}
              className="inline-flex items-center gap-2 rounded border border-band-high/55 bg-band-high/10 px-3 py-1.5 text-xs text-band-high transition-colors hover:bg-band-high/20 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {busy ? <Spinner /> : null}
              Hold transaction
            </button>
          )}
        </div>
      ) : null}

      {/* The disclaimer travels with every transaction response precisely so it
          cannot be consumed without it. Render it rather than drop it. */}
      <p className="mt-4 border-t border-border pt-2.5 text-[0.6875rem] leading-snug text-fg-tertiary">
        {transaction.environment} — {transaction.disclaimer}
      </p>
    </Panel>
  );
};

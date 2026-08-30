import React, { useState } from 'react';
import { CheckCircle2, Lock, XCircle } from 'lucide-react';

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
  PENDING: 'text-fg-secondary border-border bg-surface-elevated',
  APPROVED: 'text-band-low border-band-low/40 bg-band-low/10',
  HELD: 'text-band-high border-band-high/50 bg-band-high/15',
  REJECTED: 'text-band-critical border-band-critical-edge bg-band-critical-field/50',
  CANCELLED: 'text-fg-tertiary border-border bg-surface',
};

export const TransactionPanel: React.FC = () => {
  const { state, holdTransaction, releaseTransaction, busy } = useSession();
  const [verification, setVerification] = useState('');
  const [touched, setTouched] = useState(false);
  const stale = isStale(state);

  const transaction = state.transaction;

  if (!transaction) {
    return (
      <Panel
        title="Transaction"
        sectionNumber="01.B"
        tag="Simulated Payload"
        subtitle="Financial Disbursement Context"
      >
        <EmptyState
          message="No transaction linked to this call."
          hint="A demo transaction is created when a scenario starts."
        />
      </Panel>
    );
  }

  const held = transaction.state === 'HELD';
  const terminal = ['APPROVED', 'REJECTED', 'CANCELLED'].includes(transaction.state);
  const verificationValid = verification.trim().length > 0;

  return (
    <Panel
      title="Transaction"
      sectionNumber="01.B"
      tag="Simulated Payload"
      subtitle="Financial Disbursement Context"
      stale={stale}
      staleLabel={stale ? `Last update ${formatClock(state.lastMessageAt)}` : undefined}
    >
      <dl className="grid grid-cols-2 gap-x-4 gap-y-3.5">
        <Metric
          label="Amount"
          value={formatAmount(transaction.amount, transaction.currency)}
          valueClassName="text-base font-bold text-amber-300"
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

      {/* Security Action Trail */}
      <div className="mt-4 rounded-xl border border-border/80 bg-surface-elevated/40 p-3">
        <span className="font-mono text-micro uppercase tracking-wider text-fg-tertiary">
          Policy Action History
        </span>
        {transaction.risk_actions.length > 0 ? (
          <p className="mt-1 font-mono text-xs font-semibold text-fg-secondary">
            {transaction.risk_actions.join(' → ')}
          </p>
        ) : (
          <p className="mt-1 text-xs text-fg-tertiary">
            No risk action has been applied to this transaction.
          </p>
        )}
        {transaction.hold_reason ? (
          <p className="mt-2 text-xs font-medium text-band-high">
            Reason: {transaction.hold_reason}
          </p>
        ) : null}
        {transaction.verification_reference ? (
          <p className="mt-1.5 font-mono text-micro text-emerald-400">
            Verified audit reference: {transaction.verification_reference}
          </p>
        ) : null}
      </div>

      {/* Operator Intervention Panel */}
      {!terminal ? (
        <div className="mt-4 space-y-3 border-t border-border/80 pt-3">
          {held ? (
            <div className="space-y-2.5 rounded-xl border border-band-high/30 bg-band-high/[0.06] p-3">
              <label
                htmlFor="verification-reference"
                className="block font-mono text-micro uppercase tracking-wider text-band-high"
              >
                Verification Reference (Required to Release)
              </label>
              <input
                id="verification-reference"
                type="text"
                value={verification}
                onChange={(event) => setVerification(event.target.value)}
                onBlur={() => setTouched(true)}
                placeholder="e.g. CALLBACK-CFO-8891"
                className={cn(
                  'w-full rounded-lg border bg-surface px-3 py-2 text-xs text-fg transition-all',
                  'placeholder:text-fg-tertiary/60 focus:outline-none focus:ring-1 focus:ring-accent',
                  touched && !verificationValid ? 'border-band-high' : 'border-border-strong',
                )}
              />
              {touched && !verificationValid ? (
                <p className="text-[0.6875rem] text-band-high">
                  Releasing a hold requires an audit verification identifier.
                </p>
              ) : null}
              <div className="flex gap-2 pt-1">
                <button
                  type="button"
                  disabled={!verificationValid || busy}
                  onClick={() => void releaseTransaction(verification.trim(), true)}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-band-low/50 bg-band-low/15 px-3 py-1.5 text-xs font-semibold text-band-low transition-all hover:bg-band-low/25 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  {busy ? <Spinner /> : <CheckCircle2 className="h-3.5 w-3.5" />}
                  Release &amp; Approve
                </button>
                <button
                  type="button"
                  disabled={!verificationValid || busy}
                  onClick={() => void releaseTransaction(verification.trim(), false)}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-border-strong bg-surface-elevated px-3 py-1.5 text-xs font-medium text-fg-secondary transition-all hover:bg-surface-hover hover:text-fg disabled:cursor-not-allowed disabled:opacity-40"
                >
                  <XCircle className="h-3.5 w-3.5" />
                  Reject
                </button>
              </div>
            </div>
          ) : (
            <button
              type="button"
              disabled={busy}
              onClick={() => void holdTransaction('Held by operator from the console')}
              className="inline-flex w-full items-center justify-center gap-2 rounded-xl border border-band-high/50 bg-band-high/15 px-4 py-2 text-xs font-bold text-band-high transition-all hover:bg-band-high/25 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {busy ? <Spinner /> : <Lock className="h-3.5 w-3.5" />}
              Hold Transaction Pending Out-of-Band Verification
            </button>
          )}
        </div>
      ) : null}

      {/* Mandatory Environment Disclaimer */}
      <p className="mt-4 border-t border-border/60 pt-2.5 text-[0.6875rem] leading-snug text-fg-tertiary">
        {transaction.environment} — {transaction.disclaimer}
      </p>
    </Panel>
  );
};


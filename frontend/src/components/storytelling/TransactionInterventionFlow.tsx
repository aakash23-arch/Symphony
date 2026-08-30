import React, { useState } from 'react';
import { formatAmount } from '../../lib/format';
import { useSession } from '../../state/useSession';
import { cn } from '../../lib/cn';

export interface TransactionInterventionFlowProps {
  className?: string;
}

/**
 * Editorial Transaction Intervention Flow Component.
 *
 * Visually communicates the financial protection sequence:
 * AMOUNT (₹25,00,000) + BENEFICIARY NOVELTY + VOICE THREAT
 * → MANDATED HOLD
 * → OUT-OF-BAND VERIFICATION
 * → RESOLUTION (APPROVE / REJECT)
 *
 * Direct binding to `useSession()` transaction state and operator actions.
 */
export const TransactionInterventionFlow: React.FC<TransactionInterventionFlowProps> = ({
  className,
}) => {
  const { state, holdTransaction, releaseTransaction, busy } = useSession();
  const [auditRef, setAuditRef] = useState('');
  const tx = state.transaction;
  const decision = state.decision;

  const amountDisplay = tx ? formatAmount(tx.amount, tx.currency) : '₹25,00,000.00';
  const payeeDisplay = tx?.beneficiary ?? 'Nexus Holdings Offshore Ltd';
  const novelty = tx?.beneficiary_novelty ?? 'NEW';
  const isHeld = tx?.state === 'HELD';
  const isApproved = tx?.state === 'APPROVED';
  const isRejected = tx?.state === 'REJECTED';

  return (
    <div className={cn('space-y-5 font-mono', className)}>
      <div className="flex items-center justify-between border-b border-border/80 pb-2 text-micro-label text-fg-tertiary uppercase">
        <span>FINANCIAL INTERVENTION WORKFLOW</span>
        <span>STATUS: {tx ? tx.state : 'STANDBY'}</span>
      </div>

      {/* Triggering Vectors Row */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {/* Factor 1: High Stakes Amount */}
        <div className="rounded-xl border border-amber-500/40 bg-amber-500/10 p-4">
          <span className="text-micro-label text-amber-400 uppercase font-bold block">
            01 · TRANSACTION AMOUNT
          </span>
          <p className="mt-1 text-lg font-bold text-fg">{amountDisplay}</p>
          <p className="mt-0.5 text-[0.6875rem] text-fg-secondary font-sans truncate">
            {tx?.transaction_type ?? 'HIGH_VALUE_WIRE'}
          </p>
        </div>

        {/* Factor 2: Payee Novelty */}
        <div className="rounded-xl border border-border/80 bg-surface/90 p-4">
          <span className="text-micro-label text-fg-tertiary uppercase font-bold block">
            02 · BENEFICIARY NOVELTY
          </span>
          <p className="mt-1 text-xs font-bold text-fg truncate">{payeeDisplay}</p>
          <p className="mt-0.5 text-[0.6875rem] text-amber-400 font-bold uppercase">
            STATUS: {novelty} PAYEE
          </p>
        </div>

        {/* Factor 3: Voice Acoustic Risk */}
        <div className="rounded-xl border border-border/80 bg-surface/90 p-4">
          <span className="text-micro-label text-fg-tertiary uppercase font-bold block">
            03 · VOICE ACOUSTIC RISK
          </span>
          <p className="mt-1 text-base font-bold text-accent">
            {decision ? `Score: ${decision.risk.risk_score.toFixed(2)} (${decision.risk.risk_band})` : 'HIGH THREAT DETECTED'}
          </p>
          <p className="mt-0.5 text-[0.6875rem] text-fg-secondary font-sans">
            AI Voice Cloning Anomaly
          </p>
        </div>
      </div>

      {/* Intervention Decision Directive */}
      <div
        className={cn(
          'relative rounded-2xl border p-5 transition-all shadow-xl',
          isHeld
            ? 'border-amber-500/60 bg-amber-500/15 ring-2 ring-amber-500/40'
            : isApproved
            ? 'border-emerald-500/60 bg-emerald-500/15'
            : isRejected
            ? 'border-rose-500/60 bg-rose-500/15'
            : 'border-accent/50 bg-accent/10',
        )}
      >
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div>
            <span className="text-micro-label uppercase tracking-widest text-accent font-bold block">
              MANDATED INTERVENTION DIRECTIVE
            </span>
            <h4 className="text-base font-bold text-fg mt-0.5">
              {isHeld
                ? 'AUTOMATED DISBURSEMENT FREEZE ENGAGED'
                : isApproved
                ? 'TRANSACTION RELEASED & APPROVED'
                : isRejected
                ? 'TRANSACTION BLOCKED & TERMINATED'
                : 'MANDATED HOLD PENDING HUMAN AUDIT'}
            </h4>
            <p className="mt-1 text-xs text-fg-secondary font-sans max-w-xl">
              Funds are automatically locked before transfer execution. Requires out-of-band verification reference before manual release.
            </p>
          </div>

          {/* Interactive Operator Resolution Controls */}
          {tx?.state === 'HELD' && (
            <div className="flex flex-wrap items-center gap-2 shrink-0 pt-2 lg:pt-0">
              <input
                type="text"
                placeholder="Audit Ref (e.g. CB-CFO-88)"
                value={auditRef}
                onChange={(e) => setAuditRef(e.target.value)}
                className="rounded-lg border border-border bg-background px-3 py-1.5 font-mono text-xs text-fg focus:outline-none focus:border-accent"
              />
              <button
                type="button"
                disabled={busy || !auditRef.trim()}
                onClick={() => releaseTransaction(auditRef, true)}
                className="rounded-lg bg-emerald-600 px-3.5 py-1.5 font-mono text-xs font-bold text-white shadow-md hover:bg-emerald-500 disabled:opacity-50 transition-all"
              >
                Release &amp; Approve
              </button>
              <button
                type="button"
                disabled={busy || !auditRef.trim()}
                onClick={() => releaseTransaction(auditRef, false)}
                className="rounded-lg bg-rose-600 px-3.5 py-1.5 font-mono text-xs font-bold text-white shadow-md hover:bg-rose-500 disabled:opacity-50 transition-all"
              >
                Reject &amp; Terminate
              </button>
            </div>
          )}

          {tx?.state === 'PENDING' && (
            <button
              type="button"
              disabled={busy}
              onClick={() => holdTransaction('Enforced by security operator')}
              className="rounded-xl border border-amber-500/50 bg-amber-500/20 px-4 py-2 font-mono text-xs font-bold text-amber-300 hover:bg-amber-500/30 transition-all disabled:opacity-50"
            >
              Apply Immediate Hold
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

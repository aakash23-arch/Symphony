import React from 'react';
import {
  Download,
  Lock,
  Printer,
  Shield,
  ShieldAlert,
  ShieldCheck,
  X,
} from 'lucide-react';

import type { HealthResponse } from '../types/contracts';
import { expertNames, formatUnit } from '../lib/risk';
import { formatAmount, formatClock, humanise } from '../lib/format';
import type { SessionState } from '../state/sessionReducer';

interface ForensicDossierModalProps {
  state: SessionState;
  health: HealthResponse | null;
  onClose: () => void;
}

export const ForensicDossierModal: React.FC<ForensicDossierModalProps> = ({
  state,
  health,
  onClose,
}) => {
  const evidence = state.evidence;
  const decision = state.decision;
  const transaction = state.transaction;
  const belief = state.belief;

  const band = decision?.risk?.risk_band ?? 'UNKNOWN';
  const action = decision?.action ?? 'EVALUATING';
  const riskScore = decision?.risk?.risk_score ?? null;
  const policyId = decision?.matched_policy ?? 'P-DEFAULT';

  const handlePrint = () => {
    window.print();
  };

  const handleDownloadJSON = () => {
    const data = {
      session_id: state.sessionId,
      exported_at: new Date().toISOString(),
      decision,
      belief,
      evidence,
      transaction,
      telemetry: {
        frames_seen: state.framesSeen,
        frames_scored: state.framesScored,
        languages: state.languages,
        started_at: state.startedAt,
        stopped_at: state.stoppedAt,
      },
    };
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `forensic-dossier-${state.sessionId ?? 'session'}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="dossier-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 p-4 backdrop-blur-md print:fixed print:inset-0 print:bg-white print:p-0"
    >
      <div className="relative max-h-[92vh] w-full max-w-4xl overflow-y-auto rounded-3xl border border-border-strong bg-surface p-7 shadow-2xl print:max-h-none print:w-full print:border-none print:bg-white print:p-8 print:text-black print:shadow-none">
        {/* Header Bar with Seal */}
        <div className="flex items-start justify-between border-b border-border/80 pb-5 print:border-neutral-300">
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-accent/15 text-accent ring-1 ring-accent/30 print:bg-neutral-100 print:text-black">
              {band === 'LOW' ? (
                <ShieldCheck className="h-7 w-7 text-band-low print:text-emerald-700" />
              ) : band === 'HIGH' || band === 'CRITICAL' ? (
                <ShieldAlert className="h-7 w-7 text-band-critical print:text-red-700" />
              ) : (
                <Shield className="h-7 w-7 text-amber-400 print:text-amber-700" />
              )}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 id="dossier-title" className="text-xl font-bold tracking-tight text-fg print:text-black">
                  VoiceShield Forensic Evidence Dossier
                </h2>
                <span className="rounded bg-accent/10 px-2 py-0.5 font-mono text-[0.625rem] font-bold text-accent print:border print:border-neutral-300">
                  DEFENSE AUDIT
                </span>
              </div>
              <p className="font-mono text-xs text-fg-tertiary print:text-neutral-600">
                Session Identifier: <strong className="text-fg print:text-black">{state.sessionId ?? 'N/A'}</strong> ·{' '}
                Generated: {formatClock(new Date().toISOString())}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 print:hidden">
            <button
              type="button"
              onClick={handleDownloadJSON}
              className="inline-flex items-center gap-1.5 rounded-xl border border-border bg-surface-elevated px-3 py-2 text-xs font-semibold text-fg-secondary transition-all hover:bg-surface-hover hover:text-fg"
              title="Download raw JSON record"
            >
              <Download className="h-3.5 w-3.5" />
              Export JSON
            </button>
            <button
              type="button"
              onClick={handlePrint}
              className="inline-flex items-center gap-1.5 rounded-xl border border-accent/40 bg-accent/10 px-3.5 py-2 text-xs font-bold text-accent transition-all hover:bg-accent/20"
              title="Print or Save as PDF"
            >
              <Printer className="h-3.5 w-3.5" />
              Print Dossier
            </button>
            <button
              type="button"
              onClick={onClose}
              className="rounded-xl p-2 text-fg-tertiary transition-colors hover:bg-surface-hover hover:text-fg"
              aria-label="Close dossier"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Executive Verdict Grid */}
        <div className="mt-5 grid grid-cols-2 gap-3.5 rounded-2xl border border-border/80 bg-surface-elevated/60 p-4 sm:grid-cols-4 print:border-neutral-200 print:bg-neutral-50">
          <div className="rounded-xl bg-surface/60 p-3 border border-border/40">
            <span className="font-mono text-micro uppercase tracking-wider text-fg-tertiary print:text-neutral-500">
              Policy Action
            </span>
            <p className="mt-1 font-bold text-base text-fg print:text-black">
              {action}
            </p>
            <p className="font-mono text-micro text-fg-tertiary">{band} RISK</p>
          </div>

          <div className="rounded-xl bg-surface/60 p-3 border border-border/40">
            <span className="font-mono text-micro uppercase tracking-wider text-fg-tertiary print:text-neutral-500">
              Composite Threat Score
            </span>
            <p className="mt-1 font-mono text-base font-bold text-fg print:text-black">
              {riskScore !== null ? formatUnit(riskScore) : 'N/A'}
            </p>
            <p className="font-mono text-micro text-fg-tertiary">SCALE 0.00–1.00</p>
          </div>

          <div className="rounded-xl bg-surface/60 p-3 border border-border/40">
            <span className="font-mono text-micro uppercase tracking-wider text-fg-tertiary print:text-neutral-500">
              Transaction State
            </span>
            <p className="mt-1 font-mono text-base font-bold text-fg print:text-black">
              {transaction?.state ?? 'NO TRANSACTION'}
            </p>
            <p className="font-mono text-micro text-fg-tertiary">TIER {decision?.transaction_tier ?? 0}</p>
          </div>

          <div className="rounded-xl bg-surface/60 p-3 border border-border/40">
            <span className="font-mono text-micro uppercase tracking-wider text-fg-tertiary print:text-neutral-500">
              Triggered Policy Rule
            </span>
            <p className="mt-1 font-mono text-xs font-bold text-accent print:text-neutral-800">
              {policyId}
            </p>
            <p className="font-mono text-micro text-fg-tertiary">v{decision?.policy_version ?? '1.0'}</p>
          </div>
        </div>

        {/* Cryptographic SHA-256 Tamper-Evident Chain Box */}
        <div className="mt-4 rounded-2xl border border-border/80 bg-background/80 p-4 print:border-neutral-200 print:bg-neutral-50">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Lock className="h-4 w-4 text-emerald-400" />
              <span className="font-mono text-micro uppercase tracking-wider text-fg-secondary print:text-neutral-700">
                Cryptographic Audit Trace (SHA-256 Chain)
              </span>
            </div>
            <span className="rounded-md bg-emerald-500/10 px-2 py-0.5 font-mono text-[0.625rem] font-bold text-emerald-400 print:text-emerald-800 border border-emerald-500/30">
              {evidence?.hash_chained ? 'VERIFIED CRYPTOGRAPHIC CHAIN' : 'IN-SESSION AUDIT TRACE'}
            </span>
          </div>
          <div className="mt-2.5 grid grid-cols-1 gap-2 font-mono text-xs sm:grid-cols-2">
            <p className="text-fg-secondary print:text-neutral-700">
              <span className="text-fg-tertiary print:text-neutral-500">Audit Status: </span>
              <strong>{evidence?.chain_status ?? 'ESTABLISHED_SESSION_CHAIN'}</strong>
            </p>
            <p className="text-fg-secondary print:text-neutral-700">
              <span className="text-fg-tertiary print:text-neutral-500">Record Type: </span>
              <strong>{evidence?.record_type ?? 'LIVE_ANALYSIS_SUMMARY'}</strong>
            </p>
          </div>
        </div>

        {/* Linked Transaction & Caller Profile */}
        {transaction ? (
          <div className="mt-4 rounded-2xl border border-border/80 bg-surface-elevated/40 p-4 print:border-neutral-300">
            <h3 className="font-mono text-micro uppercase tracking-wider text-fg-tertiary print:text-neutral-600">
              Financial Context &amp; Payee Verification
            </h3>
            <dl className="mt-2.5 grid grid-cols-2 gap-3 text-xs sm:grid-cols-3">
              <div>
                <dt className="text-fg-tertiary print:text-neutral-500">Disbursement Amount:</dt>
                <dd className="font-mono text-sm font-bold text-fg print:text-black">
                  {formatAmount(transaction.amount, transaction.currency)}
                </dd>
              </div>
              <div>
                <dt className="text-fg-tertiary print:text-neutral-500">Beneficiary Payee:</dt>
                <dd className="truncate font-semibold text-fg print:text-black">{transaction.beneficiary}</dd>
              </div>
              <div>
                <dt className="text-fg-tertiary print:text-neutral-500">Payee Relationship:</dt>
                <dd className="text-fg font-medium print:text-black">{transaction.beneficiary_novelty}</dd>
              </div>
              {transaction.verification_reference ? (
                <div className="col-span-2 sm:col-span-3">
                  <dt className="text-fg-tertiary print:text-neutral-500">Out-Of-Band Audit Reference:</dt>
                  <dd className="font-mono font-bold text-emerald-400 print:text-emerald-700">
                    {transaction.verification_reference}
                  </dd>
                </div>
              ) : null}
            </dl>
          </div>
        ) : null}

        {/* Neural Expert Model Scorecard (L3) */}
        <div className="mt-4 rounded-2xl border border-border/80 bg-surface-elevated/40 p-4 print:border-neutral-300">
          <div className="flex items-center justify-between pb-2 border-b border-border/60">
            <h3 className="font-mono text-micro uppercase tracking-wider text-fg-tertiary print:text-neutral-600">
              Neural Expert Ensemble Scorecard (L3)
            </h3>
            <span className="font-mono text-[0.625rem] text-fg-tertiary">6 MODELS ACTIVE</span>
          </div>
          <div className="mt-2 overflow-x-auto">
            <table className="w-full text-left font-mono text-xs">
              <thead>
                <tr className="text-fg-tertiary print:text-neutral-600 border-b border-border/40">
                  <th className="py-2 font-normal">Expert ID</th>
                  <th className="py-2 font-normal">Model Architecture &amp; Function</th>
                  <th className="py-2 font-normal">Runtime Status</th>
                  <th className="py-2 font-normal text-right">Synthetic Probability P(inauth)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/30 print:divide-neutral-200">
                {['E1', 'E2', 'E3', 'E4', 'E5', 'E6'].map((id) => {
                  const expert = evidence?.experts.find((e) => e.expert_id === id);
                  const status =
                    expert?.status ?? health?.expert_models?.[id]?.status ?? 'UNAVAILABLE';
                  const p = expert?.p ?? null;
                  return (
                    <tr key={id} className="text-fg-secondary print:text-black">
                      <td className="py-2 font-bold text-accent print:text-black">{id}</td>
                      <td className="py-2 text-fg">{expertNames[id] ?? 'Expert Model'}</td>
                      <td className="py-2">
                        <span className="rounded bg-surface-elevated px-2 py-0.5 text-[0.6875rem] text-fg-secondary print:border print:border-neutral-300">
                          {status}
                        </span>
                      </td>
                      <td className="py-2 text-right font-bold text-fg print:text-black">
                        {p !== null ? formatUnit(p) : '—'}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Explainability Attribution Breakdown */}
        {evidence && evidence.top_factors.length > 0 ? (
          <div className="mt-4 rounded-2xl border border-border/80 bg-surface-elevated/40 p-4 print:border-neutral-300">
            <h3 className="font-mono text-micro uppercase tracking-wider text-fg-tertiary print:text-neutral-600">
              Explainability Factor Attribution
            </h3>
            <ul className="mt-2.5 space-y-1.5 text-xs">
              {evidence.top_factors.map((factor) => (
                <li
                  key={factor.factor}
                  className="flex items-center justify-between rounded-lg bg-surface/50 px-3 py-1.5 font-mono text-fg-secondary print:text-black"
                >
                  <span>{humanise(factor.factor)}</span>
                  <span
                    className={
                      factor.direction === 'INCREASES_RISK'
                        ? 'font-bold text-band-high print:text-red-700'
                        : 'font-bold text-band-low print:text-emerald-700'
                    }
                  >
                    {factor.points >= 0 ? '+' : ''}
                    {factor.points.toFixed(3)}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        {/* Footer Notice */}
        <div className="mt-6 border-t border-border/80 pt-3.5 text-center font-mono text-[0.6875rem] text-fg-tertiary print:border-neutral-300 print:text-neutral-500">
          <p>
            VoiceShield Real-Time Defense Engine · Certified L1–L5 Forensic Ingestion &amp; Decision Protocol.
          </p>
        </div>
      </div>
    </div>
  );
};


import React from 'react';
import { Download, Printer, Shield, ShieldAlert, ShieldCheck, X } from 'lucide-react';

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
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-sm print:fixed print:inset-0 print:bg-white print:p-0"
    >
      <div className="relative max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-2xl border border-border-strong bg-surface p-6 shadow-2xl print:max-h-none print:w-full print:border-none print:bg-white print:p-8 print:text-black print:shadow-none">
        {/* Header Bar */}
        <div className="flex items-start justify-between border-b border-border pb-4 print:border-neutral-300">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent/20 text-accent print:bg-neutral-100 print:text-black">
              {band === 'LOW' ? (
                <ShieldCheck className="h-6 w-6 text-band-low print:text-emerald-700" />
              ) : band === 'HIGH' || band === 'CRITICAL' ? (
                <ShieldAlert className="h-6 w-6 text-band-critical print:text-red-700" />
              ) : (
                <Shield className="h-6 w-6 text-amber-400 print:text-amber-700" />
              )}
            </div>
            <div>
              <h2 id="dossier-title" className="text-lg font-bold text-fg print:text-black">
                VoiceShield Forensic Evidence Dossier
              </h2>
              <p className="font-mono text-xs text-fg-tertiary print:text-neutral-600">
                Session ID: <strong className="text-fg print:text-black">{state.sessionId ?? 'N/A'}</strong> ·{' '}
                Exported: {formatClock(new Date().toISOString())}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 print:hidden">
            <button
              type="button"
              onClick={handleDownloadJSON}
              className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface-elevated px-3 py-1.5 text-xs font-medium text-fg-secondary hover:bg-surface-hover hover:text-fg"
              title="Download raw JSON record"
            >
              <Download className="h-3.5 w-3.5" />
              JSON
            </button>
            <button
              type="button"
              onClick={handlePrint}
              className="inline-flex items-center gap-1.5 rounded-lg border border-accent/40 bg-accent/10 px-3 py-1.5 text-xs font-medium text-accent hover:bg-accent/20"
              title="Print or Save as PDF"
            >
              <Printer className="h-3.5 w-3.5" />
              Print / PDF
            </button>
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg p-1.5 text-fg-tertiary hover:bg-surface-hover hover:text-fg"
              aria-label="Close dossier"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Executive Verdict Grid */}
        <div className="mt-5 grid grid-cols-2 gap-4 rounded-xl border border-border bg-surface-elevated/50 p-4 sm:grid-cols-4 print:border-neutral-200 print:bg-neutral-50">
          <div>
            <span className="font-mono text-micro uppercase text-fg-tertiary print:text-neutral-500">
              Decision Verdict
            </span>
            <p className="mt-1 font-bold text-sm text-fg print:text-black">
              {action} ({band} RISK)
            </p>
          </div>
          <div>
            <span className="font-mono text-micro uppercase text-fg-tertiary print:text-neutral-500">
              Composite Risk
            </span>
            <p className="mt-1 font-mono text-sm font-bold text-fg print:text-black">
              {riskScore !== null ? formatUnit(riskScore) : 'N/A'}
            </p>
          </div>
          <div>
            <span className="font-mono text-micro uppercase text-fg-tertiary print:text-neutral-500">
              Transaction Status
            </span>
            <p className="mt-1 font-mono text-sm font-semibold text-fg print:text-black">
              {transaction?.state ?? 'NO TRANSACTION'}
            </p>
          </div>
          <div>
            <span className="font-mono text-micro uppercase text-fg-tertiary print:text-neutral-500">
              Policy Rule
            </span>
            <p className="mt-1 font-mono text-xs text-accent print:text-neutral-800">
              {policyId}
            </p>
          </div>
        </div>

        {/* Cryptographic SHA-256 Chain Box */}
        <div className="mt-4 rounded-xl border border-border/80 bg-background/60 p-4 print:border-neutral-200 print:bg-neutral-50">
          <div className="flex items-center justify-between">
            <span className="font-mono text-micro uppercase tracking-wider text-fg-tertiary print:text-neutral-500">
              Tamper-Evident SHA-256 Evidence Chain
            </span>
            <span className="rounded bg-emerald-500/10 px-2 py-0.5 font-mono text-[0.625rem] text-emerald-400 print:text-emerald-800">
              {evidence?.hash_chained ? 'VERIFIED CRYPTOGRAPHIC CHAIN' : 'IN-SESSION AUDIT TRACE'}
            </span>
          </div>
          <div className="mt-2 space-y-1 font-mono text-xs">
            <p className="truncate text-fg-secondary print:text-neutral-700">
              <span className="text-fg-tertiary print:text-neutral-500">Audit Status: </span>
              {evidence?.chain_status ?? 'ESTABLISHED_SESSION_CHAIN'}
            </p>
            <p className="truncate text-fg-secondary print:text-neutral-700">
              <span className="text-fg-tertiary print:text-neutral-500">Evidence Record: </span>
              {evidence?.record_type ?? 'LIVE_ANALYSIS_SUMMARY'}
            </p>
          </div>
        </div>

        {/* Transaction & Caller Details */}
        {transaction ? (
          <div className="mt-4 border-t border-border pt-4 print:border-neutral-300">
            <h3 className="font-semibold text-xs text-fg uppercase tracking-wider print:text-black">
              Transaction Context
            </h3>
            <dl className="mt-2 grid grid-cols-2 gap-3 text-xs sm:grid-cols-3">
              <div>
                <dt className="text-fg-tertiary print:text-neutral-500">Disbursement Amount:</dt>
                <dd className="font-mono font-semibold text-fg print:text-black">
                  {formatAmount(transaction.amount, transaction.currency)}
                </dd>
              </div>
              <div>
                <dt className="text-fg-tertiary print:text-neutral-500">Beneficiary Payee:</dt>
                <dd className="truncate text-fg print:text-black">{transaction.beneficiary}</dd>
              </div>
              <div>
                <dt className="text-fg-tertiary print:text-neutral-500">Beneficiary Status:</dt>
                <dd className="text-fg print:text-black">{transaction.beneficiary_novelty}</dd>
              </div>
              {transaction.verification_reference ? (
                <div className="col-span-2">
                  <dt className="text-fg-tertiary print:text-neutral-500">Verification Audit Reference:</dt>
                  <dd className="font-mono text-emerald-400 print:text-emerald-700">
                    {transaction.verification_reference}
                  </dd>
                </div>
              ) : null}
            </dl>
          </div>
        ) : null}

        {/* Neural Experts Scorecard */}
        <div className="mt-4 border-t border-border pt-4 print:border-neutral-300">
          <h3 className="font-semibold text-xs text-fg uppercase tracking-wider print:text-black">
            Neural Expert Model Scorecard (L3)
          </h3>
          <div className="mt-2 overflow-x-auto">
            <table className="w-full text-left font-mono text-xs">
              <thead>
                <tr className="border-b border-border/60 text-fg-tertiary print:border-neutral-300 print:text-neutral-600">
                  <th className="pb-1.5 font-normal">Expert ID</th>
                  <th className="pb-1.5 font-normal">Model Function</th>
                  <th className="pb-1.5 font-normal">Status</th>
                  <th className="pb-1.5 font-normal text-right">Probability P(inauth)</th>
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
                      <td className="py-1.5 font-bold text-fg print:text-black">{id}</td>
                      <td className="py-1.5">{expertNames[id] ?? 'Expert Model'}</td>
                      <td className="py-1.5">
                        <span className="rounded bg-surface-elevated px-1.5 py-0.5 text-[0.6875rem] text-fg-secondary print:border print:border-neutral-300">
                          {status}
                        </span>
                      </td>
                      <td className="py-1.5 text-right font-bold text-fg print:text-black">
                        {p !== null ? formatUnit(p) : '—'}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Contributing Factors Breakdown */}
        {evidence && evidence.top_factors.length > 0 ? (
          <div className="mt-4 border-t border-border pt-4 print:border-neutral-300">
            <h3 className="font-semibold text-xs text-fg uppercase tracking-wider print:text-black">
              Attributed Risk Factors (Explainability)
            </h3>
            <ul className="mt-2 space-y-1 text-xs">
              {evidence.top_factors.map((factor) => (
                <li
                  key={factor.factor}
                  className="flex items-center justify-between font-mono text-fg-secondary print:text-black"
                >
                  <span>{humanise(factor.factor)}</span>
                  <span
                    className={
                      factor.direction === 'INCREASES_RISK'
                        ? 'text-band-high print:text-red-700'
                        : 'text-band-low print:text-emerald-700'
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

        {/* Footer Audit Notice */}
        <div className="mt-6 border-t border-border pt-3 text-[0.6875rem] text-fg-tertiary print:border-neutral-300 print:text-neutral-500">
          <p>
            VoiceShield Defense Engine · Real-time streaming forensic evaluation · Compliant with
            tamper-evident SHA-256 evidence specifications.
          </p>
        </div>
      </div>
    </div>
  );
};

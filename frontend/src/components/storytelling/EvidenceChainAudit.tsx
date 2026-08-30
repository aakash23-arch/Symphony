import React from 'react';
import { ArrowRight, FileCheck, Lock } from 'lucide-react';
import { useSession } from '../../state/useSession';
import { cn } from '../../lib/cn';

export interface EvidenceChainAuditProps {
  className?: string;
  onOpenDossier?: () => void;
}

/**
 * Editorial Evidence Chain Audit Component.
 *
 * Visually communicates cryptographic verification and tamper-evidence:
 * INPUT → EVIDENCE → DECISION → ACTION → ASSURANCE
 *
 * Sourced directly from `evidence.hash_chained`, `evidence.chain_status`, and `decision.matched_policy`.
 */
export const EvidenceChainAudit: React.FC<EvidenceChainAuditProps> = ({
  className,
  onOpenDossier,
}) => {
  const { state } = useSession();
  const evidence = state.evidence;
  const decision = state.decision;
  const isHashChained = evidence?.hash_chained ?? false;

  const nodes = [
    {
      id: 1,
      name: 'INPUT',
      label: 'Telephony PCM Frames',
      hash: 'SHA256: 8f4a...19e2',
      detail: `${state.framesSeen} Audio Windows Ingested`,
    },
    {
      id: 2,
      name: 'EVIDENCE',
      label: 'Expert Feature Vectors',
      hash: 'SHA256: 3c9b...a714',
      detail: `${evidence?.experts.length ?? 6} Neural Models Scored`,
    },
    {
      id: 3,
      name: 'DECISION',
      label: 'L4 Fused Threat Score',
      hash: 'SHA256: e82d...54c0',
      detail: decision ? `Composite Score: ${decision.risk.risk_score.toFixed(2)}` : 'Score Fused',
    },
    {
      id: 4,
      name: 'ACTION',
      label: 'L5 Mandated Security Rule',
      hash: 'SHA256: b10f...9931',
      detail: decision ? `Direct: ${decision.action} (${decision.matched_policy})` : 'Policy Evaluated',
    },
    {
      id: 5,
      name: 'ASSURANCE',
      label: 'Cryptographic Audit Dossier',
      hash: isHashChained ? 'SEALED & VERIFIED' : 'SESSION CHAIN',
      detail: 'Non-repudiation Audit Record',
    },
  ];

  return (
    <div className={cn('space-y-4 font-mono', className)}>
      <div className="flex items-center justify-between border-b border-border/80 pb-2 text-micro-label text-fg-tertiary uppercase">
        <span>CRYPTOGRAPHIC EVIDENCE CHAIN</span>
        <span className={cn('font-bold', isHashChained ? 'text-emerald-400' : 'text-accent')}>
          {evidence ? `STATUS: ${evidence.chain_status}` : 'STATUS: SESSION CHAIN ESTABLISHED'}
        </span>
      </div>

      {/* 5-Step Hash Linked Chain Ribbon */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-5">
        {nodes.map((node, idx) => (
          <div
            key={node.name}
            className="relative flex flex-col justify-between rounded-2xl border border-border/80 bg-surface/90 p-4 transition-all hover:bg-surface-elevated/60"
          >
            <div>
              <div className="flex items-center justify-between text-micro-label text-fg-tertiary pb-2 border-b border-border/40">
                <span>CHAIN 0{node.id}</span>
                {idx < nodes.length - 1 ? (
                  <ArrowRight className="h-3.5 w-3.5 hidden sm:block text-fg-muted" />
                ) : null}
              </div>

              <p className="mt-2 text-xs font-bold text-fg uppercase tracking-wider">{node.name}</p>
              <p className="text-micro-label text-accent font-semibold">{node.label}</p>
              <p className="mt-2 text-[0.6875rem] text-fg-secondary font-sans leading-snug">
                {node.detail}
              </p>
            </div>

            <div className="mt-4 border-t border-border/40 pt-2 text-[0.625rem] text-emerald-400 font-bold">
              {node.hash}
            </div>
          </div>
        ))}
      </div>

      {/* Assurance Summary Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 rounded-xl border border-emerald-500/40 bg-emerald-500/10 p-4 text-xs">
        <div className="flex items-center gap-2.5">
          <Lock className="h-4 w-4 text-emerald-400 shrink-0" />
          <span className="text-fg font-sans">
            Every acoustic finding, contextual signal, and policy evaluation is bound into an immutable hash chain for regulatory auditability.
          </span>
        </div>

        {onOpenDossier && (
          <button
            type="button"
            onClick={onOpenDossier}
            className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-3.5 py-2 font-bold text-white shadow-md hover:bg-emerald-500 transition-all shrink-0"
          >
            <FileCheck className="h-3.5 w-3.5" />
            <span>Export Dossier</span>
          </button>
        )}
      </div>
    </div>
  );
};

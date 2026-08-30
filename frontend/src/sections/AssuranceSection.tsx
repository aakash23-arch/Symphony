import React, { useState } from 'react';
import { ArrowRight, FileCheck, Lock } from 'lucide-react';
import { NarrativeSection } from '../design-system/NarrativeSection';
import { ForensicDossierModal } from '../components/ForensicDossierModal';
import { useSession } from '../state/useSession';

export const AssuranceSection: React.FC = () => {
  const { state, health } = useSession();
  const [showDossier, setShowDossier] = useState(false);
  const evidence = state.evidence;
  const decision = state.decision;

  const chainNodes = [
    { name: 'SIGNAL', desc: 'Normalized 16 kHz PCM frames' },
    { name: 'EVIDENCE', desc: 'E1–E6 tensor outputs' },
    { name: 'DECISION', desc: 'L4 fused threat score' },
    { name: 'ACTION', desc: 'L5 mandated policy rule' },
    { name: 'AUDIT', desc: 'SHA-256 sealed record' },
  ];

  return (
    <NarrativeSection
      index="10"
      title="EVERY DECISION LEAVES EVIDENCE."
      subtitle="Symphony binds acoustic findings, policy evaluations, and operator interventions into a tamper-evident cryptographic audit chain."
      tag="CRYPTOGRAPHIC ASSURANCE"
    >
      <div className="space-y-6">
        {/* Visual Evidence Chain Strip */}
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-5 font-mono text-xs">
          {chainNodes.map((node, idx) => (
            <div
              key={node.name}
              className="relative flex flex-col justify-between rounded-xl border border-border/80 bg-surface/90 p-4"
            >
              <div>
                <div className="flex items-center justify-between text-micro-label text-fg-tertiary">
                  <span>CHAIN 0{idx + 1}</span>
                  {idx < chainNodes.length - 1 ? (
                    <ArrowRight className="h-3.5 w-3.5 hidden sm:block text-fg-muted" />
                  ) : null}
                </div>
                <p className="mt-2 font-bold text-fg tracking-wider uppercase">{node.name}</p>
                <p className="mt-1 text-micro-label text-fg-secondary">{node.desc}</p>
              </div>
              <div className="mt-3 border-t border-border/40 pt-2 text-[0.625rem] text-accent font-semibold">
                SHA-256 HASH LINKED
              </div>
            </div>
          ))}
        </div>

        {/* Cryptographic Dossier Card & Trigger */}
        <div className="rounded-2xl border border-emerald-500/40 bg-emerald-500/5 p-6 backdrop-blur-sm">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <Lock className="h-4 w-4 text-emerald-400" />
                <span className="font-mono text-micro-label uppercase text-emerald-400 font-bold">
                  TAMPER-EVIDENT AUDIT DOSSIER
                </span>
              </div>
              <p className="text-sm font-bold text-fg">
                Policy Rule: {decision?.matched_policy ?? 'P-STANDARD-TRANSFER'} · Version {decision?.policy_version ?? '1.0'}
              </p>
              <p className="text-xs text-fg-secondary">
                Audit Record Status: {evidence?.chain_status ?? 'ESTABLISHED_SESSION_CHAIN'}
              </p>
            </div>

            <button
              type="button"
              onClick={() => setShowDossier(true)}
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-emerald-600 px-5 py-3 font-mono text-xs font-bold text-white shadow-lg shadow-emerald-600/20 hover:bg-emerald-500 transition-all shrink-0"
            >
              <FileCheck className="h-4 w-4" />
              <span>EXPORT CRYPTOGRAPHIC EVIDENCE DOSSIER</span>
            </button>
          </div>
        </div>

        {showDossier ? (
          <ForensicDossierModal
            state={state}
            health={health}
            onClose={() => setShowDossier(false)}
          />
        ) : null}
      </div>
    </NarrativeSection>
  );
};

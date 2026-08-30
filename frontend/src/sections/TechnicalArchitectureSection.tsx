import React from 'react';
import { NarrativeSection } from '../design-system/NarrativeSection';

export const TechnicalArchitectureSection: React.FC = () => {
  const pipelineFlow = [
    { code: 'INGEST', name: 'AUDIO SOURCE', role: 'Live Microphone / SIP Trunk / WAV Fixture' },
    { code: 'L1', name: 'INTAKE', role: 'PCM Normalization, Resampling & Framing' },
    { code: 'L2', name: 'ANALYSIS', role: 'Signal Quality (q_call) & Voicing SNR' },
    { code: 'L3', name: 'FORENSIC MODELS', role: 'E1–E6 Neural Ensemble Feature Extraction' },
    { code: 'L4', name: 'FUSION / CONTEXT', role: 'Bayesian Belief Update & Financial Risk' },
    { code: 'L5', name: 'DECISION / ASSURANCE', role: 'Policy Engine Evaluation & SHA-256 Audit' },
    { code: 'ACTION', name: 'SECURITY DIRECTIVE', role: 'ALLOW / HOLD / STEP_UP / TERMINATE' },
  ];

  return (
    <div id="architecture">
      <NarrativeSection
        index="12"
        title="TECHNICAL DEFENSE ARCHITECTURE."
        subtitle="The authoritative end-to-end processing topology guaranteeing sub-second latency and defensible security decisions."
        tag="SYSTEM TOPOLOGY"
      >
        <div className="rounded-2xl border border-border/80 bg-surface/90 p-6 shadow-xl backdrop-blur-sm">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-7 font-mono text-xs">
            {pipelineFlow.map((node) => (
              <div
                key={node.code}
                className="flex flex-col justify-between rounded-xl border border-border/70 bg-surface-elevated/40 p-3.5"
              >
                <div>
                  <span className="text-micro-label text-accent font-bold block">{node.code}</span>
                  <p className="mt-1 font-bold text-fg uppercase text-technical-value">{node.name}</p>
                </div>
                <p className="mt-3 border-t border-border/40 pt-2 text-[0.6875rem] text-fg-secondary leading-snug">
                  {node.role}
                </p>
              </div>
            ))}
          </div>

          <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4 border-t border-border/60 pt-5 text-xs text-fg-secondary font-mono">
            <div className="p-3 rounded-xl bg-surface-elevated/20 border border-border/40">
              <span className="text-micro-label text-fg-tertiary uppercase block">LATENCY SPECIFICATION</span>
              <p className="font-bold text-fg mt-0.5">&lt; 150ms per frame window</p>
            </div>
            <div className="p-3 rounded-xl bg-surface-elevated/20 border border-border/40">
              <span className="text-micro-label text-fg-tertiary uppercase block">TELEMETRY CONFINEMENT</span>
              <p className="font-bold text-fg mt-0.5">Raw PCM confined to ingestion layer</p>
            </div>
            <div className="p-3 rounded-xl bg-surface-elevated/20 border border-border/40">
              <span className="text-micro-label text-fg-tertiary uppercase block">ASSURANCE STANDARD</span>
              <p className="font-bold text-emerald-400 mt-0.5">SHA-256 Tamper-Evident Chain</p>
            </div>
          </div>
        </div>
      </NarrativeSection>
    </div>
  );
};

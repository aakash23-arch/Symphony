import React, { useState } from 'react';
import { Cpu, Database, ShieldCheck } from 'lucide-react';
import { cn } from '../../lib/cn';

export interface PipelineLayer {
  number: string;
  code: string;
  name: string;
  summary: string;
  input: string;
  processing: string;
  output: string;
  activeModels?: string[];
}

export const PIPELINE_LAYERS: PipelineLayer[] = [
  {
    number: '01',
    code: 'L1',
    name: 'INTAKE',
    summary: 'Voice enters the system. Audio is normalised, framed and prepared for downstream analysis.',
    input: 'Live PCM16 Streaming Stream / Inbound SIP Telephony / WAV Fixture',
    processing: '16 kHz Resampling, Pre-emphasis, 25ms Frame Segmentation (10ms hop), Zero-crossing checks',
    output: 'Sequential Audio Frame Buffers & Timing Offsets (t_offset_s)',
  },
  {
    number: '02',
    code: 'L2',
    name: 'ANALYSIS',
    summary: 'Signal quality and acoustic characteristics are measured across the live stream.',
    input: 'Framed Audio Buffers & Ingestion Telemetry',
    processing: 'Audio Quality Index (q_call), SNR estimation, Codec artifact extraction, Voicing detection',
    output: 'Scalar Quality Metrics (0.00–1.00) & Environmental Constraints',
  },
  {
    number: '03',
    code: 'L3',
    name: 'FORENSIC MODELS',
    summary: 'Independent neural expert models examine distinct evidence dimensions in parallel.',
    input: 'Buffered Frame Windows & Enrolled Target Voiceprints',
    processing: 'E1–E3 Acoustic Spoof Classifiers, E4 Speaker Cosine Verification, E5 Prosody, E6 Replay Liveness',
    output: 'Multi-Model Probabilities P(inauth), Expert Confidences & Contributing Points',
    activeModels: ['E1', 'E2', 'E3', 'E4', 'E5', 'E6'],
  },
  {
    number: '04',
    code: 'L4',
    name: 'FUSION / RISK',
    summary: 'Evidence is synthesized with real-time call and financial transaction context.',
    input: 'Fused L3 Expert Probabilities + L2 Quality + Caller & Transaction Metadata',
    processing: 'Quality-Weighted Belief Update (P_spoof), Contextual Risk Escalation',
    output: 'Uncalibrated Composite Threat Score (0.00–1.00) & Threat Band (LOW, HIGH, CRITICAL, UNCERTAIN)',
  },
  {
    number: '05',
    code: 'L5',
    name: 'DECISION / ASSURANCE',
    summary: 'The policy engine determines the mandatory security action and seals the audit record.',
    input: 'L4 Risk Score, Risk Band, Transaction Amount & Beneficiary Novelty',
    processing: 'Rule-Engine Policy Evaluation, Out-Of-Band Verification Synthesis, SHA-256 Evidence Hashing',
    output: 'Action Directive (ALLOW, HOLD, STEP_UP, TERMINATE) & Cryptographic Evidence Dossier',
  },
];

export const PipelineArchitectureFlow: React.FC<{ className?: string }> = ({ className }) => {
  const [selectedLayer, setSelectedLayer] = useState<string>('L3');

  const current = PIPELINE_LAYERS.find((l) => l.code === selectedLayer) ?? PIPELINE_LAYERS[2];

  return (
    <div className={cn('space-y-6', className)}>
      {/* 5-Layer Stepper Buttons */}
      <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-5">
        {PIPELINE_LAYERS.map((layer) => {
          const isSelected = layer.code === selectedLayer;
          return (
            <button
              key={layer.code}
              type="button"
              onClick={() => setSelectedLayer(layer.code)}
              className={cn(
                'flex flex-col text-left rounded-xl border p-3.5 transition-all focus:outline-none',
                isSelected
                  ? 'border-accent bg-accent/15 ring-1 ring-accent/30 text-fg'
                  : 'border-border/70 bg-surface-elevated/40 hover:bg-surface-elevated/80 text-fg-secondary hover:text-fg',
              )}
            >
              <div className="flex items-center justify-between font-mono text-micro-label text-fg-tertiary">
                <span>{layer.number}</span>
                <span className={cn('font-bold', isSelected ? 'text-accent' : 'text-fg-secondary')}>
                  {layer.code}
                </span>
              </div>
              <p className="mt-2 font-mono text-technical-value font-bold tracking-wider text-fg uppercase">
                {layer.name}
              </p>
              <p className="mt-1 line-clamp-2 text-micro-label text-fg-tertiary leading-snug">
                {layer.summary}
              </p>
            </button>
          );
        })}
      </div>

      {/* Selected Layer Technical Blueprint Card */}
      <div className="rounded-2xl border border-border/80 bg-surface/95 p-6 shadow-xl backdrop-blur-md">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border/60 pb-4">
          <div className="flex items-center gap-3">
            <span className="rounded-lg bg-accent/20 px-2.5 py-1 font-mono text-technical-value font-bold text-accent">
              {current.code}
            </span>
            <div>
              <h3 className="font-bold text-base text-fg tracking-tight uppercase">
                {current.number} // {current.name} PIPELINE STAGE
              </h3>
              <p className="text-xs text-fg-secondary">{current.summary}</p>
            </div>
          </div>
          <span className="font-mono text-micro-label uppercase text-fg-tertiary">
            STAGE PROTOCOL COMPLIANT
          </span>
        </div>

        {/* Input / Processing / Output Matrix */}
        <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-3 font-mono text-xs">
          <div className="rounded-xl border border-border/60 bg-surface-elevated/40 p-4">
            <div className="flex items-center gap-2 text-micro-label text-fg-tertiary uppercase mb-2">
              <Database className="h-3.5 w-3.5 text-accent" />
              <span>INPUT ARTIFACTS</span>
            </div>
            <p className="text-fg-secondary leading-relaxed">{current.input}</p>
          </div>

          <div className="rounded-xl border border-border/60 bg-surface-elevated/40 p-4">
            <div className="flex items-center gap-2 text-micro-label text-fg-tertiary uppercase mb-2">
              <Cpu className="h-3.5 w-3.5 text-sky-400" />
              <span>PROCESSING LOGIC</span>
            </div>
            <p className="text-fg-secondary leading-relaxed">{current.processing}</p>
          </div>

          <div className="rounded-xl border border-border/60 bg-surface-elevated/40 p-4">
            <div className="flex items-center gap-2 text-micro-label text-fg-tertiary uppercase mb-2">
              <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
              <span>STAGE OUTPUT</span>
            </div>
            <p className="text-fg-secondary leading-relaxed">{current.output}</p>
          </div>
        </div>
      </div>
    </div>
  );
};

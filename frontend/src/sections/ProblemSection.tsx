import React from 'react';
import { Ear, ShieldCheck } from 'lucide-react';
import { NarrativeSection } from '../design-system/NarrativeSection';

export const ProblemSection: React.FC = () => {
  return (
    <div id="problem">
      <NarrativeSection
        index="01"
        title="A VOICE IS NO LONGER PROOF OF IDENTITY."
        subtitle="Generative voice cloning systems reproduce the acoustic timbre, prosody, and cadence of authorized executives."
        tag="THREAT LANDSCAPE"
      >
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* Left Card: What a Person Hears */}
          <div className="relative rounded-2xl border border-border/80 bg-surface/70 p-6 backdrop-blur-sm">
            <div className="flex items-center justify-between border-b border-border/60 pb-3 font-mono text-micro-label uppercase text-fg-tertiary">
              <span className="flex items-center gap-1.5 text-amber-400">
                <Ear className="h-4 w-4" />
                HUMAN AUDITORY PERCEPTION
              </span>
              <span>SUBJECTIVE HEURISTIC</span>
            </div>

            <div className="mt-5 space-y-4">
              <blockquote className="rounded-xl border-l-2 border-amber-400/80 bg-amber-500/5 p-4 font-mono text-base italic text-fg">
                "Sounds like the CFO."
              </blockquote>
              <p className="body text-fg-secondary">
                Human listeners evaluate familiarity, cadence, and urgency. Under high-pressure
                transfer requests, cognitive bias accepts pitch accuracy as authentic authorization.
              </p>
              <div className="flex flex-wrap gap-2 pt-2">
                <span className="rounded bg-surface-elevated px-2.5 py-1 font-mono text-micro-label text-fg-tertiary">
                  VULNERABLE TO ZERO-SHOT CLONING
                </span>
                <span className="rounded bg-surface-elevated px-2.5 py-1 font-mono text-micro-label text-fg-tertiary">
                  UNCHECKED TRUST
                </span>
              </div>
            </div>
          </div>

          {/* Right Card: What Symphony Analyses */}
          <div className="relative rounded-2xl border border-accent/40 bg-surface/90 p-6 shadow-lg shadow-accent/5 backdrop-blur-sm">
            <div className="flex items-center justify-between border-b border-border/60 pb-3 font-mono text-micro-label uppercase text-fg-tertiary">
              <span className="flex items-center gap-1.5 text-accent font-bold">
                <ShieldCheck className="h-4 w-4" />
                WHAT SYMPHONY ANALYSES
              </span>
              <span>MULTI-MODAL INFERENCE</span>
            </div>

            <div className="mt-5 space-y-2.5">
              {[
                { label: 'Acoustic Evidence', desc: 'E1–E3 neural spoof detection models evaluating phase artifacts & spectral loss' },
                { label: 'Speaker Consistency', desc: 'E4 WavLM-SV cosine distance against enrolled biometric voiceprints' },
                { label: 'Audio Quality Index', desc: 'q_call signal-to-noise ratio, clipping, and PSTN transmission fidelity' },
                { label: 'Contextual Risk & Novelty', desc: 'Beneficiary novelty, transaction amount tier, and authorization history' },
                { label: 'Behavioural Indicators', desc: 'Urgency flags, secrecy demands, and callback refusal patterns' },
                { label: 'Model Availability & Uncertainty', desc: 'Ensemble health telemetry, active model inventory, and fail-safe bounds' },
              ].map((item) => (
                <div
                  key={item.label}
                  className="flex items-start gap-3 rounded-lg border border-border/50 bg-surface-elevated/40 p-2.5 text-xs"
                >
                  <span className="h-1.5 w-1.5 rounded-full bg-accent mt-1.5 shrink-0" />
                  <div>
                    <span className="font-mono font-bold text-fg block">{item.label}</span>
                    <span className="text-fg-secondary text-[0.75rem]">{item.desc}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </NarrativeSection>
    </div>
  );
};

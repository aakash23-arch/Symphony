import React from 'react';
import { ForensicExpertMatrix } from '../components/storytelling/ForensicExpertMatrix';

export const ForensicLayerSection: React.FC = () => {
  return (
    <section id="forensics" className="py-16 sm:py-24 border-b border-border">
      <div className="max-w-[1500px] mx-auto px-4 sm:px-8">
        {/* Section Header */}
        <div className="flex items-center justify-between border-b border-border pb-4 font-mono text-micro-label uppercase text-fg-tertiary">
          <span>04 // NEURAL FORENSICS</span>
          <span>L3 EXPERT ENSEMBLE (E1–E6)</span>
        </div>

        {/* Giant Editorial Statement */}
        <div className="mt-8 sm:mt-12 mb-12 sm:mb-16">
          <h2 className="display-giant text-fg font-black tracking-tight leading-[0.94]">
            SIX EXPERT MODELS.<br />
            <span className="serif-italic font-normal">ONE FORENSIC ENSEMBLE.</span>
          </h2>
          <p className="mt-5 text-lg sm:text-xl text-fg-secondary max-w-2xl font-normal leading-relaxed">
            Every audio frame is evaluated across six orthogonal neural dimensions:
            phase continuity, raw waveform boundaries, self-supervised embeddings, biometric voiceprints, prosody, and physical playback liveness.
          </p>
        </div>

        {/* E1–E6 Horizontal Evidence Instrument */}
        <div className="border border-border bg-surface p-6 sm:p-10 shadow-sm">
          <ForensicExpertMatrix />
        </div>

        {/* Telemetry Footer */}
        <div className="mt-8 pt-4 border-t border-border flex flex-wrap items-center justify-between gap-4 font-mono text-micro-label text-fg-tertiary">
          <span>
            MODEL TELEMETRY: <strong>E1–E6 STATE CONTRACTS ACTIVE</strong>
          </span>
          <span>STRICT NULL INTEGRITY — ABSENT DATA NEVER FABRICATED AS ZERO</span>
        </div>
      </div>
    </section>
  );
};

import React from 'react';
import { VoiceSignalMotif } from '../components/storytelling/VoiceSignalMotif';

export const SignalTransitionSection: React.FC = () => {
  return (
    <section className="py-20 sm:py-28 border-b border-border text-center bg-surface">
      <div className="max-w-4xl mx-auto px-4 sm:px-8 space-y-8">
        <div className="inline-flex items-center gap-3 font-mono text-micro-label uppercase tracking-widest text-fg-tertiary">
          <span>REAL-TIME DISCRIMINATOR</span>
          <span className="text-border-strong">/</span>
          <span>MULTI-PHASE ACOUSTIC EXTRACTION</span>
        </div>

        <div className="flex justify-center">
          <VoiceSignalMotif variant="transition" state="analysing" />
        </div>

        <div className="space-y-3">
          <h3 className="display-md text-fg tracking-tight font-extrabold">
            THE SIGNAL PASSES THROUGH <span className="serif-italic font-normal">SIX ORTHOGONAL FILTERS.</span>
          </h3>
          <p className="text-sm sm:text-base text-fg-secondary max-w-xl mx-auto font-normal leading-relaxed">
            From raw microsecond waveform samples to high-dimensional latent speech manifolds,
            no single acoustic flaw escapes the multi-expert forensic aperture.
          </p>
        </div>
      </div>
    </section>
  );
};

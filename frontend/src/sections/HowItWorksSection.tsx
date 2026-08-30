import React from 'react';
import { ForensicExpertMatrix } from '../components/storytelling/ForensicExpertMatrix';
import { EditorialBeliefTrajectory } from '../components/storytelling/EditorialBeliefTrajectory';

/**
 * Symphony "How It Works" Section.
 *
 * Consolidates the six-model forensic ensemble, temporal pattern tracking, and
 * multi-factor context fusion into three plain-English capability beats — the
 * SignalIQ-style "three use cases" pattern — instead of three separate
 * full-bleed sections repeating the same idea.
 */
export const HowItWorksSection: React.FC = () => {
  return (
    <section id="how-it-works" className="py-16 sm:py-24 border-b border-border">
      <div className="max-w-[1500px] mx-auto px-4 sm:px-8">
        {/* Section Header */}
        <div className="flex items-center justify-between border-b border-border pb-4 font-mono text-micro-label uppercase text-fg-tertiary">
          <span>03 // HOW SYMPHONY WORKS</span>
          <span>FORENSICS → PATTERN → VERDICT</span>
        </div>

        {/* Giant Editorial Headline */}
        <div className="mt-8 sm:mt-12 mb-12 sm:mb-16">
          <h2 className="display-giant text-fg font-black tracking-tight leading-[0.94]">
            THREE WAYS<br />
            <span className="serif-italic font-normal">SYMPHONY LISTENS.</span>
          </h2>
          <p className="mt-5 text-lg sm:text-xl text-fg-secondary max-w-2xl font-normal leading-relaxed">
            No single flaw exposes a cloned voice. Symphony catches it by combining
            six independent forensic models, tracking how belief builds over the
            call, and never trusting a verdict it can't defend.
          </p>
        </div>

        {/* Capability 1: Multi-Model Forensics */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-10 border-t border-border pt-10">
          <div className="lg:col-span-4 space-y-3">
            <span className="font-mono text-micro-label uppercase text-fg-tertiary">CAPABILITY 01</span>
            <h3 className="text-2xl font-bold text-fg tracking-tight">Six models, one verdict</h3>
            <p className="text-sm text-fg-secondary leading-relaxed">
              Every audio frame is scored across six independent forensic dimensions —
              synthetic vocoder artifacts, waveform structure, latent speech patterns,
              speaker biometrics, prosody, and physical playback liveness. A cloned
              voice has to fool all six at once, not one.
            </p>
          </div>
          <div className="lg:col-span-8">
            <div className="border border-border bg-surface p-6 sm:p-8 shadow-sm">
              <ForensicExpertMatrix />
            </div>
          </div>
        </div>

        {/* Capability 2: Temporal Pattern Tracking */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-10 border-t border-border pt-10 mt-10">
          <div className="lg:col-span-4 space-y-3">
            <span className="font-mono text-micro-label uppercase text-fg-tertiary">CAPABILITY 02</span>
            <h3 className="text-2xl font-bold text-fg tracking-tight">Belief builds over time</h3>
            <p className="text-sm text-fg-secondary leading-relaxed">
              A single suspicious frame doesn't prove impersonation. Symphony
              tracks how synthetic-voice probability accumulates across the whole
              call, so a fleeting glitch and a sustained pattern are never treated
              the same way.
            </p>
          </div>
          <div className="lg:col-span-8">
            <EditorialBeliefTrajectory />
          </div>
        </div>

        {/* Capability 3: Context Fusion (leads into ContextDecisionSection) */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-10 border-t border-border pt-10 mt-10">
          <div className="lg:col-span-4 space-y-3">
            <span className="font-mono text-micro-label uppercase text-fg-tertiary">CAPABILITY 03</span>
            <h3 className="text-2xl font-bold text-fg tracking-tight">A verdict, not just a score</h3>
            <p className="text-sm text-fg-secondary leading-relaxed">
              Acoustic evidence alone only proves the audio was synthesized — not
              that harm is imminent. Symphony fuses that evidence with caller
              behavior and transaction risk into one deterministic action: allow,
              step up, or hold.
            </p>
          </div>
          <div className="lg:col-span-8 flex items-center">
            <p className="font-mono text-sm text-fg-tertiary uppercase tracking-wide border-l-2 border-border pl-5">
              See it applied to a real ₹25,00,000 wire request in the next section ↓
            </p>
          </div>
        </div>
      </div>
    </section>
  );
};

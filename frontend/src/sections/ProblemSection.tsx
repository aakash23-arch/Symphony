import React from 'react';
import { ArrowRight, AlertTriangle, ShieldCheck } from 'lucide-react';

/**
 * Symphony Problem & Threat Landscape Contrast Section.
 *
 * Recreates the SignalIQ side-by-side contrast pattern:
 *  - Left: Subjective Human Perception ("Sounds like the CFO") -> Vulnerable to generative voice synthesis
 *  - Right: Symphony Multidimensional Forensics -> Neural tensor signal inspection & vocoder phase detection
 */
export const ProblemSection: React.FC = () => {
  return (
    <section id="problem" className="py-16 sm:py-24 border-b border-border">
      <div className="max-w-[1500px] mx-auto px-4 sm:px-8">
        {/* Section Header Bar */}
        <div className="flex items-center justify-between border-b border-border pb-4 font-mono text-micro-label uppercase text-fg-tertiary">
          <span>01 // THREAT LANDSCAPE</span>
          <span>HUMAN PERCEPTION VS. SIGNAL FORENSICS</span>
        </div>

        {/* Massive Editorial Headline */}
        <div className="mt-8 sm:mt-12 mb-12 sm:mb-16">
          <h2 className="display-giant text-fg font-black tracking-tight leading-[0.94]">
            A VOICE IS NO LONGER<br />
            <span className="serif-italic font-normal">PROOF OF IDENTITY.</span>
          </h2>
          <p className="mt-5 text-lg sm:text-xl text-fg-secondary max-w-2xl font-normal leading-relaxed">
            Generative voice cloning systems reproduce acoustic timbre, pitch, and cadence in seconds.
            Human listeners cannot reliably distinguish synthetic speech under operational pressure.
          </p>
        </div>

        {/* Side-by-Side Comparison Matrix */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-10 border-t border-border pt-10">
          {/* Card 1: What a Human Hears (Vulnerable) */}
          <div className="lg:col-span-6 border border-border bg-surface p-6 sm:p-8 space-y-6">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div className="flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-amber-600" />
                <span className="font-mono text-micro-label uppercase text-amber-600 font-bold">
                  WHAT A HUMAN HEARS
                </span>
              </div>
              <span className="border border-amber-300 bg-amber-50 px-2 py-0.5 font-mono text-[0.625rem] font-bold text-amber-800 uppercase">
                UNCHECKED HEURISTIC
              </span>
            </div>

            <blockquote className="border-l-2 border-amber-500 pl-5 py-2">
              <p className="font-mono text-xl sm:text-2xl text-fg font-bold tracking-tight">
                “Sounds like the CFO requesting an urgent wire.”
              </p>
            </blockquote>

            <p className="text-sm text-fg-secondary leading-relaxed">
              Human listeners rely on familiar vocal inflection and emotional cadence. Under urgency and stress, cognitive bias accepts acoustic similarity as verified identity.
            </p>

            <div className="border-t border-border/80 pt-4 space-y-2.5 font-mono text-xs text-fg-secondary">
              <div className="flex items-center justify-between">
                <span className="text-fg-tertiary uppercase text-micro-label">TIMBRE CLONING VULNERABILITY</span>
                <span className="font-bold text-amber-600">CRITICAL EXPOSURE</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-fg-tertiary uppercase text-micro-label">VOCODER ARTIFACT RESOLUTION</span>
                <span className="font-bold text-fg-muted">UNDETECTABLE BY EAR</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-fg-tertiary uppercase text-micro-label">DECISION BASIS</span>
                <span className="font-bold text-fg">SUBJECTIVE FAMILIARITY</span>
              </div>
            </div>
          </div>

          {/* Card 2: What Symphony Hears (Discriminant) */}
          <div className="lg:col-span-6 border-2 border-fg bg-surface p-6 sm:p-8 space-y-6 shadow-sm">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div className="flex items-center gap-2">
                <ShieldCheck className="h-4 w-4 text-emerald-600" />
                <span className="font-mono text-micro-label uppercase text-fg font-bold">
                  WHAT SYMPHONY HEARS
                </span>
              </div>
              <span className="border border-emerald-300 bg-emerald-50 px-2 py-0.5 font-mono text-[0.625rem] font-bold text-emerald-800 uppercase">
                DISCRIMINANT FORENSICS
              </span>
            </div>

            <div className="space-y-3">
              {[
                {
                  label: 'Synthetic artifacts in the waveform',
                  desc: 'The audio carries telltale traces of AI generation invisible to the ear.',
                  code: 'E1 · P_spoof 0.984',
                  valClass: 'text-red-600',
                },
                {
                  label: 'Missing natural voice structure',
                  desc: "No human chest resonance or vocal tract airflow — the sound is synthesized, not spoken.",
                  code: 'E2 · confidence 99.1%',
                  valClass: 'text-fg-tertiary',
                },
                {
                  label: "Doesn't match the real voiceprint",
                  desc: 'Compared against the enrolled CFO voiceprint, the biometric distance is far outside tolerance.',
                  code: 'E4 · mismatch > 0.72',
                  valClass: 'text-red-600',
                },
              ].map((item) => (
                <div key={item.label} className="border border-border/80 p-3 bg-background/60 space-y-1">
                  <p className="text-sm font-bold text-fg">{item.label}</p>
                  <p className="text-xs text-fg-secondary leading-normal">{item.desc}</p>
                  <span className={`font-mono text-[0.625rem] uppercase ${item.valClass}`}>{item.code}</span>
                </div>
              ))}
            </div>

            <div className="border-t border-border pt-4 flex items-center justify-between font-mono text-xs">
              <span className="text-fg-tertiary text-micro-label uppercase">VERDICT STATUS</span>
              <span className="font-bold text-red-600 bg-red-50 px-2.5 py-0.5 border border-red-200">
                SYNTHETIC CLONE DETECTED // MANDATED HOLD
              </span>
            </div>
          </div>
        </div>

        {/* Progression Transformation Ribbon */}
        <div className="mt-12 sm:mt-16 pt-6 border-t border-border flex flex-col sm:flex-row sm:items-center justify-between gap-4 font-mono text-xs">
          <span className="text-micro-label uppercase text-fg-tertiary">
            SECURITY TRANSFORMATION CYCLE
          </span>

          <div className="flex items-center gap-3 sm:gap-6 font-bold text-fg uppercase">
            <span className="text-fg-tertiary">SUBJECTIVE TRUST</span>
            <ArrowRight className="h-4 w-4 text-border-strong" />
            <span className="text-amber-600">ACOUSTIC INTAKE</span>
            <ArrowRight className="h-4 w-4 text-border-strong" />
            <span className="text-emerald-600">DETERMINISTIC VERIFICATION</span>
          </div>
        </div>
      </div>
    </section>
  );
};

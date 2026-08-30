import React from 'react';
import { ArrowRight } from 'lucide-react';

export const ProblemSection: React.FC = () => {
  return (
    <section id="problem" className="py-16 sm:py-24 border-b border-border">
      <div className="max-w-[1500px] mx-auto px-4 sm:px-8">
        {/* Section Header */}
        <div className="flex items-center justify-between border-b border-border pb-4 font-mono text-micro-label uppercase text-fg-tertiary">
          <span>01 // THREAT LANDSCAPE</span>
          <span>HUMAN PERCEPTION VS. SIGNAL FORENSICS</span>
        </div>

        {/* Giant Editorial Statement */}
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

        {/* What a Human Hears vs What Symphony Hears (Contrast Comparison) */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-16 border-t border-border pt-12">
          {/* Left: What a Human Hears */}
          <div className="lg:col-span-5 space-y-8">
            <div>
              <span className="font-mono text-micro-label uppercase text-amber-600 font-bold block mb-2">
                WHAT A HUMAN HEARS
              </span>
              <p className="font-mono text-xs text-fg-tertiary uppercase tracking-wider">
                SUBJECTIVE PERCEPTION // TRUST HEURISTIC
              </p>
            </div>

            <blockquote className="border-l-2 border-amber-500 pl-6 py-2">
              <p className="font-mono text-2xl sm:text-3xl text-fg font-bold tracking-tight">
                “Sounds like the CFO.”
              </p>
            </blockquote>

            <p className="text-sm sm:text-base text-fg-secondary leading-relaxed">
              Human listeners rely on familiar vocal inflection and emotional tone. In high-value authorization calls, urgency triggers cognitive bias, accepting timbre similarity as verified proof.
            </p>

            <div className="flex flex-wrap gap-2 pt-2 font-mono text-micro-label text-fg-tertiary">
              <span className="border border-border bg-surface px-3 py-1">ZERO-SHOT CLONING VULNERABLE</span>
              <span className="border border-border bg-surface px-3 py-1">UNCHECKED AUTHORIZATION</span>
            </div>
          </div>

          {/* Center Divider / Progression */}
          <div className="hidden lg:flex lg:col-span-1 items-center justify-center">
            <div className="h-full w-px bg-border flex flex-col justify-around items-center py-12">
              <span className="bg-background px-1 font-mono text-[0.625rem] text-fg-muted uppercase rotate-90">
                DISCRIMINANT
              </span>
            </div>
          </div>

          {/* Right: What Symphony Hears */}
          <div className="lg:col-span-6 space-y-6">
            <div>
              <span className="font-mono text-micro-label uppercase text-fg-primary font-bold block mb-2">
                WHAT SYMPHONY HEARS
              </span>
              <p className="font-mono text-xs text-fg-tertiary uppercase tracking-wider">
                MULTIDIMENSIONAL NEURAL FORENSICS
              </p>
            </div>

            <div className="divide-y divide-border border-y border-border">
              {[
                {
                  id: '01',
                  title: 'ACOUSTIC EVIDENCE',
                  detail: 'Neural models detect phase discontinuities, spectral tilt, and vocoder synthesis artifacts invisible to human ears.',
                },
                {
                  id: '02',
                  title: 'SPEAKER EVIDENCE',
                  detail: 'WavLM-SV calculates 512-dim cosine distance against enrolled biometric voiceprints to catch impersonators.',
                },
                {
                  id: '03',
                  title: 'TEMPORAL ACCUMULATION',
                  detail: 'Bayesian belief accumulates across 25ms audio frames over time, establishing statistical confidence.',
                },
                {
                  id: '04',
                  title: 'CONTEXTUAL SYNTHESIS',
                  detail: 'Acoustic findings are weighted against transaction amount tier, payee novelty, and refusal behaviors.',
                },
              ].map((row) => (
                <div key={row.id} className="py-4 sm:py-5 flex items-start gap-4 sm:gap-6 group">
                  <span className="font-mono text-xs font-bold text-fg-primary shrink-0 mt-0.5">
                    {row.id}
                  </span>
                  <div>
                    <h4 className="font-mono text-sm font-bold text-fg uppercase tracking-wider">
                      {row.title}
                    </h4>
                    <p className="mt-1 text-xs sm:text-sm text-fg-secondary leading-relaxed">
                      {row.detail}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Progression Transformation Ribbon */}
        <div className="mt-16 sm:mt-24 pt-8 border-t border-border flex flex-col sm:flex-row sm:items-center justify-between gap-6">
          <span className="font-mono text-micro-label uppercase text-fg-tertiary">
            SECURITY TRANSFORMATION CYCLE
          </span>

          <div className="flex items-center gap-3 sm:gap-6 font-mono text-xs sm:text-sm font-bold text-fg uppercase">
            <span className="text-fg-tertiary">TRUST</span>
            <ArrowRight className="h-4 w-4 text-border-strong" />
            <span className="text-amber-600">QUESTION</span>
            <ArrowRight className="h-4 w-4 text-border-strong" />
            <span className="text-fg-primary">VERIFY</span>
          </div>
        </div>
      </div>
    </section>
  );
};

import React from 'react';
import { useSession } from '../state/useSession';

export const PipelineSection: React.FC = () => {
  const { state } = useSession();
  const decision = state.decision;
  const isStreaming = Boolean(state.sessionId && state.sourceType);

  const activeStage = decision
    ? 5
    : state.evidence
    ? 3
    : isStreaming
    ? 2
    : state.sessionId
    ? 1
    : 0;

  const stages = [
    {
      num: '01',
      name: 'INTAKE',
      sub: 'L1 Telephony Ingestion',
      desc: '16 kHz Mono PCM normalization & 25ms framing.',
    },
    {
      num: '02',
      name: 'ANALYSIS',
      sub: 'L2 Signal Conditioning',
      desc: 'Audio quality estimation (q_call) & spectral features.',
    },
    {
      num: '03',
      name: 'FORENSICS',
      sub: 'L3 Model Ensemble',
      desc: 'E1–E6 neural classifiers evaluating acoustic spoof markers.',
    },
    {
      num: '04',
      name: 'FUSION',
      sub: 'L4 Context Synthesis',
      desc: 'Bayesian accumulation weighted with transaction novelty.',
    },
    {
      num: '05',
      name: 'DECISION',
      sub: 'L5 Policy Engine',
      desc: 'Deterministic rules: Allow, Step-Up, or Mandated Hold.',
    },
  ];

  return (
    <section id="pipeline" className="py-16 sm:py-24 border-b border-border">
      <div className="max-w-[1500px] mx-auto px-4 sm:px-8">
        {/* Section Header */}
        <div className="flex items-center justify-between border-b border-border pb-4 font-mono text-micro-label uppercase text-fg-tertiary">
          <span>03 // PIPELINE ARCHITECTURE</span>
          <span>L1–L5 DETERMINISTIC FLOW</span>
        </div>

        {/* Giant Section Headline */}
        <div className="mt-8 sm:mt-12 mb-12 sm:mb-16">
          <h2 className="display-giant text-fg font-black tracking-tight leading-[0.94]">
            FIVE STAGES.<br />
            <span className="serif-italic font-normal">ZERO AMBIGUITY.</span>
          </h2>
          <p className="mt-5 text-lg sm:text-xl text-fg-secondary max-w-2xl font-normal leading-relaxed">
            From raw audio ingestion to cryptographic decision assurance, each architectural stage
            enforces strict mathematical separation of concerns.
          </p>
        </div>

        {/* Minimal Horizontal Line Pipeline */}
        <div className="relative pt-6">
          {/* Continuous Connecting Line */}
          <div className="hidden lg:block absolute top-[52px] left-0 right-0 h-px bg-border z-0" />

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-10 lg:gap-8 relative z-10">
            {stages.map((st, idx) => {
              const isPassed = activeStage >= idx + 1;
              const isCurrent = activeStage === idx + 1;

              return (
                <div key={st.num} className="space-y-4 group">
                  {/* Large Number Top Marker */}
                  <div className="flex items-center gap-3">
                    <span
                      className={`font-mono text-4xl sm:text-5xl font-black tracking-tighter transition-colors ${
                        isCurrent
                          ? 'text-fg-primary'
                          : isPassed
                          ? 'text-emerald-600'
                          : 'text-fg-muted group-hover:text-fg'
                      }`}
                    >
                      {st.num}
                    </span>
                    <span className="h-2 w-2 rounded-full bg-border group-hover:bg-fg transition-colors" />
                  </div>

                  {/* Stage Details */}
                  <div className="space-y-1.5 pt-2 border-t lg:border-t-0 border-border">
                    <h3 className="font-mono text-sm sm:text-base font-bold text-fg tracking-wider uppercase">
                      {st.name}
                    </h3>
                    <p className="font-mono text-micro-label text-fg-tertiary uppercase">
                      {st.sub}
                    </p>
                    <p className="text-xs sm:text-sm text-fg-secondary leading-relaxed pt-1">
                      {st.desc}
                    </p>
                  </div>

                  {/* Active Status Flag */}
                  <div className="font-mono text-micro-label uppercase pt-1">
                    {isCurrent ? (
                      <span className="text-fg font-bold animate-pulse">● LIVE EXECUTION</span>
                    ) : isPassed ? (
                      <span className="text-emerald-600 font-semibold">✓ VERIFIED</span>
                    ) : (
                      <span className="text-fg-muted">READY</span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
};

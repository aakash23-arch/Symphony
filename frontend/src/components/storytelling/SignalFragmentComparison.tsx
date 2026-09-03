import React from 'react';
import { TickerMarquee } from '../../design-system/TickerMarquee';
import { CountUp } from '../../design-system/CountUp';

/**
 * The headline moat, rendered as evidence: published anti-spoofing
 * architectures (AASIST, RawNet2) hold sub-1% EER on English benchmarks
 * (ASVspoof 2019) and exceed 50% EER on Indian languages without
 * adaptation — worse than a coin flip. Sourced from IndicSynth (ACL 2025)
 * benchmarking. This is the one number the whole pitch traces back to.
 */
export const SignalFragmentComparison: React.FC = () => {
  return (
    <div className="relative rounded-sm overflow-hidden border border-border bg-surface">
      <div className="absolute inset-x-0 top-0 border-b border-border py-3">
        <TickerMarquee text="ASVSPOOF 2019  INDICSYNTH  AASIST  RAWNET2  EQUAL ERROR RATE " />
      </div>

      <div className="px-8 pt-20 pb-2">
        <p className="text-xs text-fg-tertiary italic">
          Error rate = how often the detector gets it wrong. Lower is better; 50% is a coin flip.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-0">
        <div className="p-8 pt-2 border-b lg:border-b-0 lg:border-r border-border">
          <div className="font-mono text-micro-label uppercase tracking-widest text-fg-tertiary mb-4">
            On English speech (ASVspoof 2019)
          </div>
          <div className="font-mono text-6xl font-black text-state-safe">
            <CountUp to={1} prefix="<" suffix="%" />
          </div>
          <div className="font-mono text-xs text-fg-tertiary uppercase tracking-wider mt-3">
            Error rate — published AASIST / RawNet2
          </div>
        </div>

        <div className="p-8 pt-2">
          <div className="font-mono text-micro-label uppercase tracking-widest text-fg-tertiary mb-4">
            On Indian languages, no adaptation
          </div>
          <div className="font-mono text-6xl font-black text-state-critical">
            <CountUp to={50} prefix=">" suffix="%" />
          </div>
          <div className="font-mono text-xs text-fg-tertiary uppercase tracking-wider mt-3">
            Error rate — worse than a coin flip (IndicSynth benchmark)
          </div>
        </div>
      </div>

      <div className="border-t border-border p-6 flex items-center justify-between gap-4 flex-wrap">
        <p className="text-sm text-fg-secondary max-w-xl">
          State-of-the-art architectures fail dramatically when tested against real-world Indian accents and multilingual code-switching. Symphony is engineered with Indic-language fine-tuning specifically to eliminate this critical vulnerability.
        </p>
        <span className="font-mono text-xs text-fg-tertiary uppercase tracking-widest shrink-0">
          Source: IndicSynth Benchmark (ACL 2025)
        </span>
      </div>
    </div>
  );
};

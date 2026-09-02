import React, { useRef } from 'react';
import { motion, useScroll, useTransform } from 'framer-motion';
import { StickyNarrative } from '../design-system/StickyNarrative';
import { TickerMarquee } from '../design-system/TickerMarquee';
import { SignalStabilityGraph, SpectralProfileGraph, ModelAgreementGraph } from '../components/visualizations/EmbeddedGraphs';

export const TransformationSection: React.FC = () => {
  const sectionRef = useRef<HTMLElement>(null);
  const { scrollYProgress } = useScroll({
    target: sectionRef,
    offset: ["start center", "end center"]
  });

  const step1Opacity = useTransform(scrollYProgress, [0, 0.2, 0.3], [0, 1, 0.2]);
  const step2Opacity = useTransform(scrollYProgress, [0.3, 0.5, 0.6], [0, 1, 0.2]);
  const step3Opacity = useTransform(scrollYProgress, [0.6, 0.8, 1], [0, 1, 1]);

  const narrative = (
    <div className="pt-12 lg:pt-16">
      <div className="font-mono text-micro-label uppercase tracking-widest text-fg-tertiary mb-6">
        <span>PHASE II // ANALYSIS</span>
      </div>
      <h2 className="display-lg text-fg font-bold tracking-tight leading-[1.1] max-w-md mb-6 uppercase">
        A clone is more than<br />
        <span className="serif-italic font-normal normal-case text-fg-secondary">a voiceprint match.</span>
      </h2>
      <p className="text-xl text-fg-secondary leading-relaxed max-w-md">
        Six independent experts score every frame in parallel. An attacker who defeats one hasn't defeated the rest —
        <span className="serif-italic font-normal"> independence is the product.</span>
      </p>
    </div>
  );

  const steps = [
    {
      id: "E1",
      title: "SPECTRO-TEMPORAL",
      tagline: "Listens for tell-tale frequency patterns",
      desc: "Trained to spot the frequency fingerprints AI voice generators leave behind — though it struggles on low-quality 8kHz calls, so it's never used alone.",
      opacity: step1Opacity,
      graph: <SignalStabilityGraph />
    },
    {
      id: "E2",
      title: "RAW WAVEFORM",
      tagline: "Reads the sound wave directly, no shortcuts",
      desc: "Works straight off the raw audio instead of a processed version of it — which is exactly why it holds up best on noisy, low-quality phone calls.",
      opacity: step2Opacity,
      graph: <SpectralProfileGraph />
    },
    {
      id: "E3",
      title: "SSL FOUNDATION",
      tagline: "Pretrained across many languages",
      desc: "Built on a model already fluent in dozens of languages — the main reason this system holds up on Indian speech where others fall apart.",
      opacity: step3Opacity,
      graph: <ModelAgreementGraph />
    }
  ];

  const content = (
    <div className="space-y-10 py-12 lg:py-16">
      {steps.map((step) => (
        <motion.div 
          key={step.id} 
          style={{ opacity: step.opacity }}
          className="rounded-sm flex gap-8 items-start border border-border bg-surface p-8 shadow-sm"
        >
          <div className="font-mono text-xl text-fg-tertiary pt-1">{step.id}</div>
          <div className="space-y-4 w-full">
            <div className="flex justify-between items-start gap-4">
              <div>
                <h3 className="font-mono text-2xl font-bold uppercase text-fg">{step.title}</h3>
                <p className="text-sm text-fg-secondary italic mt-0.5">{step.tagline}</p>
              </div>
              {step.graph}
            </div>
            <p className="text-lg text-fg-secondary">{step.desc}</p>
            {/* Visual element placeholder for Phase 6 */}
            <div className="h-16 w-full border border-border bg-background mt-6 relative overflow-hidden flex items-center px-4">
              <motion.div 
                className="h-0.5 bg-fg absolute left-0 top-1/2 -translate-y-1/2"
                style={{ width: "100%", scaleX: step.opacity, transformOrigin: "left" }}
              />
            </div>
          </div>
        </motion.div>
      ))}
    </div>
  );

  return (
    <section
      ref={sectionRef}
      className="relative px-4 sm:px-8 py-16 border-b border-border bg-background overflow-hidden"
    >
      <div className="border-b border-border py-3 mb-10">
        <TickerMarquee text="16KHZ PCM  SPECTRAL TILT  VOCODER ARTIFACT  PHASE COHERENCE  FRAME 402  " />
      </div>
      <div className="max-w-[1400px] mx-auto w-full">
        <StickyNarrative
          narrative={narrative} 
          content={content} 
          stickyTopOffset="top-32"
        />
      </div>
    </section>
  );
};


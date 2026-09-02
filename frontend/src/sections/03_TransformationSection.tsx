import React, { useRef } from 'react';
import { motion, useScroll, useTransform } from 'framer-motion';
import { StickyNarrative } from '../design-system/StickyNarrative';
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
    <div className="pt-24 lg:pt-32">
      <div className="font-mono text-micro-label uppercase tracking-widest text-fg-tertiary mb-6">
        <span>03 // THE TRANSFORMATION</span>
      </div>
      <h2 className="display-lg text-fg font-bold tracking-tight leading-[1.1] max-w-md mb-6">
        WE DON'T TRUST <br/>THE VOICE.
      </h2>
      <p className="text-xl text-fg-secondary leading-relaxed max-w-md">
        We verify the signal. Data becomes <span className="serif-italic font-normal">evidence</span> through a rigorous neural extraction pipeline.
      </p>
    </div>
  );

  const steps = [
    {
      id: "01",
      title: "INPUT",
      desc: "16kHz PCM stream intercepted.",
      opacity: step1Opacity,
      graph: <SignalStabilityGraph />
    },
    {
      id: "02",
      title: "ANALYSIS",
      desc: "Neural extraction of phase and spectral tilt.",
      opacity: step2Opacity,
      graph: <SpectralProfileGraph />
    },
    {
      id: "03",
      title: "EVIDENCE",
      desc: "Vocoder artifacts detected in frame 402.",
      opacity: step3Opacity,
      graph: <ModelAgreementGraph />
    }
  ];

  const content = (
    <div className="space-y-24 py-32 lg:py-48">
      {steps.map((step) => (
        <motion.div 
          key={step.id} 
          style={{ opacity: step.opacity }}
          className="flex gap-8 items-start border border-border bg-surface p-8 shadow-sm"
        >
          <div className="font-mono text-xl text-fg-tertiary pt-1">{step.id}</div>
          <div className="space-y-4 w-full">
            <div className="flex justify-between items-start">
              <h3 className="font-mono text-2xl font-bold uppercase text-fg">{step.title}</h3>
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
      className="relative min-h-[150vh] px-4 sm:px-8 border-b border-border bg-background"
    >
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


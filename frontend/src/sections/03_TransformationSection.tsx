import React, { useRef } from 'react';
import { motion, useScroll, useTransform } from 'framer-motion';

export const TransformationSection: React.FC = () => {
  const sectionRef = useRef<HTMLElement>(null);
  const { scrollYProgress } = useScroll({
    target: sectionRef,
    offset: ["start center", "end center"]
  });

  // A sequence animation as the user scrolls
  const step1Opacity = useTransform(scrollYProgress, [0, 0.2, 0.3], [0, 1, 0.2]);
  const step2Opacity = useTransform(scrollYProgress, [0.3, 0.5, 0.6], [0, 1, 0.2]);
  const step3Opacity = useTransform(scrollYProgress, [0.6, 0.8, 1], [0, 1, 1]);

  const steps = [
    {
      id: "01",
      title: "INPUT",
      desc: "16kHz PCM stream intercepted.",
      opacity: step1Opacity,
    },
    {
      id: "02",
      title: "ANALYSIS",
      desc: "Neural extraction of phase and spectral tilt.",
      opacity: step2Opacity,
    },
    {
      id: "03",
      title: "EVIDENCE",
      desc: "Vocoder artifacts detected in frame 402.",
      opacity: step3Opacity,
    }
  ];

  return (
    <section 
      ref={sectionRef}
      className="relative min-h-[150vh] py-32 px-4 sm:px-8 border-b border-border bg-background"
    >
      <div className="sticky top-1/3 max-w-[1200px] mx-auto w-full grid grid-cols-1 lg:grid-cols-2 gap-16">
        
        <div>
          <div className="font-mono text-micro-label uppercase tracking-widest text-fg-tertiary mb-6">
            <span>03 // THE TRANSFORMATION</span>
          </div>
          <h2 className="display-lg text-fg font-bold tracking-tight leading-[1.1] max-w-md">
            Data becomes <span className="serif-italic font-normal">evidence.</span>
          </h2>
        </div>

        <div className="space-y-12">
          {steps.map((step) => (
            <motion.div 
              key={step.id} 
              style={{ opacity: step.opacity }}
              className="flex gap-8 items-start"
            >
              <div className="font-mono text-xl text-fg-tertiary pt-1">{step.id}</div>
              <div className="space-y-2">
                <h3 className="font-mono text-2xl font-bold uppercase">{step.title}</h3>
                <p className="text-lg text-fg-secondary">{step.desc}</p>
                <div className="h-0.5 w-full bg-border mt-4">
                  <motion.div 
                    className="h-full bg-fg"
                    style={{ scaleX: step.opacity, transformOrigin: "left" }}
                  />
                </div>
              </div>
            </motion.div>
          ))}
        </div>

      </div>
    </section>
  );
};

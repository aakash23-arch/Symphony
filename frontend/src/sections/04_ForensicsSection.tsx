import React, { useRef } from 'react';
import { motion, useScroll, useTransform } from 'framer-motion';

export const ForensicsSection: React.FC = () => {
  const sectionRef = useRef<HTMLElement>(null);
  const { scrollYProgress } = useScroll({
    target: sectionRef,
    offset: ["start end", "end start"]
  });

  const layerY = useTransform(scrollYProgress, [0, 1], [100, -100]);

  return (
    <section 
      ref={sectionRef}
      className="relative min-h-[100vh] flex items-center py-32 px-4 sm:px-8 border-b border-border bg-surface-elevated overflow-hidden"
    >
      <div className="max-w-[1200px] mx-auto w-full grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
        
        <div className="space-y-8 z-10">
          <div className="font-mono text-micro-label uppercase tracking-widest text-fg-tertiary">
            <span>04 // THE FORENSICS</span>
          </div>
          
          <h2 className="display-lg text-fg font-bold tracking-tight leading-[1.1]">
            Beneath the <br/>
            <span className="serif-italic font-normal">surface.</span>
          </h2>

          <p className="text-lg text-fg-secondary max-w-sm">
            We don't just listen. We dissect the signal across 6 distinct neural models, searching for mathematical impossibilities in the voice.
          </p>
        </div>

        <motion.div 
          style={{ y: layerY }}
          className="relative h-[600px] w-full flex flex-col justify-center items-end"
        >
          {/* Abstract Forensic Layers */}
          {[1, 2, 3].map((layer) => (
            <motion.div
              key={layer}
              initial={{ x: 50, opacity: 0 }}
              whileInView={{ x: 0, opacity: 1 }}
              transition={{ delay: layer * 0.1, duration: 0.8 }}
              className="w-full max-w-md h-32 border border-border bg-surface mb-[-40px] shadow-sm flex flex-col justify-between p-4 transform hover:-translate-x-4 transition-transform"
              style={{ zIndex: 10 - layer }}
            >
              <div className="font-mono text-xs text-fg-tertiary uppercase">
                Layer 0{layer}
              </div>
              <div className="font-mono text-sm font-bold uppercase">
                {layer === 1 ? 'Acoustic Discontinuities' : layer === 2 ? 'Spectral Tilt Anomalies' : 'Vocoder Artifacts'}
              </div>
              <div className="w-full h-1 bg-border-strong overflow-hidden">
                <div className="h-full bg-state-uncertain w-3/4" />
              </div>
            </motion.div>
          ))}
        </motion.div>

      </div>
    </section>
  );
};

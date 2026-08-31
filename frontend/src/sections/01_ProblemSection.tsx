import React, { useRef } from 'react';
import { motion, useScroll, useTransform } from 'framer-motion';

interface ProblemSectionProps {
  onScrollToLive: () => void;
}

export const ProblemSection: React.FC<ProblemSectionProps> = ({ onScrollToLive }) => {
  const sectionRef = useRef<HTMLElement>(null);
  const { scrollYProgress } = useScroll({
    target: sectionRef,
    offset: ["start start", "end start"]
  });

  const y = useTransform(scrollYProgress, [0, 1], ["0%", "50%"]);
  const opacity = useTransform(scrollYProgress, [0, 0.8], [1, 0]);

  return (
    <section 
      ref={sectionRef}
      className="relative min-h-screen flex flex-col justify-center px-4 sm:px-8 border-b border-border overflow-hidden"
    >
      <motion.div 
        style={{ y, opacity }}
        className="max-w-[1200px] mx-auto w-full relative z-10 space-y-12"
      >
        <div className="font-mono text-micro-label uppercase tracking-widest text-fg-tertiary">
          <span>01 // THE PROBLEM</span>
        </div>

        <div className="space-y-6">
          <h1 className="display-giant text-fg font-black tracking-tight leading-[0.94] uppercase">
            A VOICE IS NO LONGER<br />
            <span className="serif-italic font-normal lowercase text-fg-secondary">proof of</span><br />
            IDENTITY.
          </h1>

          <p className="text-xl sm:text-2xl text-fg-secondary max-w-2xl font-normal leading-relaxed">
            Generative voice cloning systems reproduce acoustic timbre in seconds. 
            Human listeners cannot reliably distinguish synthetic speech under operational pressure.
          </p>
        </div>

        <div className="pt-8 flex gap-6 items-center">
          <button
            type="button"
            onClick={onScrollToLive}
            className="font-mono text-sm font-bold uppercase bg-fg text-background px-8 py-4 hover:bg-fg/90 transition-colors"
          >
            START LIVE DETECTION
          </button>
          <div className="font-mono text-xs text-fg-tertiary uppercase tracking-widest">
            SCROLL TO UNDERSTAND ↓
          </div>
        </div>
      </motion.div>
    </section>
  );
};

import React, { useRef } from 'react';
import { motion, useScroll, useTransform } from 'framer-motion';

interface DecisionSectionProps {
  onScrollToLive: () => void;
}

export const DecisionSection: React.FC<DecisionSectionProps> = ({ onScrollToLive }) => {
  const sectionRef = useRef<HTMLElement>(null);
  const { scrollYProgress } = useScroll({
    target: sectionRef,
    offset: ["start center", "end end"]
  });

  const scale = useTransform(scrollYProgress, [0, 0.8], [0.9, 1]);
  const opacity = useTransform(scrollYProgress, [0, 0.5], [0, 1]);

  return (
    <section 
      ref={sectionRef}
      className="relative min-h-[90vh] flex flex-col justify-center items-center py-32 px-4 sm:px-8 border-b border-border bg-background"
    >
      <div className="font-mono text-micro-label uppercase tracking-widest text-fg-tertiary mb-12 text-center">
        <span>05 // THE DECISION</span>
      </div>

      <motion.div 
        style={{ scale, opacity }}
        className="w-full max-w-3xl flex flex-col items-center text-center space-y-12"
      >
        <h2 className="display-giant text-fg font-black tracking-tight leading-[0.9]">
          SYNTHETIC.
        </h2>

        <div className="flex gap-4 items-center">
          <div className="h-3 w-3 bg-state-critical rounded-full animate-pulse" />
          <span className="font-mono text-xl font-bold uppercase tracking-widest text-state-critical">
            High Risk Detected
          </span>
        </div>

        <p className="text-xl text-fg-secondary max-w-xl mx-auto">
          The forensic evidence is conclusive. Trust is withdrawn. 
          The transaction is suspended automatically.
        </p>

        <div className="pt-12 border-t border-border w-full flex flex-col items-center justify-center">
          <p className="font-mono text-sm text-fg-tertiary mb-6 uppercase tracking-wider">
            Ready to test the system?
          </p>
          <button
            onClick={onScrollToLive}
            className="font-mono text-lg font-bold uppercase bg-fg text-background px-12 py-5 hover:bg-fg/90 transition-all hover:scale-105"
          >
            ENTER LIVE CONSOLE
          </button>
        </div>
      </motion.div>
    </section>
  );
};

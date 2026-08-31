import React, { useRef } from 'react';
import { motion, useScroll, useTransform } from 'framer-motion';
import { VoiceSignalMotif } from '../components/storytelling/VoiceSignalMotif';

export const SignalSection: React.FC = () => {
  const sectionRef = useRef<HTMLElement>(null);
  const { scrollYProgress } = useScroll({
    target: sectionRef,
    offset: ["start end", "end start"]
  });

  const scale = useTransform(scrollYProgress, [0, 0.5, 1], [0.8, 1, 0.9]);
  const opacity = useTransform(scrollYProgress, [0, 0.2, 0.8, 1], [0, 1, 1, 0]);
  const textY = useTransform(scrollYProgress, [0.2, 0.5], [50, 0]);

  return (
    <section 
      ref={sectionRef}
      className="relative min-h-[120vh] flex flex-col justify-center px-4 sm:px-8 border-b border-border bg-surface-subtle"
    >
      <div className="max-w-[1200px] mx-auto w-full grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
        
        <motion.div 
          style={{ opacity, y: textY }}
          className="space-y-6"
        >
          <div className="font-mono text-micro-label uppercase tracking-widest text-fg-tertiary">
            <span>02 // THE SIGNAL</span>
          </div>

          <h2 className="display-xl text-fg font-black tracking-tight leading-[1]">
            LISTEN <br />
            <span className="serif-italic font-normal text-fg-secondary">closer.</span>
          </h2>

          <p className="text-lg sm:text-xl text-fg-secondary font-normal leading-relaxed max-w-md">
            Before words are understood, a voice is merely an acoustic waveform. We intercept this raw signal before it reaches human ears.
          </p>
        </motion.div>

        <motion.div 
          style={{ scale, opacity }}
          className="flex justify-center items-center h-[500px] w-full"
        >
          {/* We reuse the existing motif but scale it up drastically to carry the visual weight */}
          <div className="transform scale-150 origin-center">
            <VoiceSignalMotif variant="hero" state="listening" />
          </div>
        </motion.div>

      </div>
    </section>
  );
};

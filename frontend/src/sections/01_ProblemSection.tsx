import React, { useRef } from 'react';
import { motion, useScroll, useTransform } from 'framer-motion';
import { CursorMatrixField } from '../design-system/CursorMatrixField';
import { DecryptText } from '../design-system/DecryptText';
import { SignalFragmentComparison } from '../components/storytelling/SignalFragmentComparison';

interface ProblemSectionProps {
  onScrollToLive: () => void;
}

const Pill: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <span className="inline-block rounded-sm border border-background/20 bg-background/10 px-2.5 py-1 font-mono text-[0.625rem] font-bold uppercase tracking-widest text-background">
    {children}
  </span>
);

export const ProblemSection: React.FC<ProblemSectionProps> = ({ onScrollToLive }) => {
  const sectionRef = useRef<HTMLElement>(null);
  const { scrollYProgress } = useScroll({
    target: sectionRef,
    offset: ["start start", "end start"]
  });

  const opacity = useTransform(scrollYProgress, [0, 0.8], [1, 0]);

  return (
    <>
      <section
        id="hero"
        ref={sectionRef}
        className="relative min-h-[92vh] flex flex-col justify-center px-4 sm:px-8 overflow-hidden bg-fg text-background"
      >
        <CursorMatrixField />

        <motion.div
          style={{ opacity }}
          className="max-w-[1200px] mx-auto w-full relative z-10 space-y-8"
        >
          <div className="flex flex-wrap items-center gap-3">
            <Pill>Forensic-Grade AI</Pill>
            <span className="serif-italic normal-case text-sm text-background/60">/Introducing/</span>
          </div>

          <div className="text-2xl sm:text-3xl font-black tracking-tight text-background">
            SYMPHONY
          </div>

          <h1 className="display-giant font-black tracking-tight leading-[0.94] uppercase text-background">
            <DecryptText text="A VOICE IS NO LONGER" />
            <br />
            <DecryptText
              text="proof of"
              delayMs={260}
              className="serif-italic font-normal lowercase text-background/60"
            />
            <br />
            <DecryptText text="IDENTITY." delayMs={520} />
          </h1>

          <p className="text-xl sm:text-2xl text-background/70 max-w-2xl font-normal leading-relaxed">
            A real-time voice-security layer that catches cloned-voice fraud calls as they happen —
            tuned for Indian languages and telephony, where the published state of the art fails outright.
          </p>

          <div className="pt-4 flex flex-wrap gap-6 items-center">
            <button
              type="button"
              onClick={onScrollToLive}
              className="rounded-sm font-mono text-sm font-bold uppercase bg-accent-bright text-accent-bright-ink px-8 py-4 hover:bg-accent-bright-hover transition-all duration-200 ease-out hover:scale-[1.03] active:scale-[0.98]"
            >
              START LIVE DETECTION →
            </button>
            <div className="font-mono text-xs text-background/50 uppercase tracking-widest">
              SCROLL TO UNDERSTAND ↓
            </div>
          </div>
        </motion.div>
      </section>

      <section className="relative px-4 sm:px-8 py-20 border-b border-border">
        <div className="max-w-[1200px] mx-auto w-full">
          <div className="space-y-3 mb-8 text-center">
            <h2 className="display-lg text-fg font-bold tracking-tight leading-[1.1] uppercase">
              English benchmarks say <span className="serif-italic font-normal normal-case text-state-safe">solved.</span><br />
              Indian speech says <span className="serif-italic font-normal normal-case text-state-critical">otherwise.</span>
            </h2>
            <p className="text-lg text-fg-secondary max-w-xl mx-auto">
              Leading anti-spoofing models score sub-1% EER on English benchmarks — and exceed 50% on Indian
              languages without adaptation. That published gap is what Symphony is built to close.
            </p>
          </div>
          <SignalFragmentComparison />
        </div>
      </section>
    </>
  );
};

import React, { useRef } from 'react';
import { motion, useScroll, useTransform } from 'framer-motion';

interface DecisionSectionProps {
  onScrollToLive: () => void;
}

const TIERS = [
  { tier: '0', label: 'Just checking balance', action: 'Log only', tone: 'border-border text-fg-tertiary' },
  { tier: '1', label: 'Viewing account info', action: 'Warn', tone: 'border-border text-fg-secondary' },
  { tier: '2', label: 'Changing a password', action: 'Verify identity', tone: 'border-state-medium/50 text-state-medium' },
  { tier: '3', label: 'Sending money', action: 'Verify identity', tone: 'border-state-high/50 text-state-high' },
  { tier: '4', label: 'Big-value transfer', action: 'Hold & call back', tone: 'border-state-critical bg-state-critical/5 text-state-critical' },
];

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
      className="relative flex flex-col justify-center items-center py-20 px-4 sm:px-8 border-b border-border bg-background"
    >
      <div className="font-mono text-micro-label uppercase tracking-widest text-fg-tertiary mb-8 text-center">
        <span>PHASE IV // DECISION</span>
      </div>

      <motion.div
        style={{ scale, opacity }}
        className="w-full max-w-3xl flex flex-col items-center text-center space-y-10"
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
          Symphony protects <span className="serif-italic font-normal text-fg">an action, not an audio file.</span> The same
          voice-risk score means something different for a balance inquiry than a ₹5 crore transfer.
        </p>

        <div className="w-full max-w-2xl">
          <div className="font-mono text-micro-label uppercase tracking-widest text-fg-tertiary mb-3">
            Same risk score, different response — it depends what's being asked
          </div>
          <div className="flex flex-wrap items-stretch justify-center gap-1.5">
            {TIERS.map((t, i) => (
              <React.Fragment key={t.tier}>
                <div className={`rounded-sm border ${t.tone} px-3 py-2.5 min-w-[7rem] text-center bg-surface`}>
                  <div className="font-mono text-lg font-black">{t.tier}</div>
                  <div className="font-mono text-[0.625rem] uppercase tracking-wide mt-0.5">{t.label}</div>
                  <div className="font-mono text-[0.625rem] font-bold uppercase mt-1 opacity-80">{t.action}</div>
                </div>
                {i < TIERS.length - 1 && (
                  <span className="font-mono text-fg-tertiary self-center text-sm">→</span>
                )}
              </React.Fragment>
            ))}
          </div>
        </div>

        <div className="pt-4 border-t border-border w-full flex flex-col items-center justify-center">
          <p className="font-mono text-sm text-fg-tertiary mb-6 uppercase tracking-wider">
            Ready to test the system?
          </p>
          <button
            onClick={onScrollToLive}
            className="rounded-sm font-mono text-lg font-bold uppercase bg-fg text-background px-12 py-5 hover:bg-fg/90 transition-all duration-200 ease-out hover:scale-[1.03] active:scale-[0.98]"
          >
            ENTER LIVE CONSOLE
          </button>
        </div>
      </motion.div>
    </section>
  );
};

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

export const FaqSection: React.FC = () => {
  const faqs = [
    {
      q: "What's actually new here?",
      a: "No single component is unprecedented — spectral classifiers and speaker verification both exist. What's new is combining them into a real-time system built specifically against the published finding that leading detectors exceed 50% EER on Indian languages, with segment-level localization and a code-switch-stable score. The novelty is the combination and the evaluation protocol."
    },
    {
      q: "Why six experts instead of one model?",
      a: "Different experts fail on different things. An attacker who defeats the spectral classifier hasn't defeated the raw-waveform or speaker-verification branch. Independence is the product."
    },
    {
      q: "How fast is a decision?",
      a: "A provisional risk update publishes in under 500ms. A trustworthy call-level verdict needs 1–2 seconds of accumulated speech — sub-100ms inference and reliable evidence are different things, and we say so explicitly."
    },
    {
      q: "What does it not catch yet?",
      a: "Very short utterances (under 1 second) and adversarially post-processed clones remain the weakest cases. We'd rather say so than overclaim."
    },
    {
      q: "Is every decision auditable?",
      a: "Yes. Every high-risk verdict carries the per-expert scores, flagged time spans, and context features behind it — an evidence record, not just a label."
    }
  ];

  const [openIndex, setOpenIndex] = useState<number | null>(0);

  return (
    <section id="faq" className="w-full py-16 px-4 sm:px-8 border-b border-border bg-background">
      <div className="max-w-[800px] mx-auto space-y-8">
        <div className="text-center space-y-3 mb-10">
          <div className="font-mono text-micro-label uppercase tracking-widest text-fg-tertiary">
            FREQUENTLY ASKED QUESTIONS
          </div>
          <h2 className="text-3xl font-bold tracking-tight text-fg">
            Technical Inquiries.
          </h2>
        </div>

        <div className="border-t border-border">
          {faqs.map((faq, i) => {
            const isOpen = openIndex === i;
            return (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 10 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.05 }}
                className="border-b border-border"
              >
                <button
                  type="button"
                  onClick={() => setOpenIndex(isOpen ? null : i)}
                  aria-expanded={isOpen}
                  className="w-full flex items-center justify-between gap-6 py-6 text-left"
                >
                  <span className="font-mono text-sm font-bold uppercase text-fg">{faq.q}</span>
                  <span className="font-mono text-xl text-fg-tertiary shrink-0">
                    {isOpen ? '−' : '+'}
                  </span>
                </button>
                <AnimatePresence initial={false}>
                  {isOpen && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
                      className="overflow-hidden"
                    >
                      <p className="pb-6 text-base text-fg-secondary leading-relaxed max-w-xl">
                        {faq.a}
                      </p>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
};

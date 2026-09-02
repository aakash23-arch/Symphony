import React from 'react';
import { motion } from 'framer-motion';

export const FaqSection: React.FC = () => {
  const faqs = [
    {
      q: "What types of signals can Symphony detect?",
      a: "Symphony detects deepfakes, TTS synthesis, voice conversion, and replay attacks by analyzing spectral, temporal, and prosodic artifacts that are invisible to the human ear."
    },
    {
      q: "How does it differ from traditional security?",
      a: "Traditional security relies on what is said (passwords, pins). Symphony verifies how it is said, validating the physical properties of the voice signal itself."
    },
    {
      q: "Can it run in real-time?",
      a: "Yes. The pipeline is optimized for extremely low latency, providing continuous risk assessment on live audio streams."
    }
  ];

  return (
    <section id="faq" className="w-full py-24 px-4 sm:px-8 border-b border-border bg-background">
      <div className="max-w-[800px] mx-auto space-y-12">
        <div className="text-center space-y-4 mb-16">
          <div className="font-mono text-micro-label uppercase tracking-widest text-fg-tertiary">
            FREQUENTLY ASKED QUESTIONS
          </div>
          <h2 className="text-3xl font-bold tracking-tight text-fg">
            Technical Inquiries.
          </h2>
        </div>

        <div className="space-y-8">
          {faqs.map((faq, i) => (
            <motion.div 
              key={i}
              initial={{ opacity: 0, y: 10 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
              className="border-b border-border pb-6"
            >
              <h3 className="font-mono text-sm font-bold uppercase text-fg mb-3">{faq.q}</h3>
              <p className="text-base text-fg-secondary leading-relaxed">{faq.a}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
};

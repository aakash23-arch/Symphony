import React, { useState } from 'react';
import { Plus, Minus } from 'lucide-react';

interface FaqItem {
  id: string;
  question: string;
  answer: string;
}

const FAQS: FaqItem[] = [
  {
    id: 'faq-01',
    question: 'What is Symphony?',
    answer:
      'Symphony is a real-time voice integrity and impersonation defense system. It continuously analyzes incoming call audio, evaluates it against six neural forensic models, correlates call behavior and transaction risk, and executes a deterministic action: allow, step-up verify, or hold.',
  },
  {
    id: 'faq-02',
    question: 'How does Symphony detect AI-generated or cloned voice?',
    answer:
      'Rather than relying on human ear perception or a single classifier, Symphony inspects the audio across six independent forensic dimensions — vocoder synthesis artifacts, waveform structure, latent speech patterns, speaker biometric voiceprint, prosody, and physical playback liveness — so a clone has to fool all six at once.',
  },
  {
    id: 'faq-03',
    question: 'How does Symphony protect a transaction?',
    answer:
      'When synthetic-voice probability or contextual risk thresholds are exceeded during a high-stakes call — for example a large wire request to an unfamiliar payee — Symphony triggers an immediate disbursement hold, freezing the transfer until it clears out-of-band verification.',
  },
  {
    id: 'faq-04',
    question: 'What happens when the evidence is uncertain?',
    answer:
      'When audio quality degrades or the forensic models disagree, Symphony enters a dedicated UNCERTAIN state rather than defaulting to low risk. Uncertain evidence always forces step-up verification — it is never silently treated as benign.',
  },
];

export const FaqSection: React.FC = () => {
  const [openId, setOpenId] = useState<string | null>(null);

  const toggle = (id: string) => {
    setOpenId((prev) => (prev === id ? null : id));
  };

  return (
    <section id="faq" className="w-full border-t border-border py-24 sm:py-32">
      <div className="max-w-4xl mx-auto px-4 sm:px-6">
        {/* Minimal Section Tag */}
        <div className="flex items-center justify-between border-b border-border pb-4 font-mono text-micro-label uppercase text-fg-tertiary">
          <span>FREQUENTLY ASKED QUESTIONS</span>
          <span>SYSTEM ARCHITECTURE & CAPABILITIES</span>
        </div>

        {/* Section Headline */}
        <div className="mt-8 mb-16">
          <h2 className="display-lg text-fg font-extrabold tracking-tight">
            Clear answers on <span className="serif-italic font-normal">detection, assurance</span> &amp; policy.
          </h2>
          <p className="mt-3 text-fg-secondary text-base max-w-2xl">
            Symphony adheres to strict mathematical truthfulness. No fabricated metrics, no simulated certainty, and zero synthetic interpolation.
          </p>
        </div>

        {/* Accordion List */}
        <div className="divide-y divide-border border-y border-border">
          {FAQS.map((faq, idx) => {
            const isOpen = openId === faq.id;
            return (
              <div key={faq.id} className="py-6 sm:py-8 transition-colors">
                <button
                  type="button"
                  onClick={() => toggle(faq.id)}
                  className="flex w-full items-start justify-between gap-6 text-left focus:outline-none group"
                  aria-expanded={isOpen}
                >
                  <div className="flex items-start gap-4 sm:gap-6">
                    <span className="font-mono text-xs font-semibold text-fg-tertiary shrink-0 mt-1">
                      0{idx + 1}
                    </span>
                    <span className="text-base sm:text-lg font-bold text-fg group-hover:text-fg-secondary transition-colors">
                      {faq.question}
                    </span>
                  </div>
                  <div className="shrink-0 mt-1 text-fg-secondary group-hover:text-fg transition-colors">
                    {isOpen ? (
                      <Minus className="h-4 w-4" />
                    ) : (
                      <Plus className="h-4 w-4" />
                    )}
                  </div>
                </button>

                {isOpen && (
                  <div className="mt-4 pl-8 sm:pl-12 pr-6 sm:pr-12 text-sm sm:text-base leading-relaxed text-fg-secondary font-sans animate-fade-in">
                    {faq.answer}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
};

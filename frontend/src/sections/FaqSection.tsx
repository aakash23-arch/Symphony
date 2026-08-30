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
      'Symphony is an infrastructure-grade real-time voice integrity and impersonation defense system. It continuously analyzes incoming telephony PCM audio streams, evaluates neural forensic model ensembles (E1–E6), correlates call behavior and transaction risk, and executes deterministic policy directives (Allow, Step-Up Verification, or Mandated Disbursement Hold).',
  },
  {
    id: 'faq-02',
    question: 'How does Symphony detect AI-generated or cloned voice?',
    answer:
      'Rather than relying on human ear perception or a single binary classifier, Symphony inspects acoustic signals across multiple physical dimensions: phase continuity, vocoder synthesis artifacts, time-domain waveform boundaries, self-supervised latent speech representations (SSL), speaker biometric voiceprint divergence, and prosodic dynamics.',
  },
  {
    id: 'faq-03',
    question: 'What evidence does Symphony analyse?',
    answer:
      'Symphony ingests 25ms audio frames and evaluates evidence across three unified layers: Acoustic evidence from 6 neural forensic experts (E1–E6), Call contextual telemetry (channel codec, phone number novelty, historical profile match), and Transaction telemetry (disbursement amount, beneficiary novelty, transfer urgency).',
  },
  {
    id: 'faq-04',
    question: 'How does Symphony handle uncertain evidence?',
    answer:
      'When audio quality degrades or forensic models report low confidence, Symphony enters a dedicated UNCERTAIN fail-safe state. Uncertain evidence is never collapsed into LOW risk or assumed benign; instead, it enforces out-of-band step-up authentication before funds can move.',
  },
  {
    id: 'faq-05',
    question: 'Can Symphony work with live microphone input?',
    answer:
      'Yes. In addition to reproducible pre-recorded banking test vectors, Symphony supports real-time microphone capture at 16 kHz Mono, streaming live PCM frames over WebSocket directly into the forensic inference pipeline.',
  },
  {
    id: 'faq-06',
    question: 'How does Symphony protect a transaction?',
    answer:
      'When acoustic spoof probability or contextual risk thresholds are exceeded during a high-stakes call (e.g. ₹25,00,000 wire request to an unknown payee), Symphony triggers an immediate automated disbursement freeze, preventing fund transfer until verified through an out-of-band audit reference.',
  },
  {
    id: 'faq-07',
    question: 'What happens when a forensic model is unavailable?',
    answer:
      'Symphony maintains strict model availability semantics. If a specialized neural model is offline, deferred, or uninstalled, the Bayesian belief fusion engine re-weights remaining available experts without fabricating baseline numbers or converting null telemetry into zeros.',
  },
  {
    id: 'faq-08',
    question: 'Does Symphony store raw audio?',
    answer:
      'No. Symphony processes audio frames ephemerally in volatile memory. Only cryptographic SHA-256 evidence digests, forensic feature vectors, and policy decision receipts are recorded in the tamper-evident audit chain.',
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

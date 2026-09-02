import React from 'react';
import { motion } from 'framer-motion';

const FEATURES = [
  {
    id: '01',
    title: 'Indic-Language Fusion',
    desc: 'Fine-tuned to close the published >50% EER gap that leading detectors show on Indian languages.',
  },
  {
    id: '02',
    title: 'Partial-Spoof Localization',
    desc: 'Flags the exact seconds of a call that are synthetic — not just a single verdict on the whole thing.',
  },
  {
    id: '03',
    title: 'Code-Switch Stability',
    desc: "Doesn't false-flag genuine Hindi-English speakers when a real caller switches languages mid-sentence.",
  },
];

/**
 * Numbered three-column feature grid — the project's three named moats
 * (A1 Indic gap, A3 partial-spoof localization, A2 code-switch stability).
 */
export const NarrativeFeatureGrid: React.FC = () => {
  return (
    <div>
      <div className="max-w-2xl mb-10">
        <h2 className="display-lg text-fg font-bold tracking-tight leading-[1.1] uppercase">
          Built for Indian <br />
          <span className="serif-italic font-normal lowercase text-fg-secondary">voice channels.</span>
        </h2>
        <p className="text-lg text-fg-secondary mt-4 max-w-md">
          Not another deepfake classifier — a detection layer engineered against the specific ways Indian
          telephony and languages break the published state of the art.
        </p>
      </div>

      <div className="rounded-sm overflow-hidden grid grid-cols-1 sm:grid-cols-3 gap-px bg-border border border-border">
        {FEATURES.map((f, i) => (
          <motion.div
            key={f.id}
            initial={{ opacity: 0, y: 12 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: i * 0.1 }}
            className="bg-surface p-8 space-y-4"
          >
            <div className="font-mono text-sm text-fg-tertiary">{f.id}</div>
            <h3 className="font-mono text-sm font-bold uppercase tracking-wide text-fg">
              {f.title}
            </h3>
            <p className="text-sm text-fg-secondary leading-relaxed">{f.desc}</p>
          </motion.div>
        ))}
      </div>
    </div>
  );
};

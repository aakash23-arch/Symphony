import React from 'react';
import { motion } from 'framer-motion';

const EXPERTS = [
  { id: 'E1', name: 'Spectro-temporal', hint: 'Frequency patterns' },
  { id: 'E2', name: 'Raw waveform', hint: 'Raw sound wave' },
  { id: 'E3', name: 'SSL foundation', hint: 'Multilingual model' },
  { id: 'E4', name: 'Speaker verify', hint: 'Voice match' },
  { id: 'E5', name: 'Prosody', hint: 'Rhythm & tone' },
  { id: 'E6', name: 'Replay check', hint: 'Recording detector' },
];

/**
 * Architecture diagram: six independent experts vote, one fusion stage
 * combines their votes into a single score, and a policy stage turns that
 * score into an action. Plain-language labels so a non-technical judge
 * can read the shape of the pipeline in a few seconds.
 */
export const ExpertPipelineDiagram: React.FC = () => {
  return (
    <div className="py-4">
      <div className="font-mono text-[0.625rem] uppercase tracking-widest text-fg-tertiary mb-3 text-center">
        Six independent checks, run at the same time
      </div>

      <div className="grid grid-cols-3 sm:grid-cols-6 gap-2">
        {EXPERTS.map((e, i) => (
          <motion.div
            key={e.id}
            initial={{ opacity: 0, y: 8 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: i * 0.06 }}
            className="rounded-sm border border-border bg-background p-3 text-center"
          >
            <div className="font-mono text-xs font-bold text-fg">{e.id}</div>
            <div className="font-mono text-[0.625rem] text-fg-tertiary uppercase mt-1 leading-tight">
              {e.name}
            </div>
            <div className="text-[0.625rem] text-fg-muted italic mt-1 leading-tight">
              {e.hint}
            </div>
          </motion.div>
        ))}
      </div>

      <div className="flex justify-center font-mono text-fg-tertiary text-lg my-2">↓</div>

      <div className="flex justify-center">
        <div className="rounded-sm border border-fg bg-fg text-background px-8 py-2.5 font-mono text-xs font-bold uppercase tracking-widest text-center">
          Combine — six opinions become one score
        </div>
      </div>

      <div className="flex justify-center font-mono text-fg-tertiary text-lg my-2">↓</div>

      <div className="flex justify-center">
        <div className="rounded-sm border border-accent-bright bg-accent-bright/10 text-fg px-8 py-2.5 font-mono text-xs font-bold uppercase tracking-widest text-center">
          Decide — allow, warn, verify, or block
        </div>
      </div>
    </div>
  );
};

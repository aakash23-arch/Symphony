import React from 'react';
import { NarrativeSection } from '../design-system/NarrativeSection';
import { Badge } from '../components/Badge';
import { expertNames, expertStatusTone, formatUnit } from '../lib/risk';
import { useSession } from '../state/useSession';
import { cn } from '../lib/cn';

const ALL_EXPERTS = [
  { id: 'E1', desc: 'Analyzes high-frequency phase and spectral artifacts typical of vocoder synthesis.' },
  { id: 'E2', desc: 'Direct neural analysis on raw time-domain audio samples for end-to-end classification.' },
  { id: 'E3', desc: 'WavLM / self-supervised latent representations evaluating acoustic manifold plausibility.' },
  { id: 'E4', desc: '512-dim cosine distance verification against enrolled reference voiceprints (VP-CFO-8842).' },
  { id: 'E5', desc: 'Evaluates prosodic contour, conversational turn-taking, and affective emotional tempo.' },
  { id: 'E6', desc: 'Detects physical loudspeaker playback artifacts, room impulse responses, and replay liveness.' },
];

export const ForensicLayerSection: React.FC = () => {
  const { state, health } = useSession();
  const evidence = state.evidence;

  return (
    <div id="forensics">
      <NarrativeSection
        index="04"
        title="ONE SIGNAL. MULTIPLE QUESTIONS."
        subtitle="A single audio turn is analyzed simultaneously across six orthogonal neural forensic dimensions."
        tag="L3 EXPERT ENSEMBLE"
      >
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {ALL_EXPERTS.map((exp) => {
            const expertInEvidence = evidence?.experts.find((e) => e.expert_id === exp.id);
            const healthStatus = health?.expert_models?.[exp.id]?.status ?? 'UNKNOWN';
            const status = expertInEvidence?.status ?? healthStatus;
            const p = expertInEvidence?.p ?? null;

            return (
              <div
                key={exp.id}
                className="flex flex-col justify-between rounded-2xl border border-border/80 bg-surface/90 p-5 shadow-md backdrop-blur-sm"
              >
                <div>
                  <div className="flex items-center justify-between border-b border-border/50 pb-3">
                    <div className="flex items-center gap-2">
                      <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-accent/15 font-mono text-sm font-bold text-accent">
                        {exp.id}
                      </span>
                      <span className="font-mono text-technical-value font-bold text-fg">
                        {expertNames[exp.id] ?? 'Expert Model'}
                      </span>
                    </div>
                    <Badge className={cn('text-micro-label', expertStatusTone(status))}>
                      {status}
                    </Badge>
                  </div>

                  <p className="mt-3 text-xs leading-relaxed text-fg-secondary">{exp.desc}</p>
                </div>

                <div className="mt-4 border-t border-border/40 pt-3 flex items-center justify-between font-mono text-xs">
                  <span className="text-fg-tertiary text-micro-label uppercase">P(INAUTHENTIC)</span>
                  <span className="font-bold text-fg">
                    {p !== null ? formatUnit(p) : <span className="text-fg-tertiary font-normal">NO SCORE</span>}
                  </span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Runtime Model Availability Inventory Notice */}
        <div className="mt-4 rounded-xl border border-border/70 bg-surface-elevated/40 p-3.5 flex flex-wrap items-center justify-between gap-3 font-mono text-micro-label text-fg-tertiary">
          <span>
            MODEL INVENTORY SOURCE: <strong className="text-fg">/health &amp; /evidence contracts</strong>
          </span>
          <span>ENSEMBLE REQUIRES AT LEAST ONE LIVE ACOUSTIC EXPERT</span>
        </div>
      </NarrativeSection>
    </div>
  );
};

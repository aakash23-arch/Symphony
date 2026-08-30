import React from 'react';
import { Badge } from '../Badge';
import { expertNames, expertStatusTone, formatUnit } from '../../lib/risk';
import { useSession } from '../../state/useSession';
import { cn } from '../../lib/cn';

export interface ForensicExpertMatrixProps {
  className?: string;
  showDetails?: boolean;
}

const EXPERT_CATALOG = [
  { id: 'E1', name: 'Spectro-temporal Classifier', target: 'Synthetic Phase & Vocoder Artifacts' },
  { id: 'E2', name: 'Raw Waveform Network', target: 'Time-Domain End-to-End Classification' },
  { id: 'E3', name: 'Multilingual SSL Model', target: 'WavLM Latent Manifold Acoustic Representations' },
  { id: 'E4', name: 'Speaker Biometric Verification', target: '512-dim Cosine Distance against Enrolled Voiceprint' },
  { id: 'E5', name: 'Prosodic Contour Analyzer', target: 'Turn-Taking, Emotional Rhythm & Pitch Dynamics' },
  { id: 'E6', name: 'Replay & Acoustic Liveness', target: 'Physical Loudspeaker Playback & Impulse Response' },
];

/**
 * Editorial Forensic Expert Matrix Component.
 *
 * Visualizes the 6 neural forensic models:
 * E1 ───────── status
 * E2 ───────── status
 * E3 ───────── status
 * E4 ───────── status
 * E5 ───────── status
 * E6 ───────── status
 *
 * Sourced directly from `evidence.experts` and `health.expert_models`.
 * Strict rule: Never render fabricated numbers or fake latency when absent.
 */
export const ForensicExpertMatrix: React.FC<ForensicExpertMatrixProps> = ({
  className,
  showDetails = true,
}) => {
  const { state, health } = useSession();
  const evidence = state.evidence;

  return (
    <div className={cn('space-y-3 font-mono', className)}>
      <div className="flex items-center justify-between border-b border-border/80 pb-2 text-micro-label text-fg-tertiary uppercase tracking-wider">
        <span>EXPERT ENSEMBLE (L3 FORENSICS)</span>
        <div className="flex items-center gap-4">
          <span className="hidden sm:inline">P(INAUTHENTIC)</span>
          <span className="hidden md:inline">CONFIDENCE</span>
          <span className="hidden md:inline">LATENCY</span>
          <span>STATUS</span>
        </div>
      </div>

      <div className="space-y-2.5">
        {EXPERT_CATALOG.map((item) => {
          const liveExpert = evidence?.experts.find((e) => e.expert_id === item.id);
          const healthModel = health?.expert_models?.[item.id];
          const status = liveExpert?.status ?? healthModel?.status ?? 'STANDBY';
          const p = liveExpert?.p ?? null;
          const confidence = liveExpert?.confidence ?? null;
          const latencyMs = liveExpert?.latency_ms ?? null;

          return (
            <div
              key={item.id}
              className="group relative flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border py-3.5 transition-colors hover:bg-surface-elevated last:border-0"
            >
              {/* Expert Identifier & Name */}
              <div className="flex items-center gap-3 min-w-0">
                <span className="flex h-7 w-7 shrink-0 items-center justify-center border border-border text-sm font-bold text-fg-primary">
                  {item.id}
                </span>
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-fg-primary uppercase truncate">
                      {expertNames[item.id] ?? item.name}
                    </span>
                    <span className="text-border-strong hidden sm:inline">─────────</span>
                  </div>
                  {showDetails && (
                    <p className="text-[0.6875rem] text-fg-tertiary truncate font-sans">
                      {item.target}
                    </p>
                  )}
                </div>
              </div>

              {/* Real Measurements Strip */}
              <div className="flex items-center justify-between sm:justify-end gap-5 text-xs pt-2 sm:pt-0 border-t sm:border-t-0 border-border/40">
                {/* Score */}
                <div className="text-right">
                  <span className="text-micro-label text-fg-tertiary sm:hidden block uppercase">
                    Score
                  </span>
                  <span className="font-bold tnum text-fg">
                    {p !== null ? formatUnit(p) : <span className="text-fg-tertiary font-normal">—</span>}
                  </span>
                </div>

                {/* Confidence */}
                <div className="text-right hidden md:block">
                  <span className="font-bold tnum text-fg-secondary">
                    {confidence !== null ? formatUnit(confidence) : <span className="text-fg-tertiary font-normal">—</span>}
                  </span>
                </div>

                {/* Latency */}
                <div className="text-right hidden md:block">
                  <span className="font-bold tnum text-fg-tertiary">
                    {latencyMs !== null && latencyMs > 0 ? `${latencyMs.toFixed(0)}ms` : '—'}
                  </span>
                </div>

                {/* Status Badge */}
                <Badge className={cn('text-micro-label uppercase shrink-0', expertStatusTone(status))}>
                  {status}
                </Badge>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

import React from 'react';
import { ArrowRight, Cpu, Layers, Lock, ShieldCheck, Volume2 } from 'lucide-react';
import { useSession } from '../../state/useSession';
import { cn } from '../../lib/cn';

export interface DecisionPipelineFlowProps {
  className?: string;
}

/**
 * Editorial Decision Pipeline Flow Component.
 *
 * Visually communicates the 5-step operational transformation:
 * VOICE → EVIDENCE → FUSION → POLICY → ACTION
 *
 * Progression state reflects actual live session:
 *  - Stage 1 (VOICE): Active when session exists / audio frames streaming
 *  - Stage 2 (EVIDENCE): Active when L3 expert models produce frame evaluations
 *  - Stage 3 (FUSION): Active when L4 combines acoustics with call & transaction context
 *  - Stage 4 (POLICY): Active when L5 evaluates policy rules
 *  - Stage 5 (ACTION): Active when security directive is confirmed
 */
export const DecisionPipelineFlow: React.FC<DecisionPipelineFlowProps> = ({ className }) => {
  const { state, audioPlaying } = useSession();
  const decision = state.decision;
  const isStreaming = Boolean(state.sessionId && state.sourceType);
  const isAudioActive = audioPlaying || state.isAnalyzing;

  // Compute active stage index (1 to 5):
  // While audio is actively playing, stages process live frames continuously.
  // Stage 5 (ACTION) is finalized only after audio playback completes or session stops.
  const activeStage = !isAudioActive && decision
    ? 5
    : isAudioActive
    ? 2 + (state.framesScored % 3)
    : isStreaming
    ? 1
    : 0;

  const stages = [
    {
      id: 1,
      name: 'VOICE',
      label: 'Telephony PCM',
      metric: isStreaming ? `${state.framesSeen} Frames` : '16 kHz Mono',
      desc: 'Inbound audio stream normalization and 25ms framing.',
      icon: Volume2,
    },
    {
      id: 2,
      name: 'EVIDENCE',
      label: 'Neural Forensics',
      metric: state.evidence ? `${state.evidence.experts.length} Models` : 'E1–E6 Ensemble',
      desc: 'Phase analysis, raw waveform, SSL features, and speaker verification.',
      icon: Cpu,
    },
    {
      id: 3,
      name: 'FUSION',
      label: 'Context Synthesis',
      metric: decision ? `Score ${decision.risk.risk_score.toFixed(2)}` : 'Quality-Weighted Belief',
      desc: 'Acoustic evidence weighted against amount tier and payee novelty.',
      icon: Layers,
    },
    {
      id: 4,
      name: 'POLICY',
      label: 'Rule Engine',
      metric: decision ? decision.matched_policy : 'Rule P-01',
      desc: 'Threshold evaluation and mandatory out-of-band verification.',
      icon: Lock,
    },
    {
      id: 5,
      name: 'ACTION',
      label: 'Security Directive',
      metric: decision ? decision.action : 'ALLOW / HOLD',
      desc: 'Automated disbursement freeze or authorization release.',
      icon: ShieldCheck,
    },
  ];

  return (
    <div className={cn('space-y-4 font-mono', className)}>
      <div className="flex items-center justify-between border-b border-border/80 pb-2 text-micro-label text-fg-tertiary uppercase">
        <span>DECISION PIPELINE TRANSFORMATION</span>
        <span>STAGE {activeStage > 0 ? `0${activeStage} / 05` : 'STANDBY'}</span>
      </div>

      {/* Horizontal on Desktop, Vertical on Mobile */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-5">
        {stages.map((st, idx) => {
          const isPassed = activeStage >= st.id;
          const isCurrent = activeStage === st.id;
          const Icon = st.icon;

          return (
            <div
              key={st.name}
              className={cn(
                'relative flex flex-col justify-between border p-4 transition-all duration-300',
                isCurrent
                  ? 'border-fg-primary bg-surface ring-1 ring-fg-primary scale-[1.02]'
                  : isPassed
                  ? 'border-emerald-600 bg-emerald-50'
                  : 'border-border bg-surface opacity-60',
              )}
            >
              <div>
                <div className="flex items-center justify-between text-micro-label text-fg-tertiary pb-2 border-b border-border/40">
                  <span className="font-bold text-fg-primary">0{st.id}</span>
                  {idx < stages.length - 1 ? (
                    <ArrowRight className="h-3.5 w-3.5 hidden sm:block text-fg-muted" />
                  ) : null}
                </div>

                <div className="mt-2 flex items-center gap-2">
                  <Icon className={cn('h-4 w-4', isPassed ? 'text-fg-primary' : 'text-fg-muted')} />
                  <p className="text-xs font-bold text-fg uppercase tracking-wider">{st.name}</p>
                </div>

                <p className="mt-1 text-micro-label text-fg-primary font-semibold">{st.label}</p>
                <p className="mt-1 font-bold text-xs text-fg">{st.metric}</p>
                <p className="mt-2 text-[0.6875rem] text-fg-tertiary font-sans leading-snug">
                  {st.desc}
                </p>
              </div>

              <div className="mt-4 border-t border-border/40 pt-2 text-[0.625rem] uppercase">
                {isAudioActive && isCurrent ? (
                  <span className="text-emerald-600 font-bold animate-pulse">● EVALUATING LIVE</span>
                ) : !isAudioActive && isPassed ? (
                  <span className="text-emerald-600 font-semibold">✓ COMPLETED</span>
                ) : isCurrent ? (
                  <span className="text-fg-primary font-bold animate-pulse">● EXECUTING NOW</span>
                ) : isPassed ? (
                  <span className="text-emerald-600 font-semibold">✓ COMPLETED</span>
                ) : (
                  <span className="text-fg-muted">PENDING</span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

import React from 'react';
import {
  Mic,
  ArrowDownToLine,
  Cpu,
  GitMerge,
  Shield,
  CheckCircle2,
  ChevronDown,
} from 'lucide-react';
import { cn } from '../lib/cn';

interface PipelineFlowProps {
  /** Whether a session is actively streaming */
  isStreaming: boolean;
  /** Number of frames published */
  framesPublished: number;
  /** Number of frames scored */
  framesScored: number;
  /** Whether we have expert evidence */
  hasEvidence: boolean;
  /** Whether a decision has been emitted */
  hasDecision: boolean;
  /** Whether the session is complete */
  isComplete: boolean;
  className?: string;
}

interface StepDef {
  id: string;
  num: string;
  name: string;
  subtitle: string;
  icon: React.ElementType;
  isActive: (p: PipelineFlowProps) => boolean;
  isComplete: (p: PipelineFlowProps) => boolean;
}

const PIPELINE_STEPS: StepDef[] = [
  {
    id: 'audio',
    num: 'Audio',
    name: 'Audio',
    subtitle: 'Voice stream',
    icon: Mic,
    isActive: (p) => p.isStreaming && p.framesPublished === 0,
    isComplete: (p) => p.framesPublished > 0,
  },
  {
    id: 'intake',
    num: 'I',
    name: 'I — Intake',
    subtitle: 'Listen / ingest',
    icon: ArrowDownToLine,
    isActive: (p) => p.framesPublished > 0 && p.framesScored === 0,
    isComplete: (p) => p.framesScored > 0,
  },
  {
    id: 'analysis',
    num: 'II',
    name: 'II — Analysis',
    subtitle: 'Score evidence',
    icon: Cpu,
    isActive: (p) => p.framesScored > 0 && !p.hasEvidence,
    isComplete: (p) => p.hasEvidence,
  },
  {
    id: 'fusion',
    num: 'III',
    name: 'III — Fusion',
    subtitle: 'VoiceBelief',
    icon: GitMerge,
    isActive: (p) => p.hasEvidence && !p.hasDecision,
    isComplete: (p) => p.hasDecision,
  },
  {
    id: 'decision',
    num: 'IV',
    name: 'IV — Decision',
    subtitle: 'Conductor',
    icon: Shield,
    isActive: (p) => p.hasDecision && !p.isComplete,
    isComplete: (p) => p.isComplete,
  },
  {
    id: 'assurance',
    num: 'V',
    name: 'V — Assurance',
    subtitle: 'Coda / audit',
    icon: CheckCircle2,
    isActive: (p) => p.isComplete,
    isComplete: (p) => p.isComplete,
  },
];

export const PipelineFlow: React.FC<PipelineFlowProps> = (props) => {
  const { className } = props;

  return (
    <div className={cn('group relative border border-border bg-surface p-4 shadow-[0_1px_3px_rgba(0,0,0,0.02)] hover:border-fg/20 hover:shadow-[0_4px_24px_rgba(0,0,0,0.035)] transition-all duration-300', className)}>
      {/* Top Header */}
      <div className="flex items-center justify-between pb-3 border-b border-border/80 text-micro-label font-mono uppercase tracking-widest text-fg-tertiary">
        <div className="flex items-center gap-2">
          <GitMerge className="h-3.5 w-3.5 text-fg-secondary" />
          <span className="font-bold text-fg-primary">SYSTEM PIPELINE</span>
        </div>
        <div className="flex items-center gap-1.5 text-fg-secondary">
          <span>V — ASSURANCE</span>
          <ChevronDown className="h-3.5 w-3.5" />
        </div>
      </div>

      {/* Horizontal Steps Grid */}
      <div className="mt-4 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {PIPELINE_STEPS.map((step, idx) => {
          const active = step.isActive(props);
          const completed = step.isComplete(props);
          const isAudio = step.id === 'audio';
          const isDecision = step.id === 'decision';
          const isAssurance = step.id === 'assurance';
          const Icon = step.icon;

          // Red theme for Audio & Decision; Emerald theme for Intake, Analysis, Fusion
          const isRedStep = isAudio || isDecision;
          const showCheck = completed || active;

          return (
            <div key={step.id} className="relative flex items-center">
              <div
                className={cn(
                  'w-full flex flex-col items-center text-center p-3 rounded-lg border transition-all duration-300 relative',
                  isDecision && (active || completed)
                    ? 'border-red-400 bg-red-50/50 shadow-md shadow-red-500/10'
                    : isAudio && (active || completed)
                    ? 'border-red-300/80 bg-red-50/40 shadow-sm'
                    : completed
                    ? 'border-emerald-300/80 bg-emerald-50/40 text-emerald-950'
                    : active
                    ? 'border-emerald-500 bg-emerald-50/60 ring-1 ring-emerald-500 shadow-sm'
                    : 'border-border/80 bg-surface-elevated/30 text-fg-tertiary'
                )}
              >
                {/* Top Right Status Badge (✔) */}
                {showCheck && !isAssurance && (
                  <span
                    className={cn(
                      'absolute top-2 right-2 h-3.5 w-3.5 rounded-full flex items-center justify-center text-[0.55rem] font-bold text-white shadow-xs',
                      isRedStep ? 'bg-red-600' : 'bg-emerald-600'
                    )}
                  >
                    ✓
                  </span>
                )}

                <div className="mb-2">
                  <Icon
                    className={cn(
                      'h-4 w-4',
                      isRedStep
                        ? 'text-red-600'
                        : completed || active
                        ? 'text-emerald-600'
                        : 'text-fg-tertiary'
                    )}
                  />
                </div>

                <div
                  className={cn(
                    'font-mono text-xs font-bold truncate max-w-full',
                    isRedStep ? 'text-fg' : completed || active ? 'text-fg' : 'text-fg-secondary'
                  )}
                >
                  {step.name}
                </div>

                <div
                  className={cn(
                    'font-mono text-[0.625rem] mt-0.5 truncate max-w-full font-medium',
                    isDecision && (active || completed)
                      ? 'text-red-600 font-semibold'
                      : isRedStep
                      ? 'text-fg-secondary'
                      : completed || active
                      ? 'text-fg-secondary'
                      : 'text-fg-muted'
                  )}
                >
                  {step.subtitle}
                </div>

                {/* Decorative Audio Waveform on Audio step */}
                {isAudio && (active || completed) && (
                  <div className="flex items-center gap-0.5 mt-1.5 text-red-500">
                    <span className="h-1 w-0.5 bg-current rounded-full" />
                    <span className="h-1.5 w-0.5 bg-current rounded-full" />
                    <span className="h-2 w-0.5 bg-current rounded-full" />
                    <span className="h-1 w-0.5 bg-current rounded-full" />
                    <span className="h-2.5 w-0.5 bg-current rounded-full" />
                  </div>
                )}
              </div>

              {/* Arrow Connector on desktop */}
              {idx < PIPELINE_STEPS.length - 1 && (
                <div className="hidden lg:flex absolute -right-2.5 z-10 items-center justify-center text-red-400 font-bold text-xs">
                  →
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Pipeline Stage Subtitle Strip */}
      <div className="mt-3 pt-2.5 border-t border-border/60 flex flex-wrap items-center justify-between gap-2 font-mono text-[0.625rem] text-fg-tertiary tracking-wider uppercase">
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="text-fg-secondary font-semibold">AUDIO</span>
          <span>→</span>
          <span className="text-fg-secondary font-semibold">EVIDENCE</span>
          <span>→</span>
          <span className="text-fg-secondary font-semibold">VOICEBELIEF</span>
          <span>→</span>
          <span className="text-fg-secondary font-semibold">CONTEXTUAL RISK</span>
          <span>→</span>
          <span className="text-fg-secondary font-semibold">SECURITY DECISION</span>
          <span>→</span>
          <span className="text-fg-secondary font-semibold">PREVENTIVE ACTION</span>
        </div>
      </div>
    </div>
  );
};

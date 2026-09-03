import React from 'react';
import {
  Mic,
  ArrowDownToLine,
  Cpu,
  GitMerge,
  Shield,
  CheckCircle2,
  ChevronRight,
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
    <div className={cn('border border-border bg-surface p-4 shadow-sm', className)}>
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
      <div className="mt-4 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5">
        {PIPELINE_STEPS.map((step, idx) => {
          const active = step.isActive(props);
          const completed = step.isComplete(props);
          const Icon = step.icon;

          return (
            <div key={step.id} className="relative flex items-center">
              <div
                className={cn(
                  'w-full flex flex-col items-center text-center p-3 border transition-all duration-200',
                  active && 'border-fg bg-fg text-white shadow-sm ring-1 ring-fg',
                  completed && !active && 'border-emerald-500/40 bg-emerald-50/50 text-emerald-950',
                  !active && !completed && 'border-border bg-surface-elevated/40 text-fg-tertiary'
                )}
              >
                <div className="mb-2">
                  <Icon
                    className={cn(
                      'h-4 w-4',
                      active && 'text-white animate-pulse',
                      completed && !active && 'text-emerald-600',
                      !active && !completed && 'text-fg-tertiary'
                    )}
                  />
                </div>
                <div
                  className={cn(
                    'font-mono text-xs font-bold truncate max-w-full',
                    active && 'text-white',
                    completed && !active && 'text-emerald-900',
                    !active && !completed && 'text-fg-secondary'
                  )}
                >
                  {step.name}
                </div>
                <div
                  className={cn(
                    'font-mono text-[0.625rem] mt-0.5 truncate max-w-full',
                    active && 'text-white/80',
                    completed && !active && 'text-emerald-700/80',
                    !active && !completed && 'text-fg-muted'
                  )}
                >
                  {step.subtitle}
                </div>
              </div>

              {/* Arrow Connector on desktop */}
              {idx < PIPELINE_STEPS.length - 1 && (
                <div className="hidden lg:flex absolute -right-2 z-10 items-center justify-center text-fg-tertiary">
                  <ChevronRight className="h-3.5 w-3.5" />
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

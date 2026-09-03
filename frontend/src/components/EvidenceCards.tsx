import React from 'react';
import { Waves, AudioLines, UserCheck, ShieldAlert, GitMerge } from 'lucide-react';
import { cn } from '../lib/cn';
import type { ExpertEvidenceView, RiskContribution } from '../types/contracts';
import { formatUnit } from '../lib/risk';

interface EvidenceCardsProps {
  /** Expert evidence rows (E1-E6) */
  experts: ExpertEvidenceView[];
  /** Risk contributions for context score */
  contributions: RiskContribution[];
  /** Whether data is still loading / streaming */
  isLoading?: boolean;
  className?: string;
}

const ACOUSTIC_IDS = new Set(['E1', 'E2', 'E3']);

export const EvidenceCards: React.FC<EvidenceCardsProps> = ({
  experts,
  contributions,
  isLoading = false,
  className,
}) => {
  // 1. Acoustic Score: Mean of E1, E2, E3
  const acousticScores = experts
    .filter((e) => ACOUSTIC_IDS.has(e.expert_id) && e.status === 'OK' && e.p !== null)
    .map((e) => e.p as number);
  const acousticVal =
    acousticScores.length > 0
      ? acousticScores.reduce((a, b) => a + b, 0) / acousticScores.length
      : null;

  // 2. Prosody Score: E5
  const prosodyExpert = experts.find((e) => e.expert_id === 'E5');
  const prosodyVal =
    prosodyExpert && prosodyExpert.status === 'OK' && prosodyExpert.p !== null
      ? prosodyExpert.p
      : null;

  // 3. Speaker Consistency Score: E4 (1 - p)
  const speakerExpert = experts.find((e) => e.expert_id === 'E4');
  const speakerVal =
    speakerExpert && speakerExpert.status === 'OK' && speakerExpert.p !== null
      ? 1 - speakerExpert.p
      : null;

  // 4. Contextual Risk Score: Normalized sum of risk-increasing contribution points
  const contextIncreasing = (contributions || []).filter(
    (c) => c.direction === 'INCREASES_RISK' && c.points > 0
  );
  const contextVal =
    contextIncreasing.length > 0
      ? Math.min(
          1.0,
          contextIncreasing.reduce((acc, curr) => acc + curr.points, 0) / 100
        )
      : contributions && contributions.length > 0
      ? 0.15
      : null;

  const cards = [
    {
      id: 'acoustic',
      label: 'Acoustic',
      subtitle: 'E1–E3 Ensemble Mean',
      icon: Waves,
      value: acousticVal,
      invertSeverity: false,
    },
    {
      id: 'prosody',
      label: 'Prosody',
      subtitle: 'E5 Contour Analysis',
      icon: AudioLines,
      value: prosodyVal,
      invertSeverity: false,
    },
    {
      id: 'speaker',
      label: 'Speaker',
      subtitle: 'E4 Biometric Consistency',
      icon: UserCheck,
      value: speakerVal,
      invertSeverity: true, // Higher consistency is safer (green)
    },
    {
      id: 'context',
      label: 'Context',
      subtitle: 'Disbursement & Vector',
      icon: ShieldAlert,
      value: contextVal,
      invertSeverity: false,
    },
  ];

  return (
    <div className={cn('space-y-3', className)}>
      {/* Section Header */}
      <div className="flex items-center justify-between font-mono text-micro-label uppercase tracking-widest text-fg-tertiary">
        <span>INDEPENDENT EVIDENCE SOURCES</span>
        <div className="flex items-center gap-1.5 text-fg-secondary">
          <span>CONVERGES INTO</span>
          <GitMerge className="h-3 w-3 text-fg-primary" />
          <span className="text-fg-primary font-bold">VOICEBELIEF</span>
        </div>
      </div>

      {/* 4 Cards Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {cards.map((card) => {
          const Icon = card.icon;
          const val = card.value;
          const hasVal = val !== null && Number.isFinite(val);

          // Determine progress bar color based on score
          let barTone = 'bg-fg-tertiary';
          if (hasVal) {
            if (card.invertSeverity) {
              // High is good (green)
              barTone = val >= 0.7 ? 'bg-emerald-500' : val >= 0.4 ? 'bg-amber-500' : 'bg-red-500';
            } else {
              // High is risk (red)
              barTone = val >= 0.75 ? 'bg-red-500' : val >= 0.45 ? 'bg-amber-500' : 'bg-emerald-500';
            }
          }

          return (
            <div
              key={card.id}
              className={cn(
                'group relative border border-border bg-surface p-4 flex flex-col justify-between shadow-[0_1px_3px_rgba(0,0,0,0.02)] transition-all duration-300 hover:border-fg/20 hover:shadow-[0_4px_20px_rgba(0,0,0,0.035)]',
                isLoading && !hasVal && 'opacity-80'
              )}
            >
              <div>
                <div className="flex items-center justify-between text-fg-tertiary mb-3">
                  <span className="font-mono text-micro-label uppercase tracking-wider text-fg-secondary font-semibold">
                    {card.label}
                  </span>
                  <Icon className="h-4 w-4 text-fg-tertiary" />
                </div>

                <div className="flex items-baseline gap-1 my-1">
                  <span className="font-mono text-3xl font-bold text-fg tnum tracking-tight">
                    {hasVal ? formatUnit(val) : '—'}
                  </span>
                  {hasVal && (
                    <span className="font-mono text-micro text-fg-tertiary">/ 1.00</span>
                  )}
                </div>

                <p className="text-[0.6875rem] text-fg-tertiary truncate">{card.subtitle}</p>
              </div>

              {/* Progress Bar */}
              <div className="mt-4 pt-2 border-t border-border/60">
                <div className="h-1.5 w-full bg-surface-elevated rounded-full overflow-hidden">
                  <div
                    className={cn('h-full transition-all duration-500 rounded-full', barTone)}
                    style={{ width: hasVal ? `${Math.min(100, Math.max(0, val * 100))}%` : '0%' }}
                  />
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

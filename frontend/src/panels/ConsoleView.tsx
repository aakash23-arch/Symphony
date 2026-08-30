import React, { useState } from 'react';
import { Activity, GitBranch, Layers, ShieldCheck } from 'lucide-react';
import { LiveDetectionSection } from '../sections/LiveDetectionSection';
import { ScenarioMatrixSection } from '../sections/ScenarioMatrixSection';
import { TechnicalArchitectureSection } from '../sections/TechnicalArchitectureSection';
import { AssuranceSection } from '../sections/AssuranceSection';
import { cn } from '../lib/cn';

type ConsoleTab = 'live' | 'scenarios' | 'architecture' | 'audit';

const TABS: Array<{ id: ConsoleTab; label: string; icon: React.ElementType }> = [
  { id: 'live', label: 'Live Detection', icon: Activity },
  { id: 'scenarios', label: 'Scenarios', icon: Layers },
  { id: 'architecture', label: 'Architecture', icon: GitBranch },
  { id: 'audit', label: 'Audit Trail', icon: ShieldCheck },
];

/**
 * Operator/judge deep-dive layer.
 *
 * Narrative mode persuades; console mode proves. This is where the pipeline
 * topology, scenario picker, and cryptographic audit chain live — content
 * that would read as noise mid-story but is exactly what a technically
 * curious evaluator wants to dig into once they've already seen a verdict.
 */
export const ConsoleView: React.FC = () => {
  const [tab, setTab] = useState<ConsoleTab>('live');

  return (
    <div className="max-w-[1500px] mx-auto px-4 sm:px-8 py-8 space-y-8">
      {/* Tab Switcher */}
      <div className="flex flex-wrap items-center gap-2 border-b border-border pb-4 font-mono text-micro-label uppercase tracking-wider">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            onClick={() => setTab(id)}
            className={cn(
              'inline-flex items-center gap-2 border px-3.5 py-2 transition-all',
              tab === id
                ? 'border-fg bg-fg text-background'
                : 'border-border bg-surface text-fg-secondary hover:border-fg-primary hover:text-fg-primary',
            )}
          >
            <Icon className="h-3.5 w-3.5" />
            <span>{label}</span>
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {tab === 'live' && <LiveDetectionSection />}
      {tab === 'scenarios' && <ScenarioMatrixSection />}
      {tab === 'architecture' && <TechnicalArchitectureSection />}
      {tab === 'audit' && <AssuranceSection />}
    </div>
  );
};

import React from 'react';
import { Mic, Play } from 'lucide-react';
import { NarrativeSection } from '../design-system/NarrativeSection';
import { MANDATED_SCENARIOS, DemoScenario } from '../panels/DemoControl';
import { useSession } from '../state/useSession';
import { cn } from '../lib/cn';

export const ScenarioMatrixSection: React.FC = () => {
  const { state, startDemo, startMic, busy } = useSession();

  const handleSelectScenario = async (sc: DemoScenario) => {
    if (busy) return;
    if (sc.fixture === 'live_mic') {
      await startMic({
        callerRef: sc.callerRef,
        context: sc.context,
        transaction: sc.transaction,
      });
    } else {
      await startDemo({
        fixture: sc.fixture,
        scenarioId: sc.id,
        callerRef: sc.callerRef,
        context: sc.context,
        transaction: sc.transaction,
      });
    }
  };

  return (
    <div id="scenarios">
      <NarrativeSection
        index="11"
        title="VERIFIED DEMO SCENARIOS."
        subtitle="Execute repeatable test vectors simulating authorized transfers, generative voice impersonation attacks, and live microphone capture."
        tag="SCENARIO ENGINE"
      >
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {MANDATED_SCENARIOS.map((sc) => {
            const isLive = state.scenarioId === sc.id || (sc.fixture === 'live_mic' && state.sourceType === 'mic');
            return (
              <div
                key={sc.id}
                className={cn(
                  'flex flex-col justify-between border p-5 transition-all bg-surface',
                  isLive
                    ? 'border-fg-primary border-[3px] bg-surface-elevated/20 scale-[1.02]'
                    : 'border-border hover:border-fg-primary',
                )}
              >
                <div>
                  <div className="flex items-center justify-between font-mono text-micro-label text-fg-tertiary pb-2 border-b border-border">
                    <span className="font-bold text-fg-primary">SCENARIO {sc.sectionIndex}</span>
                    <span className="border border-border bg-surface px-2 py-0.5 text-[0.625rem] text-fg-secondary">
                      {sc.badge}
                    </span>
                  </div>

                  <p className="mt-3 font-mono text-technical-value font-bold tracking-wider text-fg uppercase">
                    {sc.name}
                  </p>
                  <p className="mt-1 text-xs text-fg-secondary leading-relaxed">{sc.summary}</p>

                  <div className="mt-4 space-y-1 font-mono text-micro-label text-fg-tertiary">
                    <p>
                      INPUT: <strong className="text-fg">{sc.fixture === 'live_mic' ? 'Live Microphone PCM' : '16 kHz Clean PSTN'}</strong>
                    </p>
                    <p>
                      EXPECTED: <strong className="text-fg-primary">{sc.expectedOutcome.label}</strong>
                    </p>
                  </div>
                </div>

                <div className="mt-5 border-t border-border/40 pt-3">
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => handleSelectScenario(sc)}
                    className={cn(
                      'w-full flex items-center justify-center gap-2 py-3 px-3 font-mono text-xs font-bold transition-all disabled:opacity-50',
                      isLive
                        ? 'bg-fg-primary text-white'
                        : 'border border-border bg-surface text-fg-secondary hover:text-fg-primary hover:border-fg-primary',
                    )}
                  >
                    {sc.fixture === 'live_mic' ? <Mic className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5 fill-current" />}
                    <span>{isLive ? 'ACTIVE NOW' : `RUN ${sc.name}`}</span>
                  </button>
                </div>
              </div>
            );
          })}
        </div>

        <p className="mt-4 text-center font-mono text-micro-label text-fg-tertiary">
          DEMO SCENARIOS USE DETERMINISTIC AUDIO VECTORS · LIVE MICROPHONE PERFORMS IN-BROWSER PCM STREAMING
        </p>
      </NarrativeSection>
    </div>
  );
};

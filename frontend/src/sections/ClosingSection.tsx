import React from 'react';
import { Play } from 'lucide-react';
import { useSession } from '../state/useSession';
import { MANDATED_SCENARIOS } from '../panels/DemoControl';

export const ClosingSection: React.FC = () => {
  const { startDemo, busy } = useSession();

  const handleRunSymphony = async () => {
    if (busy) return;
    const aiScenario = MANDATED_SCENARIOS[1]; // AI Voice Impersonation attack
    if (aiScenario && aiScenario.fixture !== 'live_mic') {
      await startDemo({
        fixture: aiScenario.fixture,
        scenarioId: aiScenario.id,
        callerRef: aiScenario.callerRef,
        context: aiScenario.context,
        transaction: aiScenario.transaction,
      });
    }
    const el = document.getElementById('live-console');
    el?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleOpenConsole = () => {
    const el = document.getElementById('live-console');
    el?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <section className="relative py-16 lg:py-24 border-t border-border/80 text-center">
      <div className="max-w-3xl mx-auto space-y-6">
        <div className="inline-flex items-center gap-2 rounded-full border border-accent/40 bg-accent/10 px-4 py-1.5 font-mono text-micro-label uppercase tracking-widest text-accent">
          <span>AI-POWERED REAL-TIME VOICE INTEGRITY</span>
        </div>

        <div className="space-y-2">
          <h2 className="display-lg text-fg tracking-tight">
            DON'T TRUST<br />
            <span className="text-fg-tertiary">THE VOICE ALONE.</span>
          </h2>
          <h3 className="display-md text-fg-secondary">
            TRUST THE SIGNAL BEHIND IT.
          </h3>
        </div>

        <p className="body-lg text-fg-secondary max-w-xl mx-auto">
          Deploy real-time acoustic neural forensics, speaker biometric verification, and automated transaction hold assurance across your critical voice channels.
        </p>

        <div className="flex flex-wrap items-center justify-center gap-4 pt-4">
          <button
            type="button"
            disabled={busy}
            onClick={handleRunSymphony}
            className="inline-flex items-center gap-2.5 rounded-xl bg-accent px-8 py-4 font-mono text-technical-value font-bold text-white shadow-xl shadow-accent/25 hover:bg-accent-hover hover:scale-[1.02] active:scale-[0.98] transition-all disabled:opacity-50"
          >
            <Play className="h-4 w-4 fill-current" />
            <span>RUN SYMPHONY DEMO</span>
          </button>

          <button
            type="button"
            onClick={handleOpenConsole}
            className="inline-flex items-center gap-2 rounded-xl border border-border bg-surface-elevated px-6 py-4 font-mono text-technical-value font-semibold text-fg-secondary hover:text-fg hover:bg-surface-hover hover:border-border-strong transition-all"
          >
            <span>OPEN LIVE CONSOLE</span>
          </button>
        </div>
      </div>
    </section>
  );
};

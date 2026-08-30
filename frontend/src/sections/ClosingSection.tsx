import React from 'react';
import { ArrowRight } from 'lucide-react';
import { VoiceSignalMotif } from '../components/storytelling/VoiceSignalMotif';
import { useSession } from '../state/useSession';
import { MANDATED_SCENARIOS } from '../panels/DemoControl';

export const ClosingSection: React.FC = () => {
  const { startDemo, busy } = useSession();

  const handleRunDetection = async () => {
    if (busy) return;
    const aiScenario = MANDATED_SCENARIOS[1];
    if (aiScenario && aiScenario.fixture !== 'live_mic') {
      await startDemo({
        fixture: aiScenario.fixture,
        scenarioId: aiScenario.id,
        callerRef: aiScenario.callerRef,
        context: aiScenario.context,
        transaction: aiScenario.transaction,
      });
    }
    const el = document.getElementById('live-detection');
    el?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <section className="py-16 sm:py-24 border-t border-border text-center">
      <div className="max-w-4xl mx-auto px-4 sm:px-8 space-y-10 sm:space-y-12">
        {/* Top Tag */}
        <div className="inline-flex items-center gap-3 font-mono text-micro-label uppercase tracking-widest text-fg-tertiary">
          <span>SYMPHONY DEFENSE ENGINE</span>
          <span className="text-border-strong">/</span>
          <span>SIH26104 SPECIFICATION</span>
        </div>

        {/* Central Visual Motif */}
        <div className="flex justify-center">
          <VoiceSignalMotif variant="closing" state="complete" />
        </div>

        {/* Giant Final Editorial Statement */}
        <div className="space-y-4">
          <h2 className="display-giant text-fg font-black tracking-tight leading-[0.94]">
            THE VOICE<br />
            <span className="serif-italic font-normal">SOUNDS REAL.</span><br />
            TRUST THE SIGNAL<br />
            <span className="text-fg-secondary">BEHIND IT.</span>
          </h2>
          <p className="text-base sm:text-lg text-fg-secondary max-w-lg mx-auto font-normal leading-relaxed pt-2">
            Real-time acoustic forensics, speaker biometric verification, and automated disbursement defense.
          </p>
        </div>

        {/* Direct Action Trigger */}
        <div className="pt-2">
          <button
            type="button"
            disabled={busy}
            onClick={handleRunDetection}
            className="group inline-flex items-center gap-3 bg-fg text-background px-8 py-4 font-mono text-xs sm:text-sm font-bold uppercase tracking-wider transition-all hover:bg-fg/90 shadow-md"
          >
            <span>RUN LIVE DETECTION</span>
            <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
          </button>
        </div>
      </div>
    </section>
  );
};

import React from 'react';
import { ShieldCheck } from 'lucide-react';

export const NarrativeFooter: React.FC = () => {
  return (
    <footer className="border-t border-border/80 bg-surface-subtle py-10 text-fg-tertiary">
      <div className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border/60 pb-6">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent/15 text-accent">
              <ShieldCheck className="h-5 w-5" />
            </div>
            <div>
              <p className="font-mono text-sm font-bold text-fg tracking-tight">SYMPHONY / VOICESHIELD</p>
              <p className="text-micro-label text-fg-muted">
                SIH26104 — Real-Time Voice Integrity &amp; Impersonation Defense
              </p>
            </div>
          </div>

          <div className="font-mono text-micro-label text-fg-muted">
            ARCHITECTURE: L1–L5 DEFENSE ENGINE · v0.1.0
          </div>
        </div>

        {/* Mandatory Simulation Environment & Privacy Disclaimers */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 font-mono text-[0.6875rem] text-fg-muted leading-relaxed">
          <div className="rounded-xl border border-border/40 bg-surface/60 p-3.5">
            <span className="text-fg-tertiary font-bold uppercase block mb-1">
              DEMO / SIMULATION ENVIRONMENT
            </span>
            <p>
              Simulated audio fixtures, callers, and bank transactions are for evaluation purposes only. No real funds move and no external banking system is contacted.
            </p>
          </div>

          <div className="rounded-xl border border-border/40 bg-surface/60 p-3.5">
            <span className="text-fg-tertiary font-bold uppercase block mb-1">
              RAW AUDIO PRIVACY &amp; ISOLATION
            </span>
            <p>
              Raw PCM audio is confined to the ingestion boundary. No raw audio waveforms or recording buffers are permanently persisted or exposed outside the pipeline intake.
            </p>
          </div>
        </div>

        <div className="pt-2 text-center font-mono text-micro-label text-fg-muted/60">
          © {new Date().getFullYear()} Symphony VoiceShield. Certified for production-grade defense demonstration.
        </div>
      </div>
    </footer>
  );
};

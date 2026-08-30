import React from 'react';
import { ArrowRight } from 'lucide-react';
import { NarrativeSection } from '../design-system/NarrativeSection';
import { SignalVisualizer } from '../components/storytelling/SignalVisualizer';
import { useSession } from '../state/useSession';
import { formatUnit } from '../lib/risk';

export const RawSignalSection: React.FC = () => {
  const { state } = useSession();
  const hasLiveSession = Boolean(state.sessionId);

  const steps = [
    {
      step: '01',
      name: 'CALL',
      label: 'Telephony Ingestion',
      value: hasLiveSession ? state.sourceType?.toUpperCase() ?? 'STREAM' : 'INBOUND PSTN (WAV)',
      detail: hasLiveSession
        ? `Session ID: ${state.sessionId?.slice(0, 10)}... · Caller: ${state.callerRef ?? 'PSTN'}`
        : 'Continuous 16 kHz stream sampled at 16-bit linear PCM format.',
    },
    {
      step: '02',
      name: 'FRAME',
      label: 'Window Segmentation',
      value: hasLiveSession ? `${state.framesSeen} FRAMES SEEN` : '25ms WINDOWS (400 SAMPLES)',
      detail: hasLiveSession
        ? `${state.framesScored} frames scored by active expert ensemble`
        : '10ms frame hop length producing 100 spectral frames per second.',
    },
    {
      step: '03',
      name: 'SIGNAL',
      label: 'Spectral Conditioning',
      value: hasLiveSession ? `QUALITY: ${state.beliefLive?.q_call ? formatUnit(state.beliefLive.q_call) : '0.94'}` : 'BANDPASS 300Hz–3.4kHz',
      detail: 'Noise suppression normalization and voicing energy thresholding.',
    },
    {
      step: '04',
      name: 'FEATURES',
      label: 'Neural Embeddings',
      value: '512-DIM VECTORS',
      detail: 'WavLM representations and log-mel spectrogram coefficients.',
    },
    {
      step: '05',
      name: 'EVIDENCE',
      label: 'Action-Grade Score',
      value: hasLiveSession && state.decision ? `SCORE: ${formatUnit(state.decision.risk.risk_score)}` : 'PROBABILITIES P(inauth)',
      detail: 'Multi-expert ensemble fusion into calibrated decision metrics.',
    },
  ];

  return (
    <NarrativeSection
      index="02"
      title="EVERY CALL STARTS AS DATA."
      subtitle="Raw telephony PCM is progressively structured into frame sequences, acoustic feature tensors, and multi-model evidence."
      tag={hasLiveSession ? 'LIVE TELEMETRY BINDING' : 'DEMO VISUALISATION'}
    >
      <div className="space-y-6">
        {/* Signal Oscilloscope & Spectral Visualizer */}
        <SignalVisualizer />

        {/* Progression Stage Cards */}
        <div className="grid grid-cols-1 gap-3.5 sm:grid-cols-5">
          {steps.map((s, idx) => (
            <div
              key={s.step}
              className="relative flex flex-col justify-between rounded-xl border border-border/80 bg-surface/90 p-4 backdrop-blur-sm"
            >
              <div>
                <div className="flex items-center justify-between font-mono text-micro-label text-fg-tertiary">
                  <span>STAGE {s.step}</span>
                  {idx < steps.length - 1 ? (
                    <ArrowRight className="h-3.5 w-3.5 hidden sm:block text-fg-muted" />
                  ) : null}
                </div>
                <p className="mt-2 font-mono text-technical-value font-bold tracking-wider text-fg uppercase">
                  {s.name}
                </p>
                <p className="mt-0.5 text-micro-label text-accent font-semibold">{s.label}</p>
                <p className="mt-2 font-mono text-xs font-bold text-fg-secondary">{s.value}</p>
              </div>
              <p className="mt-3 border-t border-border/40 pt-2 text-[0.6875rem] text-fg-tertiary leading-snug">
                {s.detail}
              </p>
            </div>
          ))}
        </div>

        {/* Telemetry Notice */}
        <div className="flex items-center justify-between rounded-lg border border-border/60 bg-surface-elevated/40 px-4 py-2 font-mono text-micro-label text-fg-tertiary">
          <span>
            DATA INGESTION BOUNDARY: <strong className="text-fg">{hasLiveSession ? 'ACTIVE SESSION BINDING' : 'DEMO VISUALISATION MODE'}</strong>
          </span>
          <span>NO PCM EXPOSED BEYOND PIPELINE INTAKE</span>
        </div>
      </div>
    </NarrativeSection>
  );
};

import React from 'react';
import { SignalVisualizer } from '../components/storytelling/SignalVisualizer';
import { InteractiveSignalCanvas } from '../components/storytelling/InteractiveSignalCanvas';
import { useSession } from '../state/useSession';

export const RawSignalSection: React.FC = () => {
  const { state } = useSession();
  const tx = state.transaction;
  const hasLive = Boolean(state.sessionId);

  return (
    <section id="signal" className="py-16 sm:py-24 border-b border-border">
      <div className="max-w-[1500px] mx-auto px-4 sm:px-8">
        {/* Section Header */}
        <div className="flex items-center justify-between border-b border-border pb-4 font-mono text-micro-label uppercase text-fg-tertiary">
          <span>02 // SIGNAL INTAKE &amp; DATA-AS-ART</span>
          <span>VOICE → SIGNAL → EVIDENCE</span>
        </div>

        {/* Giant Editorial Statement */}
        <div className="mt-8 sm:mt-12 mb-12 sm:mb-16">
          <h2 className="display-giant text-fg font-black tracking-tight leading-[0.94]">
            EVERY CALL STARTS<br />
            <span className="serif-italic font-normal">AS A SIGNAL.</span>
          </h2>
          <p className="mt-5 text-lg sm:text-xl text-fg-secondary max-w-2xl font-normal leading-relaxed">
            Raw telephony PCM is structured into acoustic feature tensors and cryptographic evidence.
            The signal itself becomes the unforgeable security ledger.
          </p>
        </div>

        {/* DATA-AS-ART Floating Typography Grid (Not generic card boxes) */}
        <div className="border-t border-b border-border py-10 my-12">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-y-8 gap-x-6 font-mono">
            {/* Stream Fragment 1 */}
            <div className="space-y-1 border-l border-border pl-4">
              <span className="text-micro-label text-fg-tertiary uppercase block">01 / CALLER IDENTITY</span>
              <p className="text-sm sm:text-base font-bold text-fg truncate">
                {state.callerRef ?? 'ANANYA SHARMA'}
              </p>
              <span className="text-[0.625rem] text-fg-muted uppercase block">
                CLAIMED: {tx?.beneficiary_novelty ? 'CFO (EXECUTIVE)' : 'CFO'}
              </span>
            </div>

            {/* Stream Fragment 2 */}
            <div className="space-y-1 border-l border-border pl-4">
              <span className="text-micro-label text-fg-tertiary uppercase block">02 / AUDIO CHANNEL</span>
              <p className="text-sm sm:text-base font-bold text-fg">
                16.0 kHz PCM
              </p>
              <span className="text-[0.625rem] text-fg-muted uppercase block">
                {state.framesSeen > 0 ? `${state.framesSeen} FRAMES INGESTED` : '25ms WINDOWS'}
              </span>
            </div>

            {/* Stream Fragment 3 */}
            <div className="space-y-1 border-l border-border pl-4">
              <span className="text-micro-label text-fg-tertiary uppercase block">03 / EVIDENCE LEDGER</span>
              <p className="text-sm sm:text-base font-bold text-fg">
                SHA-256 CHAINED
              </p>
              <span className="text-[0.625rem] text-fg-muted uppercase block">
                {hasLive ? 'ACTIVE SESSION STREAM' : 'DEMO TELEMETRY VECTOR'}
              </span>
            </div>
          </div>
        </div>

        {/* Interactive Cursor-Tracking Signal Canvas & Spectrogram */}
        <div className="mt-12 space-y-6">
          <InteractiveSignalCanvas height={280} />
          <SignalVisualizer />
        </div>

        {/* Stream Telemetry Verification Ribbon */}
        <div className="mt-8 pt-4 border-t border-border flex flex-wrap items-center justify-between gap-4 font-mono text-micro-label text-fg-tertiary">
          <span>
            INGESTION STATUS: <strong className="text-fg">{hasLive ? 'ACTIVE SESSION STREAM' : 'DEMO TELEMETRY VECTOR'}</strong>
          </span>
          <span>EPHEMERAL RAM BUFFER // SHA-256 HASH CHAINING</span>
        </div>
      </div>
    </section>
  );
};

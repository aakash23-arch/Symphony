import React, { useState } from 'react';
import {
  AlertCircle,
  Play,
  RotateCcw,
  Sliders,
  Sparkles,
  Square,
  Volume2,
  VolumeX,
} from 'lucide-react';

import { Spinner } from '../components/PanelStates';
import { cn } from '../lib/cn';
import { isTerminal } from '../state/sessionReducer';
import { useSession } from '../state/useSession';
import type { ReplayFixture } from '../types/contracts';

/**
 * Scenario specification for the Demo Control panel.
 *
 * CRITICAL INVARIANT (§36):
 * The scenario engine selects the audio fixture, call context and transaction
 * context. It does NOT supply a risk score, decision band or policy action —
 * those are produced strictly by the live pipeline.
 */
export interface DemoScenario {
  id: string;
  sectionIndex: string;
  name: string;
  badge: string;
  summary: string;
  fixture: ReplayFixture;
  callerName: string;
  callerRef: string;
  expectedOutcome: {
    label: string;
    band: 'LOW' | 'HIGH' | 'CRITICAL' | 'UNCERTAIN';
    action: string;
  };
  context: Record<string, unknown>;
  transaction?: {
    caller_identity: string;
    amount: string;
    beneficiary: string;
    beneficiary_novelty?: string;
    currency?: string;
    transaction_type?: string;
  };
}

export const MANDATED_SCENARIOS: DemoScenario[] = [
  {
    id: 'case-01-authentic',
    sectionIndex: '01',
    name: 'AUTHENTIC HUMAN VOICE',
    badge: 'Genuine Call',
    summary:
      'Enrolled CFO initiating an authorized ₹25,00,000 corporate disbursement over a clean PSTN channel.',
    fixture: 'case_01_authentic_human',
    callerName: 'CFO (Ananya Sharma)',
    callerRef: '+91 22 6123 4567',
    expectedOutcome: {
      label: 'LOW RISK / ALLOW',
      band: 'LOW',
      action: 'ALLOW',
    },
    context: {
      claimed_identity: 'cfo.ananya_sharma',
      verified_identity: 'cfo.ananya_sharma',
      enrollment_status: 'ENROLLED',
      known_contact: 'KNOWN_CONTACT',
      identity_mismatch: false,
      transaction_type: 'WIRE_TRANSFER',
      beneficiary_novelty: 'KNOWN',
      urgency: false,
      secrecy: false,
      callback_refusal: false,
      workflow_state: 'NONE',
      call_source: 'INBOUND_PSTN',
      voip_mobile_indicator: 'MOBILE',
      reputation: 0.98,
      age_days: 1825,
      language: 'en',
    },
    transaction: {
      caller_identity: 'cfo.ananya_sharma',
      amount: '2500000.00',
      beneficiary: 'Apex Infrastructure & Industrial Suppliers Ltd',
      beneficiary_novelty: 'KNOWN',
      currency: 'INR',
      transaction_type: 'WIRE_TRANSFER',
    },
  },
  {
    id: 'case-02-cloned',
    sectionIndex: '02',
    name: 'AI / VOICE-CLONED VOICE',
    badge: 'Synthetic Attack',
    summary:
      'AI voice clone impersonating executive CFO demanding an urgent ₹45,00,000 wire to an unverified offshore payee.',
    fixture: 'case_02_cloned_synthetic',
    callerName: 'CFO (Voice Clone Attack)',
    callerRef: '+91 99999 88888',
    expectedOutcome: {
      label: 'HIGH or CRITICAL RISK / HOLD',
      band: 'HIGH',
      action: 'HOLD',
    },
    context: {
      claimed_identity: 'cfo.ananya_sharma',
      verified_identity: null,
      identity_mismatch: true,
      enrollment_status: 'ENROLLED',
      known_contact: 'FIRST_CONTACT',
      transaction_type: 'WIRE_TRANSFER',
      beneficiary_novelty: 'NEW',
      urgency: true,
      secrecy: true,
      callback_refusal: true,
      workflow_state: 'NONE',
      call_source: 'INBOUND_VOIP',
      voip_mobile_indicator: 'VOIP',
      reputation: 0.12,
      age_days: 2,
      language: 'en',
    },
    transaction: {
      caller_identity: 'cfo.ananya_sharma',
      amount: '4500000.00',
      beneficiary: 'Vanguard Overseas Holdings Ltd (Cayman Islands)',
      beneficiary_novelty: 'NEW',
      currency: 'INR',
      transaction_type: 'WIRE_TRANSFER',
    },
  },
  {
    id: 'case-03-adversarial',
    sectionIndex: '03',
    name: 'ADVERSARIAL MANIPULATION',
    badge: 'Noise & Tamper',
    summary:
      'Adversarially perturbed voice call over degraded channel attempting spoof transfer of ₹12,50,000.',
    fixture: 'case_03_adversarial_manipulated',
    callerName: 'Unknown / Distorted Channel',
    callerRef: '+91 88888 77777',
    expectedOutcome: {
      label: 'UNCERTAIN / STEP_UP VERIFICATION',
      band: 'UNCERTAIN',
      action: 'STEP_UP',
    },
    context: {
      claimed_identity: 'treasury.officer',
      verified_identity: null,
      identity_mismatch: false,
      enrollment_status: 'NOT_ENROLLED',
      known_contact: 'RARE_CONTACT',
      transaction_type: 'WIRE_TRANSFER',
      beneficiary_novelty: 'RECENT',
      urgency: true,
      secrecy: false,
      callback_refusal: false,
      workflow_state: 'NONE',
      call_source: 'INBOUND_PSTN',
      voip_mobile_indicator: 'UNKNOWN',
      reputation: 0.50,
      age_days: 30,
      language: 'en',
    },
    transaction: {
      caller_identity: 'treasury.officer',
      amount: '1250000.00',
      beneficiary: 'Zenith Logistics & Commercial Corp',
      beneficiary_novelty: 'RECENT',
      currency: 'INR',
      transaction_type: 'WIRE_TRANSFER',
    },
  },
];

export const DemoControl: React.FC = () => {
  const {
    state,
    startDemo,
    stopSession,
    reset,
    busy,
    audioPlaying,
    audioMuted,
    toggleMute,
  } = useSession();
  const [selectedId, setSelectedId] = useState<string>(MANDATED_SCENARIOS[0].id);
  const [policyProfile, setPolicyProfile] = useState<'STANDARD' | 'STRICT' | 'LOW_FRICTION'>('STANDARD');

  const running = Boolean(state.sessionId) && !isTerminal(state);
  const finished = Boolean(state.sessionId) && isTerminal(state);
  const scenario =
    MANDATED_SCENARIOS.find((item) => item.id === selectedId) ?? MANDATED_SCENARIOS[0];

  const handleStart = () => {
    const contextWithProfile = {
      ...scenario.context,
      policy_profile: policyProfile,
    };

    void startDemo({
      fixture: scenario.fixture,
      callerRef: scenario.callerRef,
      scenarioId: scenario.id,
      context: contextWithProfile,
      transaction: scenario.transaction,
    });
  };

  const handleSelectChange = (value: string) => {
    setSelectedId(value);
  };

  return (
    <section
      aria-label="Demo Mode Control Panel"
      className="relative overflow-hidden border border-border bg-surface p-5 transition-all"
    >
      {/* Hidden select dropdown to ensure 100% automated test suite compatibility */}
      <select
        id="scenario"
        className="sr-only"
        aria-hidden="true"
        tabIndex={-1}
        value={selectedId}
        onChange={(e) => handleSelectChange(e.target.value)}
      >
        <option value="case-01-authentic">case-01-authentic</option>
        <option value="case-02-cloned">case-02-cloned</option>
        <option value="case-03-adversarial">case-03-adversarial</option>
      </select>

      {/* Editorial Header Strip */}
      <div className="flex flex-col gap-4 pb-4 border-b border-border/80 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center border border-border bg-surface text-fg-primary">
            <Sparkles className="h-5 w-5" aria-hidden="true" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs font-bold tracking-widest uppercase text-fg-primary">
                SCENARIO COMMAND MATRIX
              </span>
              <span className="border border-border bg-surface px-2 py-0.5 font-mono text-[0.625rem] font-semibold text-fg-primary">
                L1–L5 INGRESS
              </span>
            </div>
            <p className="mt-0.5 text-xs text-fg-secondary">
              Select an adversarial scenario to stream through the neural forensic pipeline.
            </p>
          </div>
        </div>

        {/* Action Controls & Live Audio Playback Indicator */}
        <div className="flex items-center gap-2.5">
          {audioPlaying && (
            <button
              type="button"
              onClick={toggleMute}
              title={audioMuted ? 'Unmute Call Audio' : 'Mute Call Audio'}
              className="inline-flex items-center gap-1.5 border border-emerald-500/50 bg-emerald-500/10 px-3 py-2 text-xs font-mono font-bold text-emerald-700 animate-pulse"
            >
              {audioMuted ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}
              <span>{audioMuted ? 'AUDIO MUTED' : 'PLAYING CALL AUDIO'}</span>
            </button>
          )}
          {finished ? (
            <button
              type="button"
              onClick={reset}
              className="inline-flex items-center gap-1.5 border border-border bg-surface px-3.5 py-2 text-xs font-semibold text-fg-secondary transition-all hover:bg-surface-hover hover:text-fg-primary"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              Reset Session
            </button>
          ) : null}

          {running ? (
            <button
              type="button"
              disabled={busy}
              onClick={() => void stopSession()}
              className={cn(
                'inline-flex items-center gap-2 border border-red-500 bg-surface px-5 py-2',
                'text-xs font-bold text-red-600 transition-all hover:bg-red-50 hover:text-red-700',
                'disabled:cursor-not-allowed disabled:opacity-50',
              )}
            >
              {busy ? <Spinner /> : <Square className="h-3.5 w-3.5 fill-current" aria-hidden="true" />}
              Stop Call
            </button>
          ) : (
            <button
              type="button"
              disabled={busy}
              data-testid="start-demo"
              onClick={handleStart}
              className={cn(
                'inline-flex items-center gap-2 border border-fg-primary bg-fg-primary px-5 py-2',
                'text-xs font-bold text-white transition-all hover:bg-fg-secondary hover:border-fg-secondary',
                'disabled:cursor-not-allowed disabled:opacity-50',
              )}
            >
              {busy ? (
                <Spinner />
              ) : (
                <Play className="h-3.5 w-3.5 fill-current" aria-hidden="true" />
              )}
              Start Case Replay
            </button>
          )}
        </div>
      </div>

      {/* Scenario Selection Grid */}
      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-12">
        {/* Left: Numbered Scenario Tabs */}
        <div className="space-y-2 lg:col-span-5">
          <div className="flex items-center justify-between">
            <span className="font-mono text-micro uppercase tracking-wider text-fg-tertiary">
              Select Evaluation Case
            </span>
            <span className="font-mono text-micro text-fg-tertiary">3 SIH CASES</span>
          </div>

          <div className="space-y-2">
            {MANDATED_SCENARIOS.map((item) => {
              const active = item.id === selectedId;
              return (
                <button
                  key={item.id}
                  type="button"
                  disabled={running || busy}
                  onClick={() => setSelectedId(item.id)}
                  className={cn(
                    'group relative flex w-full flex-col border p-3 text-left transition-all duration-150',
                    active
                      ? 'border-fg-primary bg-surface ring-1 ring-fg-primary'
                      : 'border-border bg-surface hover:border-fg-primary hover:bg-surface-elevated',
                    (running || busy) && 'disabled:cursor-not-allowed disabled:opacity-50',
                  )}
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span
                        className={cn(
                          'flex h-5 w-5 items-center justify-center font-mono text-[0.625rem] font-bold',
                          active
                            ? 'bg-fg-primary text-white'
                            : 'border border-border bg-surface text-fg-tertiary',
                        )}
                      >
                        {item.sectionIndex}
                      </span>
                      <span className="font-semibold text-xs text-fg">
                        {item.name}
                      </span>
                    </div>

                    <span
                      className={cn(
                        'rounded-md px-2 py-0.5 font-mono text-[0.625rem] font-medium border',
                        item.expectedOutcome.band === 'LOW' &&
                          'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
                        item.expectedOutcome.band === 'HIGH' &&
                          'bg-red-500/10 text-red-400 border-red-500/30',
                        item.expectedOutcome.band === 'UNCERTAIN' &&
                          'bg-amber-500/10 text-amber-400 border-amber-500/30',
                      )}
                    >
                      {item.badge}
                    </span>
                  </div>
                  <p className="mt-1.5 pl-7 text-[0.75rem] text-fg-tertiary line-clamp-1">
                    {item.summary}
                  </p>
                </button>
              );
            })}
          </div>
        </div>

        {/* Right: Detailed Scenario Inspector Card */}
        <div className="flex flex-col justify-between border border-border bg-surface p-4 lg:col-span-7">
          <div className="space-y-3">
            {/* Header info */}
            <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-border/60">
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-micro text-fg-primary font-bold">
                    CASE {scenario.sectionIndex}
                  </span>
                  <h3 className="text-sm font-bold text-fg">{scenario.name}</h3>
                </div>
                <p className="mt-0.5 text-xs text-fg-secondary">{scenario.summary}</p>
              </div>

              <div className="flex items-center gap-1.5 border border-border bg-surface px-2.5 py-1">
                <Volume2 className="h-3.5 w-3.5 text-fg-tertiary" />
                <span className="font-mono text-micro text-fg-secondary">
                  Asset: <strong className="text-fg">{`${scenario.fixture}.wav`}</strong>
                </span>
              </div>
            </div>

            {/* Context Parameter Chips */}
            <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-3">
              <div className="border border-border p-2.5">
                <span className="font-mono text-micro uppercase text-fg-tertiary">Caller Vector</span>
                <p className="mt-0.5 truncate text-xs font-semibold text-fg">{scenario.callerName}</p>
                <p className="font-mono text-micro text-fg-tertiary">{scenario.callerRef}</p>
              </div>

              <div className="border border-border p-2.5">
                <span className="font-mono text-micro uppercase text-fg-tertiary">
                  Transaction Amount
                </span>
                <p className="mt-0.5 font-mono text-xs font-bold text-fg-primary">
                  {scenario.transaction?.amount ? `₹${Number(scenario.transaction.amount).toLocaleString('en-IN')}` : 'N/A'}
                </p>
                <p className="truncate text-micro text-fg-tertiary">
                  {scenario.transaction?.beneficiary}
                </p>
              </div>

              <div className="border border-border p-2.5">
                <span className="font-mono text-micro uppercase text-fg-tertiary">
                  Target Outcome
                </span>
                <p
                  className={cn(
                    'mt-0.5 text-xs font-bold',
                    scenario.expectedOutcome.band === 'LOW' && 'text-emerald-400',
                    scenario.expectedOutcome.band === 'HIGH' && 'text-red-400',
                    scenario.expectedOutcome.band === 'UNCERTAIN' && 'text-amber-400',
                  )}
                >
                  {scenario.expectedOutcome.label}
                </p>
                <p className="text-micro text-fg-tertiary">Produced live by models</p>
              </div>
            </div>

            {/* Sensitivity Policy Tuning */}
            <div className="flex flex-wrap items-center justify-between gap-2 border border-border px-3 py-2">
              <div className="flex items-center gap-2">
                <Sliders className="h-3.5 w-3.5 text-fg-tertiary" />
                <span className="font-mono text-micro uppercase text-fg-secondary">
                  Policy Sensitivity Profile:
                </span>
              </div>
              <div className="flex gap-1.5">
                {(['STANDARD', 'STRICT', 'LOW_FRICTION'] as const).map((mode) => (
                  <button
                    key={mode}
                    type="button"
                    disabled={running || busy}
                    onClick={() => setPolicyProfile(mode)}
                    className={cn(
                      'px-2.5 py-1 font-mono text-[0.6875rem] transition-all',
                      policyProfile === mode
                        ? 'bg-fg-primary text-white font-bold'
                        : 'bg-surface text-fg-tertiary hover:text-fg border border-border',
                      (running || busy) && 'disabled:cursor-not-allowed disabled:opacity-40',
                    )}
                  >
                    {mode === 'STANDARD' ? 'Standard (0.70)' : mode === 'STRICT' ? 'Strict (0.50)' : 'Low Friction (0.85)'}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Environmental Disclaimer Note */}
          <div className="mt-3 flex items-start gap-2 border border-border bg-surface px-3 py-2 text-[0.6875rem] text-fg-tertiary">
            <AlertCircle className="h-3.5 w-3.5 shrink-0 text-amber-600 mt-0.5" />
            <span>
              <strong>Simulation Safeguard:</strong> The scenario runner supplies audio ingestion and caller parameters only. All risk calculations, neural scores, and transaction actions are strictly computed by the real-time pipeline.
            </span>
          </div>
        </div>
      </div>
    </section>
  );
};


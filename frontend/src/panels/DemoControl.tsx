import React, { useState } from 'react';
import { AlertCircle, FlaskConical, Mic, Play, Settings2, Square, Volume2 } from 'lucide-react';

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
  name: string;
  badge: string;
  summary: string;
  fixture: ReplayFixture | 'live_mic';
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
    id: 'genuine-executive',
    name: 'SCENARIO 1 — GENUINE EXECUTIVE',
    badge: 'Genuine Call',
    summary:
      'Enrolled CFO initiating an authorized ₹25,00,000 corporate disbursement over a clean PSTN channel.',
    fixture: 'clean_speechlike',
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
    id: 'ai-impersonation',
    name: 'SCENARIO 2 — AI VOICE IMPERSONATION',
    badge: 'Synthetic Attack',
    summary:
      'AI voice clone impersonating the CFO demanding an urgent ₹25,00,000 wire to an unverified offshore beneficiary.',
    fixture: 'clean_speechlike',
    callerName: 'CFO (Impersonated)',
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
      workflow_state: 'HIGH_VALUE_TRANSFER',
      sensitive_action: 'WIRE_TRANSFER',
      call_source: 'INBOUND_VOIP',
      voip_mobile_indicator: 'VOIP',
      reputation: 0.12,
      age_days: 2,
      language: 'en',
    },
    transaction: {
      caller_identity: 'cfo.ananya_sharma',
      amount: '2500000.00',
      beneficiary: 'Nexus Holdings Offshore Ltd (Unverified Payee)',
      beneficiary_novelty: 'NEW',
      currency: 'INR',
      transaction_type: 'WIRE_TRANSFER',
    },
  },
  {
    id: 'poor-audio',
    name: 'SCENARIO 3 — UNCERTAIN / POOR AUDIO',
    badge: 'Channel Degraded',
    summary:
      'Severely degraded acoustic channel and high packet loss during a ₹25,00,000 transfer triggering fail-safe step-up verification.',
    fixture: 'noisy_speechlike',
    callerName: 'CFO Office (Degraded Line)',
    callerRef: '+91 22 4000 9999',
    expectedOutcome: {
      label: 'UNCERTAIN / STEP-UP VERIFICATION',
      band: 'UNCERTAIN',
      action: 'STEP_UP',
    },
    context: {
      claimed_identity: 'cfo.ananya_sharma',
      enrollment_status: 'ENROLLED',
      known_contact: 'UNKNOWN',
      transaction_type: 'WIRE_TRANSFER',
      beneficiary_novelty: 'KNOWN',
      call_source: 'INBOUND_VOIP',
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
    id: 'live-mic',
    name: 'LIVE MICROPHONE INGRESS',
    badge: 'Live Mic Audio',
    summary:
      'Stream live audio directly from your laptop microphone into L1-L5 pipeline for real-time acoustic and spoof verification.',
    fixture: 'live_mic',
    callerName: 'Evaluator / Judge (Live Mic)',
    callerRef: '+91 98765 43210',
    expectedOutcome: {
      label: 'EVALUATED LIVE ON SPEECH',
      band: 'LOW',
      action: 'EVALUATING',
    },
    context: {
      claimed_identity: 'evaluator.live_judge',
      verified_identity: null,
      enrollment_status: 'NOT_ENROLLED',
      known_contact: 'LIVE_TEST',
      call_source: 'BROWSER_MIC',
      voip_mobile_indicator: 'MIC',
      language: 'en',
    },
    transaction: {
      caller_identity: 'evaluator.live_judge',
      amount: '500000.00',
      beneficiary: 'Live Evaluation Test Beneficiary',
      beneficiary_novelty: 'KNOWN',
      currency: 'INR',
      transaction_type: 'WIRE_TRANSFER',
    },
  },
];

export const DemoControl: React.FC = () => {
  const { state, startDemo, startMic, stopSession, reset, busy } = useSession();
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

    if (scenario.id === 'live-mic') {
      void startMic({
        callerRef: scenario.callerRef,
        context: contextWithProfile,
        transaction: scenario.transaction,
      });
    } else {
      void startDemo({
        fixture: scenario.fixture as ReplayFixture,
        callerRef: scenario.callerRef,
        scenarioId: scenario.id,
        context: contextWithProfile,
        transaction: scenario.transaction,
      });
    }
  };

  return (
    <section
      aria-label="Demo Mode Control Panel"
      className="rounded-2xl border border-amber-500/30 bg-gradient-to-b from-amber-500/[0.07] via-surface to-surface p-5 shadow-lg shadow-black/20"
    >
      {/* Header Banner */}
      <div className="flex flex-col gap-3 pb-4 border-b border-border/80 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-amber-500/20 text-amber-400 ring-1 ring-amber-500/40">
            <FlaskConical className="h-5 w-5" aria-hidden="true" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs font-bold tracking-wider uppercase text-amber-400">
                DEMO MODE
              </span>
              <span className="rounded bg-amber-500/10 px-2 py-0.5 font-mono text-[0.6875rem] text-amber-300 ring-1 ring-amber-500/30">
                Simulation Only
              </span>
            </div>
            <p className="mt-0.5 text-xs text-fg-secondary">
              This environment uses controlled test audio and simulated transaction context.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {finished ? (
            <button
              type="button"
              onClick={reset}
              className="rounded-lg border border-border-strong bg-surface-elevated px-3 py-1.5 text-xs font-medium text-fg-secondary transition-colors hover:bg-surface-hover hover:text-fg"
            >
              Reset Session
            </button>
          ) : null}

          {running ? (
            <button
              type="button"
              disabled={busy}
              onClick={() => void stopSession()}
              className={cn(
                'inline-flex items-center gap-2 rounded-lg border border-red-500/40 bg-red-500/10 px-4 py-1.5',
                'text-xs font-medium text-red-400 transition-colors hover:bg-red-500/20',
                'disabled:cursor-not-allowed disabled:opacity-40',
              )}
            >
              {busy ? <Spinner /> : <Square className="h-3.5 w-3.5" aria-hidden />}
              Stop Call
            </button>
          ) : (
            <button
              type="button"
              disabled={busy}
              data-testid="start-demo"
              onClick={handleStart}
              className={cn(
                'inline-flex items-center gap-2 rounded-lg border border-amber-500/60 bg-amber-500/20 px-4 py-1.5',
                'text-xs font-semibold text-amber-300 shadow-sm transition-all hover:bg-amber-500/30 hover:text-amber-200',
                'disabled:cursor-not-allowed disabled:opacity-40',
              )}
            >
              {busy ? (
                <Spinner />
              ) : scenario.id === 'live-mic' ? (
                <Mic className="h-3.5 w-3.5 text-amber-300 animate-pulse" aria-hidden />
              ) : (
                <Play className="h-3.5 w-3.5 fill-current" aria-hidden />
              )}
              {scenario.id === 'live-mic' ? 'Start Live Microphone Call' : 'Start Scenario Call'}
            </button>
          )}
        </div>
      </div>

      {/* Scenario Selector & Details Grid */}
      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-12">
        {/* Scenario Selection Buttons */}
        <div className="space-y-2 lg:col-span-4">
          <label className="font-mono text-micro uppercase text-fg-tertiary">
            Select Test Scenario
          </label>
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
                    'w-full rounded-xl border p-3 text-left transition-all',
                    active
                      ? 'border-amber-500/50 bg-amber-500/10 ring-1 ring-amber-500/30'
                      : 'border-border bg-surface/50 hover:border-border-strong hover:bg-surface-elevated',
                    (running || busy) && 'disabled:cursor-not-allowed disabled:opacity-60',
                  )}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-semibold text-xs text-fg flex items-center gap-1.5">
                      {item.id === 'live-mic' ? <Mic className="h-3.5 w-3.5 text-accent" /> : null}
                      {item.name}
                    </span>
                    <span
                      className={cn(
                        'rounded px-1.5 py-0.5 font-mono text-[0.625rem]',
                        item.expectedOutcome.band === 'LOW' && 'bg-emerald-500/10 text-emerald-400',
                        item.expectedOutcome.band === 'HIGH' && 'bg-red-500/10 text-red-400',
                        item.expectedOutcome.band === 'UNCERTAIN' && 'bg-amber-500/10 text-amber-400',
                      )}
                    >
                      {item.badge}
                    </span>
                  </div>
                  <p className="mt-1 line-clamp-2 text-xs text-fg-tertiary">{item.summary}</p>
                </button>
              );
            })}
          </div>
        </div>

        {/* Selected Scenario Inspector Card */}
        <div className="flex flex-col justify-between rounded-xl border border-border bg-surface-elevated/40 p-4 lg:col-span-8">
          <div>
            <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-border/60">
              <div>
                <h3 className="text-sm font-semibold text-fg">{scenario.name}</h3>
                <p className="mt-0.5 text-xs text-fg-secondary">{scenario.summary}</p>
              </div>
              <div className="flex items-center gap-1.5 rounded-lg bg-surface px-2.5 py-1 ring-1 ring-border">
                {scenario.id === 'live-mic' ? (
                  <Mic className="h-3.5 w-3.5 text-accent" />
                ) : (
                  <Volume2 className="h-3.5 w-3.5 text-fg-tertiary" />
                )}
                <span className="font-mono text-xs text-fg-secondary">
                  Ingress: <strong className="text-fg">{scenario.id === 'live-mic' ? 'Browser 16kHz PCM' : `${scenario.fixture}.wav`}</strong>
                </span>
              </div>
            </div>

            {/* Scenario Parameter Chips */}
            <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-3">
              <div className="rounded-lg bg-surface/70 p-2.5 ring-1 ring-border/50">
                <span className="font-mono text-micro uppercase text-fg-tertiary">Caller</span>
                <p className="mt-0.5 truncate text-xs font-medium text-fg">{scenario.callerName}</p>
                <p className="font-mono text-micro text-fg-tertiary">{scenario.callerRef}</p>
              </div>

              <div className="rounded-lg bg-surface/70 p-2.5 ring-1 ring-border/50">
                <span className="font-mono text-micro uppercase text-fg-tertiary">
                  Transaction Context
                </span>
                <p className="mt-0.5 font-mono text-xs font-semibold text-amber-300">
                  {scenario.id === 'live-mic' ? '₹5,00,000' : '₹25,00,000'}
                </p>
                <p className="truncate text-micro text-fg-tertiary">
                  {scenario.transaction?.beneficiary}
                </p>
              </div>

              <div className="rounded-lg bg-surface/70 p-2.5 ring-1 ring-border/50">
                <span className="font-mono text-micro uppercase text-fg-tertiary">
                  Expected Outcome
                </span>
                <p
                  className={cn(
                    'mt-0.5 text-xs font-semibold',
                    scenario.expectedOutcome.band === 'LOW' && 'text-emerald-400',
                    scenario.expectedOutcome.band === 'HIGH' && 'text-red-400',
                    scenario.expectedOutcome.band === 'UNCERTAIN' && 'text-amber-400',
                  )}
                >
                  {scenario.expectedOutcome.label}
                </p>
                <p className="text-micro text-fg-tertiary">Computed live by L1-L5 pipeline</p>
              </div>
            </div>

            {/* Policy Profile Sensitivity Tuning */}
            <div className="mt-3 flex items-center justify-between rounded-lg bg-surface/40 px-3 py-2 border border-border/40">
              <div className="flex items-center gap-1.5">
                <Settings2 className="h-3.5 w-3.5 text-fg-tertiary" />
                <span className="font-mono text-xs text-fg-secondary">Policy Profile:</span>
              </div>
              <div className="flex gap-1.5">
                {(['STANDARD', 'STRICT', 'LOW_FRICTION'] as const).map((mode) => (
                  <button
                    key={mode}
                    type="button"
                    disabled={running || busy}
                    onClick={() => setPolicyProfile(mode)}
                    className={cn(
                      'rounded px-2 py-0.5 font-mono text-[0.6875rem] transition-colors',
                      policyProfile === mode
                        ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 font-bold'
                        : 'bg-surface text-fg-tertiary hover:text-fg border border-border',
                      (running || busy) && 'disabled:cursor-not-allowed disabled:opacity-50',
                    )}
                  >
                    {mode === 'STANDARD' ? 'Standard (0.70)' : mode === 'STRICT' ? 'Strict (0.50)' : 'Low Friction (0.85)'}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Environmental Disclaimer Note */}
          <div className="mt-4 flex items-center gap-2 rounded-lg border border-border/50 bg-background/50 px-3 py-2 text-[0.75rem] text-fg-tertiary">
            <AlertCircle className="h-4 w-4 shrink-0 text-amber-400/70" />
            <span>
              <strong>Notice:</strong> Do not call the scenarios production functionality. The
              scenario engine supplies only fixture transport and context; risk scores and hold
              actions are strictly calculated by real-time models and policy rules.
            </span>
          </div>
        </div>
      </div>
    </section>
  );
};

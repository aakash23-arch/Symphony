/**
 * WebSocket wire types for WS /ws/sessions/{id}.
 *
 * The server sends two structurally different message shapes:
 *
 *   1. Envelopes  - `{seq, session_id, event_type, timestamp, data}`
 *   2. A snapshot - a BARE object `{type: 'session.snapshot', ...}` with no
 *                   `seq` and no `event_type`.
 *
 * So the discriminator is which key exists, not the value of one field.
 * `isSnapshot` below is the only place that decision is made.
 *
 * The envelope payloads are deliberately THIN: `risk.updated` carries no
 * `top_factors` and `belief.updated` carries no `trajectory`. Those structural
 * fields only ever arrive via REST, which is why the provider refetches
 * /evidence and /risk when a risk update lands.
 */

import type {
  ClockType,
  DecisionBand,
  PolicyAction,
  RiskBand,
  RiskDecision,
  ScoreSemantics,
  SessionLifecycleState,
  TimelineEntry,
  VoiceBelief,
} from './contracts';

export type SessionEventType =
  | 'session.started'
  | 'session.stopped'
  | 'session.error'
  | 'frame.processed'
  | 'quality.telemetry'
  | 'belief.updated'
  | 'risk.updated'
  | 'decision.emitted'
  | 'timeline.event'
  | 'state.transition'
  | 'evidence.emitted'
  | 'evidence.recorded'
  | 'tamper.alert';

export interface WebSocketEventEnvelope<T = unknown> {
  seq: number;
  session_id: string;
  event_type: SessionEventType;
  timestamp: string;
  data: T;
}

/** `frame.processed` — the whitelist in ws_audio._frame_telemetry. */
export interface FrameTelemetry {
  frame_id: number;
  t_start: number;
  t_end: number;
  is_speech: boolean;
  q_t: number | null;
  packet_loss: number | null;
  bandwidth: number | null;
  lang_t: string;
  source_type: string;
}

/** `belief.updated` — scalars only, no trajectory and no expert list. */
export interface BeliefUpdate {
  frame_id: number;
  t_end: number;
  P_spoof: number | null;
  confidence: number;
  band: DecisionBand;
  clock: ClockType;
  q_call: number | null;
  uncertainty_reason: string | null;
}

/** `risk.updated` — scalars only, no contributions and no evidence refs. */
export interface RiskUpdate {
  risk_score: number;
  risk_band: RiskBand;
  risk_confidence: number;
  score_semantics: ScoreSemantics;
  score_label: string;
  action: PolicyAction;
  matched_policy: string;
  reason_codes: string[];
  fail_safe_engaged: boolean;
  policy_version: string;
  timestamp: string;
}

/** `decision.emitted`. */
export interface DecisionEmitted {
  action: PolicyAction;
  matched_policy: string;
  transaction_tier: number;
  recommended_verifications: string[];
  timestamp: string;
}

export interface SessionStartedData {
  state: SessionLifecycleState;
  source_type: string;
  started_at: string | null;
  scenario_id: string | null;
}

export interface SessionStoppedData {
  state: SessionLifecycleState;
  reason: string | null;
  frames_published: number;
  frames_dropped: number;
}

/**
 * The opening snapshot. Carries FULL decision and belief objects (unlike the
 * envelopes), plus the last 20 timeline entries — which is why timeline is
 * merged by seq rather than replaced.
 */
export interface SessionSnapshot {
  type: 'session.snapshot';
  session_id: string;
  session_state: SessionLifecycleState;
  source_type: string;
  scenario_id: string | null;
  started_at: string | null;
  frames_published: number;
  frames_seen: number;
  frames_scored: number;
  frames_skipped: number;
  decision: RiskDecision | null;
  belief: VoiceBelief | null;
  timeline: TimelineEntry[];
  analysis_degraded: boolean;
  degradation_reasons: string[];
}

/** An error frame the server sends before closing (e.g. unknown session). */
export interface SocketErrorFrame {
  type: 'error';
  code: string;
  session_id?: string;
  message?: string;
}

export type SocketMessage =
  | SessionSnapshot
  | SocketErrorFrame
  | WebSocketEventEnvelope;

export function isSnapshot(message: SocketMessage): message is SessionSnapshot {
  return (message as SessionSnapshot).type === 'session.snapshot';
}

export function isErrorFrame(message: SocketMessage): message is SocketErrorFrame {
  return (message as SocketErrorFrame).type === 'error';
}

export function isEnvelope(message: SocketMessage): message is WebSocketEventEnvelope {
  return typeof (message as WebSocketEventEnvelope).event_type === 'string';
}

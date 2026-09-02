/**
 * Session state reducer. Pure: no fetching, no sockets, no timers.
 *
 * The type shape enforces the project's cardinal rule. `decision` is
 * `RiskDecision | null` and `riskStatus` is separate, so a component literally
 * cannot render "LOW / 0.00" for a session that has produced nothing - there is
 * no object to read from. Never introduce a default RiskDecision to "simplify"
 * this; that would make the 409 invisible.
 *
 * `belief` (full, from REST/snapshot) and `beliefLive` (thin, from WS) are kept
 * apart deliberately. The WS belief payload has no trajectory and no expert
 * list, so patching it onto a VoiceBelief would produce an object whose type
 * claims fields it does not have.
 */

import type {
  DemoTransaction,
  RiskAssessment,
  RiskDecision,
  SessionEvidenceResponse,
  SessionLifecycleState,
  TimelineEntry,
  VoiceBelief,
} from '../types/contracts';
import type {
  BeliefUpdate,
  DecisionEmitted,
  FrameTelemetry,
  RiskUpdate,
  SessionSnapshot,
  SessionStartedData,
  SessionStoppedData,
} from '../types/events';
import { assertNever } from '../lib/format';

export type ConnectionState =
  | 'idle'
  | 'connecting'
  | 'open'
  | 'reconnecting'
  /** Session reached a terminal state and the server closed. Not an error. */
  | 'closed_terminal'
  | 'failed';

export type RiskStatus = 'idle' | 'awaiting_first' | 'ready' | 'error';
export type LoadStatus = 'idle' | 'loading' | 'ready' | 'error';

export const TIMELINE_CAP = 200;

export interface LiveAnalysisPoint {
  frameId: number;
  tEnd: number;
  spoofProbability: number | null;
  confidence: number;
  band: string;
  riskScore?: number;
  riskBand?: string;
  action?: string;
}

export interface SessionState {
  sessionId: string | null;
  sessionState: SessionLifecycleState | null;
  sourceType: string | null;
  scenarioId: string | null;
  callerRef: string | null;
  startedAt: string | null;
  stoppedAt: string | null;

  connection: ConnectionState;
  reconnectAttempt: number;
  lastSeq: number;
  seqGapDetected: boolean;
  /** When the last live message arrived; drives the staleness marker. */
  lastMessageAt: string | null;

  decision: RiskDecision | null;
  riskStatus: RiskStatus;
  riskMessage: string | null;

  belief: VoiceBelief | null;
  beliefLive: BeliefUpdate | null;

  liveAnalysisPoints: LiveAnalysisPoint[];
  isAnalyzing: boolean;

  evidence: SessionEvidenceResponse | null;
  evidenceStatus: LoadStatus;

  lastFrame: FrameTelemetry | null;
  languages: string[];

  framesPublished: number;
  framesSeen: number;
  framesScored: number;
  framesSkipped: number;

  analysisDegraded: boolean;
  degradationReasons: string[];

  timeline: TimelineEntry[];

  transaction: DemoTransaction | null;
  transactionStatus: LoadStatus;

  error: { code: string; message: string; retriable: boolean } | null;
}

export const initialSessionState: SessionState = {
  sessionId: null,
  sessionState: null,
  sourceType: null,
  scenarioId: null,
  callerRef: null,
  startedAt: null,
  stoppedAt: null,
  connection: 'idle',
  reconnectAttempt: 0,
  lastSeq: 0,
  seqGapDetected: false,
  lastMessageAt: null,
  decision: null,
  riskStatus: 'idle',
  riskMessage: null,
  belief: null,
  beliefLive: null,
  liveAnalysisPoints: [],
  isAnalyzing: false,
  evidence: null,
  evidenceStatus: 'idle',
  lastFrame: null,
  languages: [],
  framesPublished: 0,
  framesSeen: 0,
  framesScored: 0,
  framesSkipped: 0,
  analysisDegraded: false,
  degradationReasons: [],
  timeline: [],
  transaction: null,
  transactionStatus: 'idle',
  error: null,
};

export type SessionAction =
  | {
      type: 'SESSION_CREATED';
      sessionId: string;
      sourceType: string;
      scenarioId: string | null;
      callerRef: string | null;
    }
  | { type: 'SESSION_RESET' }
  | { type: 'CONNECTION'; connection: ConnectionState; attempt?: number }
  | { type: 'SNAPSHOT'; snapshot: SessionSnapshot; at: string }
  | { type: 'SESSION_STARTED'; data: SessionStartedData; seq: number; at: string }
  | { type: 'SESSION_STOPPED'; data: SessionStoppedData; seq: number; at: string }
  | { type: 'FRAME'; data: FrameTelemetry; seq: number; at: string }
  | { type: 'BELIEF_PATCH'; data: BeliefUpdate; seq: number; at: string }
  | { type: 'RISK_PATCH'; data: RiskUpdate; seq: number; at: string }
  | { type: 'DECISION_PATCH'; data: DecisionEmitted; seq: number; at: string }
  | { type: 'TIMELINE_APPEND'; entry: TimelineEntry; seq: number; at: string }
  | {
      type: 'RISK_LOADED';
      decision: RiskDecision;
      belief: VoiceBelief | null;
      analysisDegraded: boolean;
      degradationReasons: string[];
      framesSeen: number;
      framesScored: number;
      framesSkipped: number;
    }
  | { type: 'RISK_AWAITING'; message: string }
  | { type: 'RISK_ERROR'; code: string; message: string; retriable: boolean }
  | { type: 'EVIDENCE_STATUS'; status: LoadStatus }
  | { type: 'EVIDENCE_LOADED'; evidence: SessionEvidenceResponse }
  | { type: 'TIMELINE_MERGE'; entries: TimelineEntry[] }
  | { type: 'TRANSACTION_STATUS'; status: LoadStatus }
  | { type: 'TRANSACTION_LOADED'; transaction: DemoTransaction | null }
  | {
      type: 'SESSION_DETAIL';
      state: SessionLifecycleState;
      startedAt: string | null;
      stoppedAt: string | null;
      framesPublished: number;
    }
  | { type: 'ERROR'; code: string; message: string; retriable: boolean }
  | { type: 'CLEAR_ERROR' }
  | { type: 'AUDIO_FINISHED' }
  | { type: 'ERROR'; code: string; message: string; retriable: boolean }
  | { type: 'CLEAR_ERROR' }
  | { type: 'AUDIO_FINISHED' }
  | { type: 'RESYNCED' };

/** Merge timeline entries by seq: dedupe, sort ascending, cap at TIMELINE_CAP. */
function mergeTimeline(existing: TimelineEntry[], incoming: TimelineEntry[]): TimelineEntry[] {
  if (incoming.length === 0) return existing;
  const bySeq = new Map<number, TimelineEntry>();
  for (const entry of existing) bySeq.set(entry.seq, entry);
  for (const entry of incoming) bySeq.set(entry.seq, entry);
  const merged = Array.from(bySeq.values()).sort((a, b) => a.seq - b.seq);
  return merged.length > TIMELINE_CAP ? merged.slice(merged.length - TIMELINE_CAP) : merged;
}

/**
 * Track envelope sequence. A gap means EventBus dropped events on a full queue
 * (it does so silently), so the caller re-syncs over REST and the UI says so.
 */
function trackSeq(
  state: SessionState,
  seq: number,
  at: string,
): Pick<SessionState, 'lastSeq' | 'seqGapDetected' | 'lastMessageAt'> {
  const gap = state.lastSeq > 0 && seq > state.lastSeq + 1;
  return {
    lastSeq: Math.max(state.lastSeq, seq),
    seqGapDetected: state.seqGapDetected || gap,
    lastMessageAt: at,
  };
}

export function sessionReducer(state: SessionState, action: SessionAction): SessionState {
  switch (action.type) {
    case 'SESSION_CREATED':
      return {
        ...initialSessionState,
        sessionId: action.sessionId,
        sourceType: action.sourceType,
        scenarioId: action.scenarioId,
        callerRef: action.callerRef,
        sessionState: 'CREATED',
        connection: 'idle',
      };

    case 'SESSION_RESET':
      return {
        ...initialSessionState,
      };

    case 'CONNECTION':
      return {
        ...state,
        connection: action.connection,
        reconnectAttempt:
          action.attempt ?? (action.connection === 'open' ? 0 : state.reconnectAttempt),
      };

    case 'SNAPSHOT': {
      const s = action.snapshot;
      return {
        ...state,
        sessionId: s.session_id,
        sessionState: s.session_state,
        sourceType: s.source_type,
        scenarioId: s.scenario_id,
        startedAt: s.started_at,
        framesPublished: s.frames_published,
        framesSeen: s.frames_seen,
        framesScored: s.frames_scored,
        framesSkipped: s.frames_skipped,
        // Authoritative for decision/belief; null here genuinely means "none yet".
        decision: s.decision,
        riskStatus: s.decision
          ? 'ready'
          : state.riskStatus === 'idle'
            ? 'awaiting_first'
            : state.riskStatus,
        belief: s.belief,
        analysisDegraded: s.analysis_degraded,
        degradationReasons: s.degradation_reasons,
        // Merged, not replaced: a reconnect snapshot carries only the last 20.
        timeline: mergeTimeline(state.timeline, s.timeline),
        lastMessageAt: action.at,
      };
    }

    case 'SESSION_STARTED':
      return {
        ...state,
        ...trackSeq(state, action.seq, action.at),
        sessionState: action.data.state,
        sourceType: action.data.source_type,
        scenarioId: action.data.scenario_id,
        startedAt: action.data.started_at,
        isAnalyzing: true,
        liveAnalysisPoints: [],
      };

    case 'SESSION_STOPPED':
      return {
        ...state,
        ...trackSeq(state, action.seq, action.at),
        sessionState: action.data.state,
        framesPublished: action.data.frames_published,
        connection: 'closed_terminal',
        stoppedAt: action.at,
        isAnalyzing: false,
      };

    case 'AUDIO_FINISHED':
      return {
        ...state,
        isAnalyzing: false,
      };

    case 'FRAME': {
      const lang = action.data.lang_t;
      const isNew = Boolean(lang) && lang !== 'UNKNOWN' && !state.languages.includes(lang);
      return {
        ...state,
        ...trackSeq(state, action.seq, action.at),
        lastFrame: action.data,
        languages: isNew ? [...state.languages, lang] : state.languages,
      };
    }

    case 'BELIEF_PATCH': {
      const b = action.data;
      const newPoint: LiveAnalysisPoint = {
        frameId: b.frame_id,
        tEnd: b.t_end,
        spoofProbability: b.P_spoof,
        confidence: b.confidence,
        band: b.band,
        riskScore: state.decision?.risk.risk_score,
        riskBand: state.decision?.risk.risk_band,
        action: state.decision?.action,
      };
      const existingIdx = state.liveAnalysisPoints.findIndex((p) => p.frameId === b.frame_id);
      let updatedPoints: LiveAnalysisPoint[];
      if (existingIdx >= 0) {
        updatedPoints = [...state.liveAnalysisPoints];
        updatedPoints[existingIdx] = { ...updatedPoints[existingIdx], ...newPoint };
      } else {
        updatedPoints = [...state.liveAnalysisPoints, newPoint];
      }
      if (updatedPoints.length > 60) {
        updatedPoints = updatedPoints.slice(updatedPoints.length - 60);
      }
      return {
        ...state,
        ...trackSeq(state, action.seq, action.at),
        beliefLive: action.data,
        liveAnalysisPoints: updatedPoints,
      };
    }

    case 'RISK_PATCH': {
      const u = action.data;
      const riskAssessment: RiskAssessment = {
        session_id: state.sessionId ?? '',
        risk_score: u.risk_score,
        risk_confidence: u.risk_confidence,
        risk_band: u.risk_band,
        contributions: state.decision?.risk.contributions ?? [],
        context_degraded: state.decision?.risk.context_degraded ?? false,
        score_semantics: u.score_semantics,
        score_label: u.score_label,
        timestamp: u.timestamp,
      };

      const decision: RiskDecision = {
        session_id: state.sessionId ?? '',
        risk: riskAssessment,
        action: u.action,
        matched_policy: u.matched_policy,
        transaction_tier: state.decision?.transaction_tier ?? ('STANDARD' as any),
        reason_codes: u.reason_codes,
        top_factors: state.decision?.top_factors ?? [],
        evidence_refs: state.decision?.evidence_refs ?? [],
        recommended_verifications: state.decision?.recommended_verifications ?? [],
        fail_safe_engaged: u.fail_safe_engaged,
        policy_version: u.policy_version,
        timestamp: u.timestamp,
      };

      // Associate risk information with the most recent live analysis points
      const updatedPoints = state.liveAnalysisPoints.map((pt, idx) => {
        if (idx === state.liveAnalysisPoints.length - 1) {
          return { ...pt, riskScore: u.risk_score, riskBand: u.risk_band, action: u.action };
        }
        return pt;
      });

      return {
        ...state,
        ...trackSeq(state, action.seq, action.at),
        decision,
        riskStatus: 'ready',
        liveAnalysisPoints: updatedPoints,
      };
    }

    case 'DECISION_PATCH': {
      const d = action.data;
      if (!state.decision) return state;
      return {
        ...state,
        ...trackSeq(state, action.seq, action.at),
        decision: {
          ...state.decision,
          action: d.action,
          matched_policy: d.matched_policy,
          recommended_verifications: d.recommended_verifications,
        },
      };
    }

    case 'TIMELINE_APPEND':
      return {
        ...state,
        ...trackSeq(state, action.seq, action.at),
        timeline: mergeTimeline(state.timeline, [action.entry]),
      };

    case 'RISK_LOADED':
      return {
        ...state,
        decision: action.decision,
        belief: action.belief,
        riskStatus: 'ready',
        riskMessage: null,
        analysisDegraded: action.analysisDegraded,
        degradationReasons: action.degradationReasons,
        framesSeen: action.framesSeen,
        framesScored: action.framesScored,
        framesSkipped: action.framesSkipped,
      };

    case 'RISK_AWAITING':
      // Explicitly leaves `decision` null. This is the 409, and it is a state.
      return { ...state, riskStatus: 'awaiting_first', riskMessage: action.message };

    case 'RISK_ERROR':
      return {
        ...state,
        riskStatus: 'error',
        error: { code: action.code, message: action.message, retriable: action.retriable },
      };

    case 'EVIDENCE_STATUS':
      return { ...state, evidenceStatus: action.status };

    case 'EVIDENCE_LOADED':
      return {
        ...state,
        evidence: action.evidence,
        evidenceStatus: 'ready',
        framesSeen: Math.max(state.framesSeen, action.evidence.frames_seen),
        framesScored: Math.max(state.framesScored, action.evidence.frames_scored),
      };

    case 'TIMELINE_MERGE':
      return { ...state, timeline: mergeTimeline(state.timeline, action.entries) };

    case 'TRANSACTION_STATUS':
      return { ...state, transactionStatus: action.status };

    case 'TRANSACTION_LOADED':
      return { ...state, transaction: action.transaction, transactionStatus: 'ready' };

    case 'SESSION_DETAIL':
      return {
        ...state,
        sessionState: action.state,
        startedAt: action.startedAt,
        stoppedAt: action.stoppedAt,
        framesPublished: action.framesPublished,
      };

    case 'ERROR':
      return {
        ...state,
        error: { code: action.code, message: action.message, retriable: action.retriable },
      };

    case 'CLEAR_ERROR':
      return { ...state, error: null };

    case 'RESYNCED':
      return { ...state, seqGapDetected: false };

    default:
      assertNever(action);
      return state;
  }
}

/** True when the session can no longer produce events. */
export function isTerminal(state: SessionState): boolean {
  return (
    state.sessionState === 'STOPPED' ||
    state.sessionState === 'FAILED' ||
    state.sessionState === 'INTERRUPTED'
  );
}

/** True when displayed values are last-known rather than live. */
export function isStale(state: SessionState): boolean {
  return state.connection === 'reconnecting' || state.connection === 'failed';
}

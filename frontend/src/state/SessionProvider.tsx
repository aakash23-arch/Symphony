/**
 * Session context: the one place with side effects.
 *
 * Wires the socket and the REST refreshes onto the pure reducer. The key
 * non-obvious behaviour is the evidence/risk refetch: the WS `risk.updated`
 * payload is thin (no top_factors, no contributions) and `belief.updated`
 * carries no trajectory, so structural data can only come from REST. A risk
 * update therefore schedules a debounced refetch rather than assuming the
 * socket said everything.
 */

import React, {
  createContext,
  useCallback,
  useEffect,
  useMemo,
  useReducer,
  useRef,
} from 'react';

import * as api from '../api/client';
import { connectSessionSocket, type SessionSocket, type SocketStatus } from '../api/socket';
import type { HealthResponse, ReplayFixture } from '../types/contracts';
import {
  isEnvelope,
  isErrorFrame,
  isSnapshot,
  type BeliefUpdate,
  type DecisionEmitted,
  type FrameTelemetry,
  type RiskUpdate,
  type SessionSnapshot,
  type SessionStartedData,
  type SessionStoppedData,
  type SocketMessage,
} from '../types/events';
import {
  initialSessionState,
  sessionReducer,
  type SessionAction,
  type SessionState,
} from './sessionReducer';

/** Trailing debounce for the post-risk-update REST refresh. */
const REFRESH_DEBOUNCE_MS = 400;
/** Cross-client drift safety net. The fast paths are event-driven. */
const TRANSACTION_POLL_MS = 10_000;

export interface StartOptions {
  fixture: ReplayFixture;
  callerRef?: string;
  scenarioId?: string;
  context?: Record<string, unknown>;
  transaction?: {
    caller_identity: string;
    amount: string;
    beneficiary: string;
    beneficiary_novelty?: string;
    currency?: string;
    transaction_type?: string;
  };
}

export interface StartMicOptions {
  callerRef?: string;
  context?: Record<string, unknown>;
  transaction?: {
    caller_identity: string;
    amount: string;
    beneficiary: string;
    beneficiary_novelty?: string;
    currency?: string;
    transaction_type?: string;
  };
}

export interface SessionContextValue {
  state: SessionState;
  health: HealthResponse | null;
  healthError: string | null;
  startDemo: (options: StartOptions) => Promise<void>;
  stopSession: () => Promise<void>;
  reset: () => void;
  holdTransaction: (reason: string) => Promise<void>;
  releaseTransaction: (verificationReference: string, approve: boolean) => Promise<void>;
  busy: boolean;
  audioPlaying: boolean;
  audioMuted: boolean;
  toggleMute: () => void;
  audioCurrentTime: number;
  audioDuration: number;
  audioAnalyserRef: React.RefObject<AnalyserNode | null>;
}

export const SessionContext = createContext<SessionContextValue | null>(null);

export const SessionProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [state, dispatch] = useReducer(sessionReducer, initialSessionState);
  const [health, setHealth] = React.useState<HealthResponse | null>(null);
  const [healthError, setHealthError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  const [audioPlaying, setAudioPlaying] = React.useState(false);
  const [audioMuted, setAudioMuted] = React.useState(false);
  const [audioCurrentTime, setAudioCurrentTime] = React.useState(0);
  const [audioDuration, setAudioDuration] = React.useState(0);

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);

  const socketRef = useRef<SessionSocket | null>(null);
  const refreshTimer = useRef<number | undefined>(undefined);
  const abortRef = useRef<AbortController | null>(null);
  const sessionIdRef = useRef<string | null>(null);
  const mountedRef = useRef(true);

  const toggleMute = useCallback(() => {
    setAudioMuted((prev) => {
      const next = !prev;
      if (audioRef.current) {
        audioRef.current.muted = next;
      }
      return next;
    });
  }, []);


  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const safeDispatch = useCallback((action: SessionAction) => {
    if (mountedRef.current) dispatch(action);
  }, []);

  // --- health -----------------------------------------------------------------

  useEffect(() => {
    const controller = new AbortController();
    api
      .getHealth(controller.signal)
      .then((data) => {
        if (mountedRef.current) setHealth(data);
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted || !mountedRef.current) return;
        setHealthError(error instanceof Error ? error.message : 'Health check failed');
      });
    return () => controller.abort();
  }, []);

  // --- REST refresh -----------------------------------------------------------

  /**
   * Pull the structural data the socket cannot carry. Aborts any in-flight
   * refresh first, which is what prevents a late response from a previous
   * session overwriting the current one (and the setState-after-unmount warning
   * that would otherwise appear in the console).
   */
  const refresh = useCallback(
    async (sessionId: string, options?: { skipRisk?: boolean }) => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      safeDispatch({ type: 'EVIDENCE_STATUS', status: 'loading' });

      // Skip the risk call when the caller already knows no assessment
      // exists. The 409 is correct protocol, but the browser still logs every
      // 4xx to the console as a failed resource, and the requirement is a
      // console with no errors in it.
      const [riskResult, evidenceResult] = await Promise.allSettled([
        options?.skipRisk
          ? Promise.resolve({ kind: 'awaiting' as const, message: '' })
          : api.getRisk(sessionId, controller.signal),
        api.getEvidence(sessionId, controller.signal),
      ]);

      if (controller.signal.aborted || sessionIdRef.current !== sessionId) return;

      if (riskResult.status === 'fulfilled') {
        const result = riskResult.value;
        if (result.kind === 'ready') {
          const data = result.data;
          safeDispatch({
            type: 'RISK_LOADED',
            decision: data.decision,
            belief: data.belief,
            analysisDegraded: data.analysis_degraded,
            degradationReasons: data.degradation_reasons,
            framesSeen: data.frames_seen,
            framesScored: data.frames_scored,
            framesSkipped: data.frames_skipped,
          });
        } else if (result.kind === 'awaiting') {
          if (result.message) safeDispatch({ type: 'RISK_AWAITING', message: result.message });
        } else {
          safeDispatch({
            type: 'RISK_ERROR',
            code: result.error.code,
            message: result.error.message,
            retriable: result.error.retriable,
          });
        }
      }

      if (evidenceResult.status === 'fulfilled') {
        safeDispatch({ type: 'EVIDENCE_LOADED', evidence: evidenceResult.value });
      } else {
        safeDispatch({ type: 'EVIDENCE_STATUS', status: 'error' });
      }
    },
    [safeDispatch],
  );

  const scheduleRefresh = useCallback(
    (sessionId: string, options?: { skipRisk?: boolean }) => {
      if (refreshTimer.current !== undefined) window.clearTimeout(refreshTimer.current);
      refreshTimer.current = window.setTimeout(() => {
        void refresh(sessionId, options);
      }, REFRESH_DEBOUNCE_MS);
    },
    [refresh],
  );

  const loadTransaction = useCallback(
    async (sessionId: string, transactionId?: string) => {
      try {
        const transaction = transactionId
          ? (await api.getTransaction(transactionId)).transaction
          : await api.findSessionTransaction(sessionId);
        if (sessionIdRef.current === sessionId) {
          safeDispatch({ type: 'TRANSACTION_LOADED', transaction });
        }
      } catch {
        safeDispatch({ type: 'TRANSACTION_STATUS', status: 'error' });
      }
    },
    [safeDispatch],
  );

  // --- socket -----------------------------------------------------------------

  const handleMessage = useCallback(
    (raw: unknown, sessionId: string) => {
      const message = raw as SocketMessage;
      const at = new Date().toISOString();

      if (isErrorFrame(message)) {
        safeDispatch({
          type: 'ERROR',
          code: message.code,
          message: message.message ?? 'Session stream error',
          retriable: false,
        });
        return;
      }

      if (isSnapshot(message)) {
        const snapshot = message as SessionSnapshot;
        safeDispatch({ type: 'SNAPSHOT', snapshot, at });
        // The snapshot carries full decision/belief objects but no evidence, so
        // fetch that. It also already says whether an assessment exists, so a
        // risk call is only worth making when one does.
        scheduleRefresh(sessionId, { skipRisk: snapshot.decision === null });
        return;
      }

      if (!isEnvelope(message)) return;

      const { seq, event_type: kind, data } = message;

      switch (kind) {
        case 'session.started':
          safeDispatch({ type: 'SESSION_STARTED', data: data as SessionStartedData, seq, at });
          break;
        case 'session.stopped':
          socketRef.current?.markTerminal();
          safeDispatch({ type: 'SESSION_STOPPED', data: data as SessionStoppedData, seq, at });
          // One final refresh so the last assessment is complete on screen.
          scheduleRefresh(sessionId);
          break;
        case 'frame.processed':
          safeDispatch({ type: 'FRAME', data: data as FrameTelemetry, seq, at });
          break;
        case 'belief.updated':
          safeDispatch({ type: 'BELIEF_PATCH', data: data as BeliefUpdate, seq, at });
          break;
        case 'risk.updated':
          safeDispatch({ type: 'RISK_PATCH', data: data as RiskUpdate, seq, at });
          // Thin payload: top_factors and evidence refs only exist over REST.
          scheduleRefresh(sessionId);
          break;
        case 'decision.emitted':
          safeDispatch({ type: 'DECISION_PATCH', data: data as DecisionEmitted, seq, at });
          break;
        case 'timeline.event': {
          const entry = data as SocketMessage & { transaction_id?: string | null; kind?: string };
          safeDispatch({
            type: 'TIMELINE_APPEND',
            entry: data as never,
            seq,
            at,
          });
          const entryKind = String(entry.kind ?? '');
          if (entryKind.startsWith('TRANSACTION_')) {
            void loadTransaction(sessionId, entry.transaction_id ?? undefined);
          }
          break;
        }
        default:
          break;
      }
    },
    [safeDispatch, scheduleRefresh, loadTransaction],
  );

  const handleStatus = useCallback(
    (status: SocketStatus, attempt: number) => {
      safeDispatch({ type: 'CONNECTION', connection: status, attempt });
    },
    [safeDispatch],
  );

  const openSocket = useCallback(
    (sessionId: string) => {
      socketRef.current?.close();
      socketRef.current = connectSessionSocket(sessionId, {
        onMessage: (raw) => handleMessage(raw, sessionId),
        onStatus: handleStatus,
        isTerminal: async () => {
          try {
            const detail = await api.getSession(sessionId);
            return ['STOPPED', 'FAILED', 'INTERRUPTED'].includes(detail.state);
          } catch {
            return false;
          }
        },
      });
    },
    [handleMessage, handleStatus],
  );

  // --- re-sync after a detected sequence gap ----------------------------------

  useEffect(() => {
    if (!state.seqGapDetected || !state.sessionId) return;
    const sessionId = state.sessionId;
    void (async () => {
      try {
        const timeline = await api.getTimeline(sessionId);
        safeDispatch({ type: 'TIMELINE_MERGE', entries: timeline.entries });
      } catch {
        // A failed re-sync leaves the gap flag up, which is the honest outcome.
        return;
      }
      void refresh(sessionId);
      safeDispatch({ type: 'RESYNCED' });
    })();
  }, [state.seqGapDetected, state.sessionId, refresh, safeDispatch]);

  // --- transaction drift poll -------------------------------------------------

  useEffect(() => {
    if (!state.sessionId || !state.transaction) return;
    if (state.connection !== 'open') return;
    const sessionId = state.sessionId;
    const timer = window.setInterval(() => {
      if (document.hidden) return;
      void loadTransaction(sessionId);
    }, TRANSACTION_POLL_MS);
    return () => window.clearInterval(timer);
  }, [state.sessionId, state.transaction, state.connection, loadTransaction]);

  // --- teardown ---------------------------------------------------------------

  useEffect(
    () => () => {
      socketRef.current?.close();
      abortRef.current?.abort();
      if (refreshTimer.current !== undefined) window.clearTimeout(refreshTimer.current);
    },
    [],
  );

  // --- actions ----------------------------------------------------------------

  const startDemo = useCallback(
    async (options: StartOptions) => {
      setBusy(true);
      try {
        safeDispatch({ type: 'SESSION_RESET' });

        const created = await api.createSession({
          source_type: 'wav',
          scenario_id: options.scenarioId,
          caller_ref: options.callerRef,
        });
        const sessionId = created.session_id;
        sessionIdRef.current = sessionId;

        safeDispatch({
          type: 'SESSION_CREATED',
          sessionId,
          sourceType: 'wav',
          scenarioId: options.scenarioId ?? null,
          callerRef: options.callerRef ?? null,
        });

        if (options.transaction) {
          const created = await api.createTransaction({
            ...options.transaction,
            session_id: sessionId,
          });
          safeDispatch({ type: 'TRANSACTION_LOADED', transaction: created.transaction });
        }

        if (options.context) {
          await api.postContext(sessionId, options.context);
        }

        // Open the socket BEFORE start, or the first frames are missed:
        // frame.processed telemetry is never replayed.
        openSocket(sessionId);
        await api.startSession(sessionId);
        await api.startReplay(sessionId, options.fixture, 1.0, 1);

        // Initiate real audio playback in the browser for scenario call evaluation
        if (audioRef.current) {
          try {
            audioRef.current.pause();
          } catch {
            // ignore
          }
          audioRef.current = null;
        }
        try {
          // Use direct static asset path served by frontend / Vite with fallback
          const audioSrc = `/audio/${options.fixture}.wav`;
          const audio = new Audio(audioSrc);
          audio.muted = audioMuted;
          audio.preload = 'auto';

          setAudioCurrentTime(0);
          setAudioDuration(0);

          audio.ontimeupdate = () => {
            if (mountedRef.current) {
              setAudioCurrentTime(audio.currentTime);
              if (audio.duration && !isNaN(audio.duration)) {
                setAudioDuration(audio.duration);
              }
            }
          };

          try {
            const AudioContextClass =
              window.AudioContext ||
              (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
            if (AudioContextClass) {
              if (!audioContextRef.current) {
                audioContextRef.current = new AudioContextClass();
              }
              const ctx = audioContextRef.current;
              if (ctx.state === 'suspended') {
                void ctx.resume();
              }
              const analyser = ctx.createAnalyser();
              analyser.fftSize = 64;
              analyser.smoothingTimeConstant = 0.8;

              try {
                const source = ctx.createMediaElementSource(audio);
                source.connect(analyser);
                analyser.connect(ctx.destination);
              } catch (srcErr) {
                console.warn('Audio node connection note:', srcErr);
              }

              analyserRef.current = analyser;
            }
          } catch (err) {
            console.warn('Web Audio API Analyser setup notice:', err);
          }

          audio.onerror = (e) => {
            console.warn('Audio playback error on primary source, trying fallback:', e);
            if (audio.src !== `${window.location.origin}/api/demo/audio/${options.fixture}.wav`) {
              audio.src = `/api/demo/audio/${options.fixture}.wav`;
              void audio.play().catch(() => {});
            } else if (mountedRef.current) {
              setAudioPlaying(false);
              safeDispatch({ type: 'AUDIO_FINISHED' });
            }
          };
          audio.onended = () => {
            if (mountedRef.current) {
              setAudioPlaying(false);
              safeDispatch({ type: 'AUDIO_FINISHED' });
              const currentSid = sessionIdRef.current;
              if (currentSid) {
                void api.stopSession(currentSid).catch(() => {});
              }
            }
          };
          const playPromise = audio.play();
          if (playPromise !== undefined) {
            playPromise
              .then(() => {
                if (mountedRef.current) setAudioPlaying(true);
              })
              .catch((playErr) => {
                console.warn('Audio autoplay blocked or failed:', playErr);
                if (mountedRef.current) setAudioPlaying(false);
              });
          }
          audioRef.current = audio;
        } catch (audioInitErr) {
          console.warn('Audio initialization notice:', audioInitErr);
          if (mountedRef.current) setAudioPlaying(false);
        }
      } catch (error: unknown) {
        const message = error instanceof Error ? error.message : 'Could not start the session';
        const code = error instanceof api.ApiError ? error.code : 'START_FAILED';
        safeDispatch({ type: 'ERROR', code, message, retriable: true });
      } finally {
        if (mountedRef.current) setBusy(false);
      }
    },
    [openSocket, safeDispatch, audioMuted],
  );




  const stopSession = useCallback(async () => {
    if (audioRef.current) {
      try {
        audioRef.current.pause();
        audioRef.current.currentTime = 0;
      } catch {
        // ignore
      }
      audioRef.current = null;
    }
    setAudioPlaying(false);
    safeDispatch({ type: 'AUDIO_FINISHED' });

    const sessionId = sessionIdRef.current;
    if (!sessionId) return;
    setBusy(true);
    try {
      await api.stopSession(sessionId);
      await refresh(sessionId);
    } catch {
      // The socket's session.stopped is the authoritative signal; a failed
      // stop call does not need its own error banner.
    } finally {
      if (mountedRef.current) setBusy(false);
    }
  }, [refresh]);

  const reset = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    setAudioPlaying(false);
    socketRef.current?.close();
    socketRef.current = null;
    abortRef.current?.abort();
    sessionIdRef.current = null;
    safeDispatch({ type: 'SESSION_RESET' });
  }, [safeDispatch]);

  const holdTransaction = useCallback(
    async (reason: string) => {
      const transaction = state.transaction;
      if (!transaction) return;
      setBusy(true);
      try {
        const response = await api.holdTransaction(transaction.transaction_id, {
          reason,
          session_id: state.sessionId ?? undefined,
        });
        // The mutation is its own read: no refetch needed.
        safeDispatch({ type: 'TRANSACTION_LOADED', transaction: response.transaction });
      } catch (error: unknown) {
        const code = error instanceof api.ApiError ? error.code : 'HOLD_FAILED';
        const message = error instanceof Error ? error.message : 'Hold failed';
        safeDispatch({ type: 'ERROR', code, message, retriable: false });
      } finally {
        if (mountedRef.current) setBusy(false);
      }
    },
    [state.transaction, state.sessionId, safeDispatch],
  );

  const releaseTransaction = useCallback(
    async (verificationReference: string, approve: boolean) => {
      const transaction = state.transaction;
      if (!transaction) return;
      setBusy(true);
      try {
        const response = await api.releaseTransaction(transaction.transaction_id, {
          verification_reference: verificationReference,
          approve,
          session_id: state.sessionId ?? undefined,
        });
        safeDispatch({ type: 'TRANSACTION_LOADED', transaction: response.transaction });
      } catch (error: unknown) {
        const code = error instanceof api.ApiError ? error.code : 'RELEASE_FAILED';
        const message = error instanceof Error ? error.message : 'Release failed';
        safeDispatch({ type: 'ERROR', code, message, retriable: false });
      } finally {
        if (mountedRef.current) setBusy(false);
      }
    },
    [state.transaction, state.sessionId, safeDispatch],
  );

  const value = useMemo<SessionContextValue>(
    () => ({
      state,
      health,
      healthError,
      startDemo,
      stopSession,
      reset,
      holdTransaction,
      releaseTransaction,
      busy,
      audioPlaying,
      audioMuted,
      toggleMute,
      audioCurrentTime,
      audioDuration,
      audioAnalyserRef: analyserRef,
    }),
    [
      state,
      health,
      healthError,
      startDemo,
      stopSession,
      reset,
      holdTransaction,
      releaseTransaction,
      busy,
      audioPlaying,
      audioMuted,
      toggleMute,
      audioCurrentTime,
      audioDuration,
    ],
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
};

/**
 * Typed REST client.
 *
 * Two rules shape this file:
 *
 *  1. The /risk 409 is a protocol state, not a failure. `getRisk` returns a
 *     discriminated result rather than throwing, so no caller can accidentally
 *     log it as an error (the requirement is zero console errors) or fall back
 *     to a zeroed assessment.
 *  2. Every error surfaces as ApiError carrying the backend's ErrorEnvelope
 *     code, so panels can show a machine-readable reason instead of "failed".
 */

import type {
  ContextIngestResponse,
  DemoTransaction,
  ErrorEnvelope,
  HealthResponse,
  ReplayFixture,
  ReplayResponse,
  SessionDetailResponse,
  SessionEvidenceResponse,
  SessionLifecycleResponse,
  SessionResponse,
  SessionRiskResponse,
  TimelineResponse,
  TransactionListResponse,
  TransactionResponse,
} from '../types/contracts';

export class ApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly retriable: boolean;

  constructor(message: string, code: string, status: number, retriable: boolean) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.status = status;
    this.retriable = retriable;
  }
}

async function parseError(response: Response): Promise<ApiError> {
  let code = `HTTP_${response.status}`;
  let message = response.statusText || 'Request failed';
  let retriable = response.status >= 500;
  try {
    const body = (await response.json()) as Partial<ErrorEnvelope>;
    if (body && body.error) {
      code = body.error.code ?? code;
      message = body.error.message ?? message;
      retriable = body.error.retriable ?? retriable;
    }
  } catch {
    // A non-JSON error body is itself informative enough; keep the defaults.
  }
  return new ApiError(message, code, response.status, retriable);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
      ...init?.headers,
    },
  });
  if (!response.ok) throw await parseError(response);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

const json = (body: unknown): RequestInit => ({ method: 'POST', body: JSON.stringify(body) });

// --- health -------------------------------------------------------------------

export const getHealth = (signal?: AbortSignal) =>
  request<HealthResponse>('/health', { signal });

// --- sessions -----------------------------------------------------------------

export const createSession = (body: { source_type: string; scenario_id?: string; caller_ref?: string }) =>
  request<SessionResponse>('/api/sessions', json(body));

export const getSession = (id: string, signal?: AbortSignal) =>
  request<SessionDetailResponse>(`/api/sessions/${id}`, { signal });

export const startSession = (id: string) =>
  request<SessionLifecycleResponse>(`/api/sessions/${id}/start`, { method: 'POST' });

export const stopSession = (id: string) =>
  request<SessionLifecycleResponse>(`/api/sessions/${id}/stop`, { method: 'POST' });

/**
 * Play a demo fixture into a session.
 *
 * `repeat` defaults to 8 because the bundled fixtures are 1-2.5 s long, which
 * is shorter than the slow clock's own 1.5 s window: a single pass would end
 * the call before an action-grade assessment could form, leaving the dashboard
 * permanently in its awaiting state.
 */
export const startReplay = (
  id: string,
  fixture: ReplayFixture,
  speed = 1.0,
  repeat = 1,
) => request<ReplayResponse>(`/api/sessions/${id}/replay`, json({ fixture, speed, repeat }));

export const postContext = (id: string, context: Record<string, unknown>) =>
  request<ContextIngestResponse>(`/api/sessions/${id}/context`, json(context));

/**
 * Risk, with the 409 modelled as a value.
 *
 * `awaiting` means the backend has explicitly said no action-grade assessment
 * exists yet. It is NOT an error and must never be rendered as a zero score.
 */
export type RiskResult =
  | { kind: 'ready'; data: SessionRiskResponse }
  | { kind: 'awaiting'; message: string }
  | { kind: 'error'; error: ApiError };

export async function getRisk(id: string, signal?: AbortSignal): Promise<RiskResult> {
  try {
    return { kind: 'ready', data: await request<SessionRiskResponse>(`/api/sessions/${id}/risk`, { signal }) };
  } catch (error) {
    if (error instanceof ApiError && error.code === 'RISK_NOT_YET_AVAILABLE') {
      return { kind: 'awaiting', message: error.message };
    }
    if (error instanceof ApiError) return { kind: 'error', error };
    throw error;
  }
}

export const getEvidence = (id: string, signal?: AbortSignal) =>
  request<SessionEvidenceResponse>(`/api/sessions/${id}/evidence`, { signal });

export const getTimeline = (id: string, sinceSeq?: number, signal?: AbortSignal) => {
  const query = sinceSeq === undefined ? '' : `?since_seq=${sinceSeq}`;
  return request<TimelineResponse>(`/api/sessions/${id}/timeline${query}`, { signal });
};

// --- demo transactions --------------------------------------------------------

export const createTransaction = (body: {
  caller_identity: string;
  amount: string;
  beneficiary: string;
  beneficiary_novelty?: string;
  currency?: string;
  transaction_type?: string;
  session_id?: string;
}) => request<TransactionResponse>('/api/transactions', json(body));

export const getTransaction = (id: string, signal?: AbortSignal) =>
  request<TransactionResponse>(`/api/transactions/${id}`, { signal });

export const listTransactions = (sessionId?: string, signal?: AbortSignal) => {
  const query = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : '';
  return request<TransactionListResponse>(`/api/transactions${query}`, { signal });
};

export const holdTransaction = (id: string, body: { reason: string; session_id?: string }) =>
  request<TransactionResponse>(`/api/transactions/${id}/hold`, json(body));

export const releaseTransaction = (
  id: string,
  body: { verification_reference: string; approve?: boolean; session_id?: string },
) => request<TransactionResponse>(`/api/transactions/${id}/release`, json(body));

/** Convenience: the transaction linked to a session, if any. */
export async function findSessionTransaction(
  sessionId: string,
  signal?: AbortSignal,
): Promise<DemoTransaction | null> {
  const list = await listTransactions(sessionId, signal);
  return list.transactions.length > 0 ? list.transactions[list.transactions.length - 1] : null;
}

// --- demo scenarios -----------------------------------------------------------

export interface ScenarioDetail {
  scenario_id: string;
  title: string;
  summary: string;
  caller_name: string;
  caller_ref: string;
  audio_fixture: ReplayFixture;
  context: Record<string, unknown>;
  transaction?: {
    caller_identity: string;
    amount: string;
    beneficiary: string;
    beneficiary_novelty?: string;
    currency?: string;
    transaction_type?: string;
  };
  expected_outcome?: {
    risk_band: string;
    action: string;
    decision_label: string;
    target_policy?: string;
  };
  environment: string;
}

export interface ScenarioListResponse {
  scenarios: ScenarioDetail[];
  environment: string;
  disclaimer: string;
}

export interface ScenarioStartResponse {
  session_id: string;
  scenario_id: string;
  transaction_id?: string;
  audio_fixture: string;
  caller_name: string;
  caller_ref: string;
  state: string;
  environment: string;
  disclaimer: string;
  started_at: string;
}

export const listScenarios = (signal?: AbortSignal) =>
  request<ScenarioListResponse>('/api/demo/scenarios', { signal });

export const startScenario = (scenarioId: string, speed = 1.0) =>
  request<ScenarioStartResponse>(
    `/api/demo/scenarios/${encodeURIComponent(scenarioId)}/start?speed=${speed}`,
    { method: 'POST' },
  );


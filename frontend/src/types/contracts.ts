/**
 * TypeScript definitions mirroring backend frozen Pydantic contracts (§6, §8).
 *
 * Nullability here is load-bearing, not incidental. `P_spoof`, `p`, `q_call`
 * and friends are `number | null` because the backend uses null to mean "no
 * evidence", which is a different statement from zero. Widening any of these
 * to `number` would let a component render 0.00 for a call the system has said
 * nothing about.
 */

export type ExpertStatus = 'OK' | 'ABSTAIN' | 'DEFERRED' | 'MODEL_UNAVAILABLE' | 'TIMEOUT' | 'ERROR';

export type DecisionBand = 'GENUINE' | 'UNCERTAIN' | 'SUSPICIOUS' | 'SYNTHETIC_HIGH_CONFIDENCE';

export type RiskBand = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL' | 'UNCERTAIN';

export type PolicyAction = 'ALLOW' | 'WARN' | 'STEP_UP' | 'HOLD' | 'ESCALATE' | 'ACTIVE_LIVENESS';

export type RiskState =
  | 'UNKNOWN' | 'MONITORING' | 'TRUSTED' | 'VERIFY'
  | 'HIGH_RISK' | 'HOLD' | 'ESCALATE' | 'REVIEWED';

export type TransactionTier = 0 | 1 | 2 | 3 | 4;

export type ClockType = 'FAST' | 'SLOW';

/**
 * The backend has NOT fitted a calibration, so the score orders calls by
 * concern rather than estimating a probability. The UI keys off this to refuse
 * percentage formatting.
 */
export type ScoreSemantics = 'UNCALIBRATED_RISK_SCORE' | 'CALIBRATED_PROBABILITY';

export type SessionLifecycleState =
  | 'CREATED' | 'RUNNING' | 'DEGRADED' | 'STOPPING'
  | 'STOPPED' | 'FAILED' | 'INTERRUPTED';

export type TransactionStateValue = 'PENDING' | 'APPROVED' | 'HELD' | 'REJECTED' | 'CANCELLED';

export type BeneficiaryNovelty = 'NEW' | 'KNOWN' | 'UNKNOWN';

export type TimelineSeverity = 'INFO' | 'NOTICE' | 'WARNING' | 'CRITICAL';

export type TimelineEventKind =
  | 'SESSION_STARTED' | 'SESSION_STOPPED' | 'SESSION_FAILED'
  | 'ANALYSIS_STARTED' | 'BAND_CHANGED' | 'ACTION_CHANGED'
  | 'LANGUAGE_DETECTED' | 'LANGUAGE_SWITCH' | 'QUALITY_DEGRADED'
  | 'MODEL_UNAVAILABLE' | 'ANALYSIS_DEGRADED'
  | 'CONTEXT_INGESTED' | 'TRANSACTION_LINKED'
  | 'TRANSACTION_HELD' | 'TRANSACTION_RELEASED';

// --- health -------------------------------------------------------------------

export interface DependencyStatus {
  status: 'OK' | 'DEGRADED' | 'UNAVAILABLE' | 'NOT_INSTALLED';
  details: Record<string, unknown>;
}

export interface HealthResponse {
  status: 'healthy' | 'degraded';
  app: string;
  version: string;
  role: string;
  environment: string;
  timestamp: string;
  dependencies: Record<string, DependencyStatus>;
  expert_models: Record<string, { status: string; version?: string; reason?: string }>;
}

// --- errors -------------------------------------------------------------------

export interface ErrorDetail {
  code: string;
  message: string;
  session_id: string | null;
  correlation_id: string;
  retriable: boolean;
}

export interface ErrorEnvelope {
  error: ErrorDetail;
}

// --- risk ---------------------------------------------------------------------

export interface RiskContribution {
  factor: string;
  weight: number;
  direction: 'INCREASES_RISK' | 'DECREASES_RISK';
  points: number;
  detail: string | null;
}

export interface EvidenceReference {
  kind: string;
  ref: string;
  detail: string | null;
}

export interface RiskAssessment {
  session_id: string;
  risk_score: number;
  risk_confidence: number;
  risk_band: RiskBand;
  contributions: RiskContribution[];
  context_degraded: boolean;
  score_semantics: ScoreSemantics;
  score_label: string;
  timestamp: string;
}

export interface RiskDecision {
  session_id: string;
  risk: RiskAssessment;
  action: PolicyAction;
  matched_policy: string;
  transaction_tier: TransactionTier;
  reason_codes: string[];
  top_factors: RiskContribution[];
  evidence_refs: EvidenceReference[];
  recommended_verifications: string[];
  fail_safe_engaged: boolean;
  policy_version: string;
  timestamp: string;
}

// --- belief -------------------------------------------------------------------

export interface TrajectoryPoint {
  t: number;
  /** Null where the experts produced nothing for that window. */
  p_spoof: number | null;
  confidence: number;
}

export interface ExpertContribution {
  expert_id: string;
  weight: number;
  raw_p: number | null;
  calibrated_p: number | null;
}

export interface VoiceBelief {
  session_id: string;
  /** Null means no usable acoustic evidence. Never render as 0. */
  P_spoof: number | null;
  confidence: number;
  band: DecisionBand;
  q_call: number | null;
  spans: string[];
  trajectory: TrajectoryPoint[];
  contributing_experts: ExpertContribution[];
  uncertainty_reason: string | null;
  switch_damping_events: string[];
  model_versions: string[];
  clock: ClockType;
  timestamp: string;
}

// --- sessions -----------------------------------------------------------------

export interface SessionResponse {
  session_id: string;
  state: string;
}

export interface SessionDetailResponse {
  session_id: string;
  state: SessionLifecycleState;
  source_type: string;
  scenario_id: string | null;
  caller_ref: string | null;
  frames_published: number;
  frames_dropped: number;
  frames_scored: number;
  frames_skipped: number;
  has_assessment: boolean;
  created_at: string;
  started_at: string | null;
  stopped_at: string | null;
  served_at: string;
}

export interface SessionLifecycleResponse {
  session_id: string;
  state: SessionLifecycleState;
  frames_published: number | null;
  served_at: string;
}

export interface SessionRiskResponse {
  session_id: string;
  session_state: SessionLifecycleState;
  decision: RiskDecision;
  belief: VoiceBelief | null;
  explanation: string;
  clock: ClockType;
  analysis_degraded: boolean;
  degradation_reasons: string[];
  frames_seen: number;
  frames_scored: number;
  frames_skipped: number;
  computed_at: string;
  served_at: string;
}

export interface ExpertEvidenceView {
  expert_id: string;
  status: ExpertStatus;
  /** Null unless status is OK. */
  p: number | null;
  confidence: number | null;
  latency_ms: number;
}

export interface SessionEvidenceResponse {
  session_id: string;
  /** Always LIVE_ANALYSIS_SUMMARY: this is not a hash-chained audit record. */
  record_type: string;
  hash_chained: boolean;
  chain_status: string;
  experts: ExpertEvidenceView[];
  model_versions: string[];
  belief_trajectory: TrajectoryPoint[];
  top_factors: RiskContribution[];
  evidence_refs: EvidenceReference[];
  audio_quality: number | null;
  frames_seen: number;
  frames_scored: number;
  served_at: string;
}

// --- timeline -----------------------------------------------------------------

export interface TimelineEntry {
  seq: number;
  session_id: string;
  kind: TimelineEventKind;
  severity: TimelineSeverity;
  label: string;
  detail: string | null;
  t_offset_s: number | null;
  risk_band: RiskBand | null;
  action: PolicyAction | null;
  reason_codes: string[];
  evidence_refs: EvidenceReference[];
  transaction_id: string | null;
  timestamp: string;
}

export interface TimelineResponse {
  session_id: string;
  entries: TimelineEntry[];
  truncated: boolean;
  served_at: string;
}

// --- context ------------------------------------------------------------------

export interface ContextVector {
  session_id: string;
  identity: Record<string, unknown>;
  number: Record<string, unknown>;
  transaction: Record<string, unknown>;
  behaviour: Record<string, unknown>;
  technical: Record<string, unknown>;
  history: Record<string, unknown>;
  language: string;
  provenance: Record<string, string>;
  timestamp: string;
}

export interface ContextIngestResponse {
  session_id: string;
  context: ContextVector;
  accepted_at: string;
}

// --- demo transactions --------------------------------------------------------

export interface DemoTransaction {
  transaction_id: string;
  environment: string;
  disclaimer: string;
  caller_identity: string;
  /**
   * Serialised from a Decimal, so it arrives as a STRING. Format it directly;
   * parseFloat would risk precision on large amounts for no benefit.
   */
  amount: string;
  currency: string;
  beneficiary: string;
  beneficiary_novelty: BeneficiaryNovelty;
  transaction_type: string | null;
  state: TransactionStateValue;
  session_id: string | null;
  hold_reason: string | null;
  verification_reference: string | null;
  risk_actions: PolicyAction[];
  created_at: string;
  updated_at: string;
}

export interface TransactionResponse {
  environment: string;
  disclaimer: string;
  transaction: DemoTransaction;
}

export interface TransactionListResponse {
  environment: string;
  disclaimer: string;
  transactions: DemoTransaction[];
}

// --- replay -------------------------------------------------------------------

export type ReplayFixture =
  | 'case_01_authentic_human'
  | 'case_02_cloned_synthetic'
  | 'case_03_adversarial_manipulated'
  | 'clean_speechlike'
  | 'noisy_speechlike'
  | 'narrowband_speechlike'
  | 'silence'
  | 'tone_440';

export interface ReplayResponse {
  session_id: string;
  state: SessionLifecycleState;
  fixture: ReplayFixture;
  environment: string;
  served_at: string;
}

// --- Canonical Evidence-Based Forensic Result Contracts ------------------------

export interface OverallRisk {
  risk_score: number;
  risk_band: RiskBand;
  severity_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL' | 'UNCERTAIN';
  summary: string;
}

export interface DecisionVerdict {
  verdict: PolicyAction;
  matched_rule: string;
  requires_step_up: boolean;
  requires_hold: boolean;
  action_narrative: string;
}

export interface ConfidenceScore {
  score: number;
  uncertainty_level: string;
  confidence_interval: [number, number];
  shrinkage_applied: number;
}

export interface DetectorScoreItem {
  detector_id: string;
  detector_name: string;
  detector_type: string;
  model_version: string;
  p_synthetic: number;
  confidence: number;
  status: 'OK' | 'DEFERRED' | 'ERROR';
  latency_ms: number;
  weight_in_fusion: number;
}

export interface EvidenceItem {
  signal: string;
  category: 'NEURAL_ACOUSTIC' | 'PHYSICAL_DSP' | 'SPEAKER_BIOMETRICS' | 'SIGNAL_QUALITY' | 'TRANSACTION_CONTEXT';
  score: number;
  severity: 'INFO' | 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  explanation: string;
}

export interface ProcessingLatency {
  total_ms: number;
  validation_ms: number;
  preprocessing_ms: number;
  feature_extraction_ms: number;
  detector_breakdown_ms: Record<string, number>;
  fusion_and_calibration_ms: number;
}

export interface AudioMetadata {
  duration_s: number;
  active_speech_duration_s: number;
  sample_rate_hz: number;
  channels: number;
  snr_db: number;
  voiced_ratio: number;
  clipping_detected: boolean;
  peak_amplitude_dbfs: number;
}

export interface CanonicalInferenceResponse {
  session_id: string;
  timestamp: string;
  is_valid_audio: boolean;
  overall_risk: OverallRisk;
  decision: DecisionVerdict;
  confidence: ConfidenceScore;
  detector_scores: DetectorScoreItem[];
  evidence_items: EvidenceItem[];
  processing_latency: ProcessingLatency;
  model_versions: Record<string, string>;
  audio_metadata: AudioMetadata;
  verdict: PolicyAction;
  risk_band: RiskBand;
  calibrated_p_synthetic: number;
  execution_time_ms: number;
}

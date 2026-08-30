# IMPLEMENTATION READINESS REPORT

**Project:** SYMPHONY / VoiceShield — Real-Time Voice Integrity & Impersonation Defense
**Problem Statement:** SIH **26104** — AI-Powered Real-Time Detection and Prevention of Voice Cloning Impersonation Attacks
**Organization:** All India Council for Technical Education (AICTE) · Cyber Security Cell
**Phase:** Pre-implementation audit. **No application code exists and none is written by this document.**

---

## §0 — Provenance and honesty statement

### 0.1 What was actually read

| Document | Status | Size | Role |
|---|---|---|---|
| `PS.txt` | **Present** | 47 lines | Official problem statement — authoritative for *what the problem is*. |
| `SYMPHONY_REFERENCE.md` | **Present** | 2044 lines | Master architecture — authoritative for *how it is to be built*. |
| `DEMO_SCOPE.md` | **ABSENT** | — | Named as an authoritative source; does not exist in the workspace. |
| `ARCHITECTURE.md` | **ABSENT** | — | Same. |
| `TECH_STACK.md` | **ABSENT** | — | Same. |
| `DEMO_SCENARIOS.md` | **ABSENT** | — | Same. |
| `VoiceShield_Agent_Build_Prompts.md` | **ABSENT** | — | Referenced by `SYMPHONY_REFERENCE.md` §41 as the companion build-prompt document. |

The workspace contains **exactly two files**. There is no `backend/`, `frontend/`, `models/`, `tests/`, `demo/`, `scripts/`, `docker-compose.yml`, `.env.example`, `.gitignore`, or `README.md`. The directory is **not a git repository**.

### 0.2 Ruling on the four absent documents

`SYMPHONY_REFERENCE.md` is treated as the **single authoritative source**. This is defensible rather than convenient: the reference document already contains, internally, the material the four absent files would have carried —

- architecture → Part A, §1–23
- technology stack → §15, §31, §31.1
- demo scope → §25–29, §39
- demo scenarios → §35, §36

The four absent files are recorded here as **missing artifacts to be generated later** (see §14). **No requirement has been invented to fill them.** Where their absence leaves a real gap, it is recorded in §10 as an ambiguity, not resolved silently.

### 0.3 Honesty constraints binding this document

This report makes **no claim** of:

- any ML accuracy, EER, AUC, or benchmark figure — **none exists**, none is quoted;
- any dataset by name as "in use" — **no dataset is present in the workspace**;
- any trained model or checkpoint being available — **no model weights are present**;
- any real-time telecom integration — **none exists and none is planned for this demo**;
- any banking or core-banking integration — **none exists and none is planned for this demo**;
- any library version — `SYMPHONY_REFERENCE.md` §31.1 explicitly forbids inventing versions, and nothing in this environment pins them.

This mirrors the frozen architectural contract at §22:

> **No score may be fabricated to make the demo work.**

### 0.4 Findings about the source files themselves

1. **`PS.md` does not exist; the file is `PS.txt`.** The task brief named `PS.md`. The content is correct and complete; only the extension differs. Recorded as an ambiguity (§10.6), not corrected here.
2. **`PS.txt` contains character-encoding corruption.** Sequences such as `â€"` (lines 6, 10, 40) are mojibake from a UTF-8 / Windows-1252 round-trip, where an em-dash was intended. The file is **not modified by this report** — the corruption is reported, not fixed. It should be repaired before the text is quoted in any judge-facing material.
3. **`SYMPHONY_REFERENCE.md` §35.2 leaves Scenario 3 formally undecided.** The document itself says *"Both are valid third scenarios; pick one as the built default and keep the other as the stretch target."* This has now been decided (§10.9).

---

## §1 — Terminology lock

The following vocabulary is **frozen**. `SYMPHONY_REFERENCE.md` §22 states that no developer or AI agent may modify phase boundaries, cross-phase contracts, model roles, or decision semantics without first amending the architecture specification. Renaming any term below constitutes such a modification.

### 1.1 The five phases

| Phase | Name | Codename | Produces |
|---|---|---|---|
| **I** | INTAKE | "Listen" | `FrameObject` |
| **II** | ANALYSIS | "Score" | `EvidenceVector` |
| **III** | FUSION | "Harmony" | `VoiceBelief` |
| **IV** | DECISION | "Conductor" | `Decision` |
| **V** | ASSURANCE | "Coda" | `EvidenceRecord` |

### 1.2 The six experts

| ID | Name | The question it answers |
|---|---|---|
| **E1** | Spectro-temporal | Are spectral/synthesis artefacts present? |
| **E2** | Raw waveform | Are waveform-level anomalies present? |
| **E3** | SSL | Does a multilingual learned representation indicate spoofing? |
| **E4** | Speaker | Does this sound like the claimed/enrolled speaker? |
| **E5** | Prosody / behaviour | Is natural conversational behaviour inconsistent? |
| **E6** | Replay / liveness | Is this potentially replayed audio rather than generated speech? |

**Locked rule (§6.1):** the experts **do not consume each other's outputs**. Violating this turns six named experts into one ensemble wearing six labels, and destroys the evidence independence that Phase III's weighting depends on.

### 1.3 The five frozen contracts

```text
FrameObject → EvidenceVector → VoiceBelief → Decision → EvidenceRecord
```

### 1.4 Frozen enumerations

- **VoiceBelief bands** (§8.6): `GENUINE` · `UNCERTAIN` · `SUSPICIOUS` · `SYNTHETIC_HIGH_CONFIDENCE`
- **Action classes** (§9.4): `ALLOW` · `WARN` · `STEP_UP` · `HOLD` · `ESCALATE` · `ACTIVE_LIVENESS`
- **Risk states** (§9.4): `UNKNOWN` → `MONITORING` → { `TRUSTED` | `VERIFY` | `HIGH_RISK` } ; `HIGH_RISK` → { `HOLD` | `ESCALATE` } ; `HOLD` → `REVIEWED`
- **Transaction sensitivity tiers** (§9.2): `0` Informational · `1` Account information · `2` Credential/security action · `3` Financial transaction · `4` Privileged authorisation
- **Abstention values** (§22): `MODEL_UNAVAILABLE` · `UNCERTAIN` · `E4 = ABSTAIN` · `codec = UNKNOWN`

### 1.5 Terminology conflicts present in the source

These are **inconsistencies already inside `SYMPHONY_REFERENCE.md`**. They are surfaced, not resolved by fiat. Recommendations appear in §10.

| # | Conflict | Locations |
|---|---|---|
| T1 | Product named **VoiceShield** vs. header text **VOICEGUARD** | §24, §30.1, §32.1 say VoiceShield; §32 header line says VOICEGUARD |
| T2 | UI risk bands `LOW / MEDIUM / HIGH / CRITICAL` vs. VoiceBelief bands `GENUINE / UNCERTAIN / SUSPICIOUS / SYNTHETIC_HIGH_CONFIDENCE` | §26.1, §32, §35 use the former; §8.6 freezes the latter |
| T3 | Two different repository trees | §30 and §30.1 |

---

## §2 — Requirement classification

Every requirement drawn from `PS.txt` and `SYMPHONY_REFERENCE.md`, sorted into four buckets. Source sections are cited so each entry can be checked against the original.

---

### A — REQUIRED FOR THIS INTERNAL DEMO

These constitute the vertical slice. `SYMPHONY_REFERENCE.md` §24 states the governing principle:

> **Build the smallest system that demonstrates the complete security story end-to-end, rather than the largest system that demonstrates isolated technical components.**

| ID | Requirement | Source | Must be real? |
|---|---|---|---|
| A1 | Audio ingestion from WAV file and microphone | §25, §26.1, §29 | **Real** |
| A2 | Chunking, timestamping, buffering, resampling, PCM normalisation | §4.1, §26.1 L1–L2 | **Real** |
| A3 | Voice activity detection (VAD) | §4.1, §26.1 L1 | **Real** |
| A4 | Audio quality estimation (`q_t`) | §4.1, §26.1 L1 | **Real** |
| A5 | `FrameObject` contract, fully populated or explicitly abstaining | §5 | **Real** |
| A6 | Redis Streams as the Phase I → Phase II decoupling buffer | P3, §3, §23 | **Real** |
| A7 | Spectrogram / log-mel / MFCC feature extraction | §26.1 L2 | **Real** |
| A8 | Prosodic feature computation — F0, energy, pause distribution, speaking rate | §6.2 E5, §26.1 L2 | **Real** (as features; scoring is deferred — see B1) |
| A9 | **E1** spectro-temporal anti-spoof inference | §6.2, §25 | **Real** |
| A10 | **E2** raw-waveform anti-spoof inference | §6.2, §25 | **Real** |
| A11 | **E3** SSL backbone + lightweight probe | §6.2, §25 | **Real** |
| A12 | **E4** speaker embedding + cosine similarity against a reference | §6.2, §25 | **Real** |
| A13 | `EvidenceVector` contract | §7 | **Real** |
| A14 | Quality-conditioned expert weighting (`weight_i = f(q_t, codec_vec, reliability)`) | §8.1 | **Real** |
| A15 | Score calibration layer | §8, §15 | **Real** |
| A16 | Bayesian log-odds temporal accumulation with evidence decay | §8.2 | **Real** |
| A17 | Two-clock architecture — fast 100–250 ms, slow 1–3 s rolling window | §8.3 | **Real** |
| A18 | Uncertainty estimation and `uncertainty_reason` | §8, §8.6 | **Real** |
| A19 | `VoiceBelief` contract including `trajectory[]` and `contributing_experts[]` | §8.6 | **Real** |
| A20 | Context vector — identity, number, transaction, behaviour, technical | §9.1 | **Real structure, simulated values** (see §12) |
| A21 | Five transaction sensitivity tiers, with thresholds tightening as tier rises | §9.2 | **Real** |
| A22 | Explicit policy layer that overrides / gates any ML risk output | §9.3 | **Real** |
| A23 | Risk state machine | §9.4 | **Real** |
| A24 | Action classes emitted as decisions | §9.4 | **Real** (emission is real; downstream execution is simulated) |
| A25 | Explanation service — contribution breakdown, attribution not causal proof | §10.1 | **Real** |
| A26 | `EvidenceRecord` with `previous_hash` / `record_hash` hash chain | §10.2 | **Real** |
| A27 | Privacy lifecycle — raw audio in short-lived buffer, feature/event persistence only | §10.3, §34 | **Real** |
| A28 | REST API — sessions, evidence, timeline, risk, context, actions | §12 | **Real** |
| A29 | WebSocket — live audio in, live security events out | §12 | **Real** |
| A30 | SQLite persistence (Profile A) | §14, §18, §31 | **Real** |
| A31 | React + TypeScript + Vite + Tailwind + shadcn/ui + Recharts dashboard, seven panels | §31, §32.1 | **Real** |
| A32 | **All displayed values sourced from backend state over WebSocket; no hardcoded demo values** | §32.1 | **Real — non-negotiable** |
| A33 | Demo scenario engine: selects audio fixture, context, transaction context, starts session — **and nothing else** | §36 | **Real** |
| A34 | `DEMO MODE` disclosure banner visible in the UI | §36 | **Real** |
| A35 | Scenario 1 — genuine CFO call → `LOW` → `ALLOW` | §35.2 | **Real pipeline** |
| A36 | Scenario 2 — full voice clone → `HIGH`/`CRITICAL` → `HOLD` + `ESCALATE` | §35.2 | **Real pipeline** |
| A37 | Scenario 3 — **poor-quality audio → `UNCERTAIN` → `STEP_UP`** *(decided; see §10.9)* | §35.2, §36 | **Real pipeline** |
| A38 | Graceful abstention semantics throughout | §22 | **Real — non-negotiable** |
| A39 | Playwright end-to-end demo verification run | §37 | **Real** |
| A40 | pytest unit/integration coverage of contracts and phase boundaries | §15, §31 | **Real** |
| A41 | Transaction simulator UI panel showing `ON HOLD` state change | §26, §27, §32.1 | **Real UI, simulated backend system** |
| A42 | Docker Compose packaging (Profile A, single machine) | §18, §31 | **Real** |

---

### B — REQUIRED BY THE ORIGINAL PROBLEM STATEMENT BUT DEFERRED

Each item below is genuinely demanded by `PS.txt`. Each is deliberately **not** built for the internal round. Deferral must be **stated aloud** in any presentation; presenting these as working would be a fabrication.

| ID | Requirement | PS basis | Why deferred |
|---|---|---|---|
| B1 | **E5** prosody as a *scored expert* contributing `p_beh` | PS "Prosody and behavioral analysis" | §25's internal slice shows only E1/E2, E3, E4. Features (A8) may be computed and displayed; the calibrated score is deferred. §6.2 already calls E5 *"a weak supporting expert, never proof of human speech."* |
| B2 | **E6** replay / liveness as a scored expert `p_rep` | PS implies replay coverage | Omitted from §25's slice. Distinct attack class needing its own data. |
| B3 | Partial-spoof localisation and the synthetic-span UI | PS "granular analysis" | §8.4 flagship capability, but §35.2 makes it the stretch target. §8.4 also warns: *"Do not claim a particular localisation resolution until measured."* |
| B4 | Code-switch stability guard with damping event logging | PS "multilingual contexts", "code switching" | §8.5. Requires reliable language tagging and measurement data that does not exist yet. |
| B5 | Validated Hindi / Marathi / Indian-English coverage | PS "diverse Indian accents and dialects" | No fixtures exist. §33 explicitly forbids claiming *"we support every Indian language."* |
| B6 | Cross-session consistency vs. historical genuine samples | PS "Cross-session consistency checks" | Needs an enrollment corpus and a reference store. §21 lists this as production-grade. |
| B7 | SMS / email / push / in-app alert channels | PS "Multi-channel alert mechanisms" | §21. Only the in-UI alert is built. |
| B8 | gRPC interface | PS "REST/gRPC APIs" | §20 assigns gRPC to *"internal/enterprise integration where required."* |
| B9 | Published SDK (`VoiceShieldClient`) | PS "SDKs" | §13 defines the shape; not built for the internal round. |
| B10 | XGBoost contextual risk model | §9.3, §15 | The explicit policy layer (A22) is the demo path. §9.3 requires the model *"must not have the final say"* regardless. |
| B11 | OAuth2 / OIDC / JWT / RBAC | §11, PS enterprise integration | §21 maps internal round to "local auth". |
| B12 | PostgreSQL | §14 | §14: *"For the internal prototype, SQLite can replace PostgreSQL … but the architecture must not be redesigned around SQLite."* |
| B13 | Edge / on-device inference option | PS "on-device or edge inference" | §21 maps it to a deployment profile. |
| B14 | MLflow / DVC model and dataset lifecycle | §10.4, §15 | §21: internal round is "manual". |
| B15 | Prometheus / Grafana / OpenTelemetry | §15 | §21: internal round is "basic metrics". |
| B16 | Drift detection, human feedback loop, retraining | §10.4, PS Phase V | Requires production traffic. |
| B17 | Speaker-/generator-/channel-/language-disjoint evaluation | §10.5 | §10.5: *"Do not randomly split audio and call that evaluation."* No dataset exists yet, so no evaluation is claimed. |
| B18 | Signed model artifacts and checksum verification | §11 | Requires a model registry. |
| B19 | Active liveness challenge (dynamic/semantic) | §9.5 | Fallback capability; §9.5 warns against challenging every call. |

---

### C — OPTIONAL FUTURE / PRODUCTION CAPABILITY

Not demanded explicitly by `PS.txt`; introduced by the production architecture as the scaling path. Neither built nor promised.

| ID | Capability | Source |
|---|---|---|
| C1 | Kubernetes orchestration | §15, §18 Profile C — *"a deployment target, not a prerequisite for the SIH prototype"* |
| C2 | Redis cluster / HA | §18, §21 |
| C3 | PostgreSQL HA | §18, §21 |
| C4 | GPU inference pool | §18, §21 |
| C5 | SIEM integration | §1, §18 |
| C6 | Model registry + canary deployment | §10.4, §18 |
| C7 | Immutable signed evidence export store | §14, §21 |
| C8 | Enterprise IAM | §18, §21 |
| C9 | Contact-centre and enterprise-collaboration adapters | §4.2, §18 |
| C10 | Object storage for model artefacts and datasets | §14 |
| C11 | Generator-control experiment framework | §10.6 |
| C12 | Loki / OpenSearch-class log aggregation | §14 |
| C13 | Load balancer + API gateway topology | §17 |

---

### D — EXPLICITLY OUT OF SCOPE FOR THIS DEMO

Taken **verbatim** from `SYMPHONY_REFERENCE.md` §16 ("What I would NOT add") and §39 ("What NOT to build for the internal round"). Nothing has been added to this list.

**From §16 — frozen out unless a genuine requirement appears:**
Kafka · RabbitMQ · Celery · Spark · Kubernetes for internal demo · GraphQL · MongoDB · Elasticsearch as primary database · microservices for every class · mobile application · custom telecom hardware · custom FPGA/DSP hardware · **LLM in the core detection path** · blockchain

> §16, emphatic: *"In particular: no LLM for voice authenticity."* An LLM may assist with explanation phrasing or analyst summaries only; the core anti-spoof decision must remain an audio ML/DSP pipeline.

**From §39 — do not spend the internal-round week building:**
Android + iOS apps · **real telecom carrier integration** · **complete banking integration** · Kubernetes · microservices everywhere · distributed GPU inference · full SIEM integration · 15-language support · **custom deepfake model from scratch** · production-grade authentication infrastructure · **actual financial transaction execution** · elaborate admin panels

**Consequence to state plainly to any audience:** this demo does **not** connect to a telecom network, does **not** connect to a bank, does **not** move money, and does **not** ship a trained-from-scratch model.

---

## §3 — Architecture

### 3.1 What the product is

Per §1, the executive architectural decision: **the final product is not a mobile application.** It is an **AI voice-security platform** sitting between a communication/audio source and the systems or people that must act on the result. The detector is an **infrastructure/security layer, not a handset app.**

### 3.2 The five-phase layer

```text
AUDIO SOURCE
     │
     ▼
┌────────────────────────────────────────────┐
│  I   INTAKE     → condition the signal     │
│  II  ANALYSIS   → independent experts      │
│  III FUSION     → evidence → voice belief  │
│  IV  DECISION   → voice + context → action │
│  V   ASSURANCE  → explain + evidence       │
└────────────────────────────────────────────┘
     │
     ▼
SECURITY OUTPUT PLANE
```

### 3.3 The five locked principles and their demo consequence

| # | Principle | Consequence for implementation |
|---|---|---|
| **P1** | **Audio source independence** — all sources terminate in the same canonical ingestion contract | The WAV/mic adapter and a future SIP/RTP adapter must be interchangeable behind `FrameObject`. No downstream module may import an audio-source library. |
| **P2** | **Phase isolation** — *"a phase may only consume fields declared by its input object; if a downstream phase wants raw audio, the architecture has leaked"* | Phase III onward must never touch PCM. This is testable and **must be tested**. |
| **P3** | **Capture never waits for ML** | Redis Streams is mandatory as the decoupling mechanism, not optional convenience. See §10.7. |
| **P4** | **Probability ≠ confidence** — *"Low confidence means 'we don't know', not 'probably genuine'"* | `P_spoof` and `confidence` must be separate fields and separately rendered. Scenario 3 (A37) exists specifically to demonstrate this. |
| **P5** | **Protect actions, not recordings** — the question is not *"Is this WAV fake?"* but *"Given the voice evidence and the requested action, should this action be trusted?"* | Phase IV must be a separate module from Phase III. This is the distinction between a deepfake detector and a fraud-prevention system. |

### 3.4 Deployment profiles

| Profile | Target | Composition |
|---|---|---|
| **A — Internal SIH** *(this build)* | One machine | React · FastAPI · Redis · SQLite · PyTorch · local model files · WebSocket · Docker Compose |
| **B — Pilot** | Deferred | + PostgreSQL · GPU inference worker · object storage · Prometheus · Grafana |
| **C — Enterprise** | Deferred | + Kubernetes · Redis cluster · PostgreSQL HA · GPU pool · model registry · IAM · SIEM |

§18: **the logical architecture does not change between profiles.**

---

## §4 — Component inventory

Structure follows §30.1 (see §10.8 on the §30 vs §30.1 conflict).

| Component | Phase | Responsibility | Real / Simulated | Cat. |
|---|---|---|---|---|
| `ingestion/audio_stream` | I | WAV + microphone source adapters, streaming | Real | A |
| `ingestion/buffering` | I | Jitter buffer, chunking, timestamping | Real | A |
| `ingestion/vad` | I | Speech/non-speech segmentation | Real | A |
| `ingestion/quality` | I | `q_t` estimation, clipping/noise/bandwidth | Real | A |
| `ingestion/channel_profiler` | I | `codec_vec`, bandwidth, packet loss | Real (values largely `UNKNOWN` for WAV input) | A |
| `ingestion/session` | I | Session creation and lifecycle | Real | A |
| *(SIP/RTP adapter)* | I | Telephony ingress | **Not built** | D |
| *(WebRTC adapter)* | I | VoIP ingress | **Not built** | D |
| `signal_processing/preprocessing` | I→II | Resampling, normalisation | Real | A |
| `signal_processing/spectrogram` | II | Log-mel / LFCC | Real | A |
| `signal_processing/mfcc` | II | MFCC | Real | A |
| `signal_processing/prosody` | II | F0, energy, pauses, speaking rate | Real (features) | A / B1 |
| `models/spoof_detector` (E1) | II | Spectro-temporal anti-spoof | Real inference, **acquired weights** | A |
| `models/spoof_detector` (E2) | II | Raw-waveform anti-spoof | Real inference, **acquired weights** | A |
| `models/ssl_probe` (E3) | II | Frozen SSL backbone + probe | Real inference, **acquired weights** | A |
| `models/speaker_verifier` (E4) | II | Speaker embedding + cosine | Real inference, **acquired weights** | A |
| `models/prosody_model` (E5) | II | Behavioural scoring | **Deferred** | B1 |
| `models/replay_detector` (E6) | II | Replay/liveness scoring | **Deferred** | B2 |
| `models/fusion/weighting` | III | Quality-conditioned weights | Real (**priors**, not measured) | A |
| `models/fusion/calibration` | III | Score calibration | Real | A |
| `models/fusion/belief` | III | Log-odds accumulation + decay | Real | A |
| `models/fusion/clocks` | III | Fast/slow two-clock scheduler | Real | A |
| `models/fusion/uncertainty` | III | Confidence + `uncertainty_reason` | Real | A |
| `models/fusion/localisation` | III | Partial-spoof spans | **Deferred (stretch)** | B3 |
| `models/fusion/codeswitch_guard` | III | Damping + event logging | **Deferred** | B4 |
| `context/caller` | IV | Claimed/verified identity, enrollment, CNAP | **Simulated adapter** | A20 |
| `context/reputation` | IV | Number reputation, age, port history | **Simulated adapter** | A20 |
| `context/transaction` | IV | Amount, type, beneficiary novelty, velocity | **Simulated adapter** | A20 |
| `context/behaviour` | IV | Urgency, secrecy, callback refusal | **Simulated / scenario-supplied** | A20 |
| `decision/risk_engine` | IV | Voice + context risk fusion | Real | A |
| `decision/thresholds` | IV | Tier-conditioned thresholds | Real | A |
| `decision/policy` | IV | Explicit rule layer with final say | Real | A |
| `decision/state_machine` | IV | Risk state transitions | Real | A |
| `decision/actions` | IV | Action emission | Real emission, **simulated execution** | A24 |
| `evidence/explanation` | V | Contribution breakdown | Real | A |
| `evidence/record` | V | `EvidenceRecord` + hash chain | Real | A |
| `evidence/privacy` | V | Buffer expiry, feature-only logging | Real | A |
| `evidence/feedback` | V | Analyst feedback loop | **Deferred** | B16 |
| `evidence/drift` | V | Drift detection | **Deferred** | B16 |
| `api/` | — | FastAPI REST surface | Real | A |
| `websocket/` | — | Audio in / events out | Real | A |
| `demo/simulator` | — | Fixture + context selection **only** | Real | A33 |
| `demo/scenarios` | — | Three frozen scenario definitions | Real | A35–A37 |
| `demo/audio` | — | Curated fixtures | **To be acquired** | §7 |
| `frontend/` | — | Seven-panel security console | Real | A31 |
| `tests/` | — | pytest + Playwright | Real | A39, A40 |

---

## §5 — Interfaces and data contracts

### 5.1 `FrameObject` — frozen (§5)

```text
FrameObject
{
    session_id
    frame_id

    pcm[]
    sample_rate

    t_start
    t_end

    codec_vec
    bandwidth
    packet_loss

    q_t

    is_speech
    speaker_turn
    overlap_flag

    lang_t
    switch_flag

    source_type

    created_at
}
```

§5: *"No downstream component should directly depend on SIP, WebRTC, microphone APIs, etc."*

**Demo note:** for WAV/mic input, `codec_vec` and `packet_loss` will frequently be unknown. Per §22 they must be emitted as `codec = UNKNOWN`, **never as invented values**.

### 5.2 `EvidenceVector` — frozen (§7)

```text
EvidenceVector
{
    session_id
    frame_id

    p_spec          # E1
    p_raw           # E2
    p_ssl           # E3
    p_spk           # E4
    p_beh           # E5  → ABSTAIN in this demo (B1)
    p_rep           # E6  → ABSTAIN in this demo (B2)

    frame_logits[]
    expert_confidences[]

    q_t
    codec_vec

    lang_t
    switch_flag

    inference_latency_ms

    model_versions[]

    timestamp
}
```

**Critical:** deferring E5/E6 does **not** mean removing `p_beh` / `p_rep` from the contract. The fields remain and carry an explicit abstention value. Removing them would be an unauthorised contract change under §22.

### 5.3 `VoiceBelief` — frozen (§8.6)

```text
VoiceBelief
{
    session_id

    P_spoof
    confidence

    band                       # GENUINE | UNCERTAIN | SUSPICIOUS | SYNTHETIC_HIGH_CONFIDENCE

    q_call

    spans[]                    # empty in this demo (B3)

    trajectory[]

    contributing_experts[]

    uncertainty_reason

    switch_damping_events[]    # empty in this demo (B4)

    model_versions[]

    timestamp
}
```

§8.6: *"Do not force fake / real when the evidence does not justify it."*

### 5.4 `ContextVector` — **DESCRIBED BUT NEVER FROZEN**

§9.1 enumerates the dimensions but never presents a named schema block, unlike the other four contracts. Fields as described:

```text
Identity     : claimed_identity · verified_identity · enrollment_status · cnap_state · identity_mismatch
Number       : reputation · age · known_fraud_status · port_history
Transaction  : amount · transaction_type · beneficiary_novelty · velocity · historical_deviation
Behaviour    : urgency · secrecy · callback_refusal · verification_bypass · unusual_request
Technical    : device_signal · network_origin · voip_mobile_indicator · codec
```

**This must be formally frozen before Phase IV is implemented.** Recorded as ambiguity §10.3.

### 5.5 `Decision` — **DESCRIBED BUT NEVER FROZEN**

§9 describes the flow (`VoiceBelief + ContextVector → Risk Fusion → Transaction Sensitivity → Policy Engine → State Machine → Action`) and §10.2 shows the fields that reach `EvidenceRecord`, but no standalone `Decision` schema block is given. Must be frozen alongside `ContextVector`.

### 5.6 `EvidenceRecord` — frozen (§10.2)

```text
EvidenceRecord
{
    record_id

    session_id
    call_id

    timestamp

    model_versions[]

    codec
    audio_quality

    expert_scores[]

    voice_belief

    context_features

    transaction_context

    risk

    confidence

    action

    policy_version

    reason_codes[]

    previous_hash
    record_hash
    signature
}
```

§10.2: signed, append-only, hash-chained. **Demo note:** `signature` requires a signing key. For Profile A a locally generated key is acceptable **provided the UI/report does not describe it as an enterprise-grade signed immutable store** (that is C7).

### 5.7 REST surface — frozen (§12)

```http
POST /v1/sessions
GET  /v1/sessions/{id}
POST /v1/sessions/{id}/start
POST /v1/sessions/{id}/stop

GET  /v1/sessions/{id}/evidence
GET  /v1/sessions/{id}/timeline
GET  /v1/sessions/{id}/risk

POST /v1/sessions/{id}/context

POST /v1/sessions/{id}/actions/verify
POST /v1/sessions/{id}/actions/hold
POST /v1/sessions/{id}/actions/escalate
```

§12: *"The external API should be deliberately small."*

### 5.8 WebSocket channels — frozen (§12)

```http
WS /v1/sessions/{id}/audio      # live audio in
WS /v1/sessions/{id}/events     # live security state out
```

**The individual event message types are never enumerated in the source.** §32.1 implies at minimum: risk update, evidence update, timeline event, transaction status change, action recommendation, language detection, privacy state. Recorded as ambiguity §10.4 — must be frozen before the frontend is built, since A32 forbids the UI inventing values.

### 5.9 SDK shape (§13, deferred — B9)

```text
VoiceShieldClient
 ├── start_session()
 ├── stream_audio()
 ├── get_risk()
 ├── get_evidence()
 ├── get_decision()
 └── subscribe_events()
```

§13: *"The SDK should never expose the internal ML implementation."*

---

## §6 — Dependencies and external software

§31.1 imposes an explicit obligation: for every dependency, specify purpose · version policy · installation method · mandatory? · GPU required? · internet required? · licensing · fallback. It also states: **"Do not invent package versions."**

Accordingly **every version below reads `REQUIRES VERIFICATION`.** Nothing in this workspace pins a version, and no manifest exists.

### 6.1 Backend

| Dependency | Purpose | Mandatory | GPU | Internet | Licence | Fallback | Version |
|---|---|---|---|---|---|---|---|
| Python | Runtime | Yes | No | Install only | PSF | None | REQUIRES VERIFICATION |
| FastAPI | REST + WS framework | Yes | No | Install only | MIT | None | REQUIRES VERIFICATION |
| Uvicorn | ASGI server | Yes | No | Install only | BSD | Hypercorn | REQUIRES VERIFICATION |
| Pydantic | Contract schemas | Yes | No | Install only | MIT | None — contracts depend on it | REQUIRES VERIFICATION |
| NumPy | DSP arrays | Yes | No | Install only | BSD | None | REQUIRES VERIFICATION |
| SciPy | DSP | Yes | No | Install only | BSD | None | REQUIRES VERIFICATION |
| librosa | Audio features | Yes | No | Install only | ISC | Hand-rolled mel via SciPy | REQUIRES VERIFICATION |
| soundfile | Audio I/O | Yes | No | Install only | BSD (libsndfile: LGPL) | `wave` stdlib for PCM WAV | REQUIRES VERIFICATION |
| PyTorch | Model inference | Yes | Optional | Install only (large) | BSD-style | None | REQUIRES VERIFICATION |
| SpeechBrain | ECAPA speaker encoder | Yes (E4) | Optional | **Yes, if weights fetched at runtime** | Apache-2.0 | Vendor weights locally | REQUIRES VERIFICATION |
| Hugging Face Transformers | SSL backbone loading (E3) | Yes (E3) | Optional | **Yes, if weights fetched at runtime** | Apache-2.0 | Vendor weights locally | REQUIRES VERIFICATION |
| redis (client) | Redis Streams | Yes (P3) | No | Install only | MIT | See §10.7 | REQUIRES VERIFICATION |
| scikit-learn | Calibration | Yes | No | Install only | BSD | Hand-rolled Platt/isotonic | REQUIRES VERIFICATION |
| XGBoost | Contextual risk model | **No — deferred B10** | No | Install only | Apache-2.0 | Explicit policy rules (A22) | REQUIRES VERIFICATION |
| pytest / pytest-asyncio | Testing | Yes | No | Install only | MIT | None | REQUIRES VERIFICATION |

### 6.2 Frontend

| Dependency | Purpose | Mandatory | Internet | Licence | Version |
|---|---|---|---|---|---|
| Node.js + npm | Build toolchain | Yes | Install only | MIT-ish | REQUIRES VERIFICATION |
| React | UI | Yes | Install only | MIT | REQUIRES VERIFICATION |
| TypeScript | Types | Yes | Install only | Apache-2.0 | REQUIRES VERIFICATION |
| Vite | Dev server / bundler | Yes | Install only | MIT | REQUIRES VERIFICATION |
| Tailwind CSS | Styling | Yes | Install only | MIT | REQUIRES VERIFICATION |
| shadcn/ui | Components | Yes | Install only | MIT | REQUIRES VERIFICATION |
| Recharts | Risk trajectory chart | Yes | Install only | MIT | REQUIRES VERIFICATION |
| Playwright | Demo verification | Yes | **Yes — downloads browsers** | Apache-2.0 | REQUIRES VERIFICATION |

### 6.3 System-level software

| Software | Purpose | Mandatory | Notes |
|---|---|---|---|
| **FFmpeg** | Audio decode/transcode | Yes | System binary, **must be on `PATH`**. Not a pip package. Windows install path must be verified. LGPL/GPL depending on build — **licence must be checked before redistribution**. |
| **Redis** | Stream buffer (P3) | Yes | Run via Docker Compose. See §10.7. |
| **SQLite** | Persistence | Yes | Bundled with Python. |
| **Docker + Compose** | Packaging | Recommended | §31.1 says "where practical". A bare-metal run path should also work. |
| **Git** | Version control | Yes | **The workspace is not currently a git repository.** |

---

## §7 — Datasets and models required

### 7.1 Statement of fact

**No model weights exist in this workspace. No dataset exists in this workspace. No audio fixture exists in this workspace. No accuracy figure exists, and none is quoted anywhere in this report.**

Everything below describes what must be **acquired**, not what is held.

### 7.2 Model families required (§6.2, §15)

| Expert | Architectural family named in source | Status |
|---|---|---|
| E1 | **AASIST-style** spectro-temporal architecture; input log-mel / LFCC / spectral | To be acquired |
| E2 | Raw PCM → learned waveform representation → temporal model | To be acquired |
| E3 | **Frozen multilingual SSL backbone — WavLM / XLS-R-class** + lightweight probe over *selected hidden layers* | To be acquired |
| E4 | **ECAPA-TDNN-style** speaker encoder, cosine similarity | To be acquired |
| E5 | Prosodic/behavioural model | Deferred (B1) |
| E6 | Replay/liveness detector | Deferred (B2) |

§6.2 on E3 adds a specific instruction: **probe frozen SSL layers rather than blindly assuming the final layer is optimal.**

§6.2 on E4 adds: this is **not** another spoof classifier — it answers *is this actually the claimed person?*

### 7.3 Acquisition requirements

Every model above requires: internet access to fetch, disk space (SSL backbones are large), and a **licence review before use or redistribution**. None of these has been performed. §39 forbids training a custom deepfake model from scratch, so pretrained weights are the only path.

### 7.4 Calibration data — absent

§8.1 is explicit:

> Initial documented weights must be treated as **engineering priors only**, not measured model parameters, until calibration data establishes them.

**No calibration data exists.** Therefore every fusion weight shipped in this demo is a **prior**, and must be labelled as such in code comments, in the UI's explanation panel if surfaced, and in any presentation.

### 7.5 Evaluation methodology — not performed

§10.5 requires dataset dimensions A–G (speaker-disjoint, generator-disjoint, channel-disjoint, language-disjoint, compound attacks, partial-spoof, code-switch density) and warns: *"Do not randomly split audio and call that evaluation."* §10.6 requires holding the generator family constant when comparing languages, because *"the language effect may actually be a generator effect."*

**No such evaluation has been designed or run.** Consequently **no performance claim of any kind may be made** about this system.

### 7.6 Demo audio fixtures required

| Fixture | For | Status |
|---|---|---|
| Genuine executive call | Scenario 1 (A35) | **Must be recorded/sourced** |
| Cloned executive voice | Scenario 2 (A36) | **Must be generated — with consent and lawful basis** |
| Poor-quality / degraded call | Scenario 3 (A37) | **Must be produced** |
| Speaker enrollment reference | E4 | **Must be recorded** |
| Hindi / Marathi / Indian-English samples | §33 | **Absent — B5** |

**Ethical and legal note:** producing a cloned voice fixture means synthesising a real person's voice. Consent from the voice donor is required, and the fixture must not be usable to impersonate anyone outside the demo. This is a prerequisite, not an afterthought.

---

## §8 — Runtime requirements

### 8.1 Target profile

**Profile A — Internal SIH: one machine is sufficient** (§18).

### 8.2 Requirements

| Requirement | Detail |
|---|---|
| OS | Development host is **Windows 11**. Docker Compose is the intended equaliser. |
| Python runtime | Version REQUIRES VERIFICATION; must be compatible with the PyTorch build chosen. |
| Node runtime | Version REQUIRES VERIFICATION. |
| **FFmpeg** | System binary on `PATH`. **The most common Windows setup failure.** |
| Redis | Container or local service. |
| Disk | Non-trivial: PyTorch plus an SSL backbone plus a speaker encoder. Exact figure unknown until models are selected. |
| GPU | **Optional.** §21 lists GPU as optional for the internal round. |
| Network | Required at install/model-fetch time. **The demo itself must run fully offline** — model weights must be vendored locally before demo day. |
| Microphone | Required only for the live-mic path; WAV fixtures are the reliable demo path. |

### 8.3 CPU latency — the live constraint

§8.3 mandates a fast clock of **100–250 ms** and a slow clock of **1–3 s**. Running four transformer-class or CNN-class models per frame on CPU may not meet the fast clock. This is **Risk R2**. Mitigations that stay within the architecture: run only a subset of experts on the fast clock and the full set on the slow clock; downsample frame rate; batch. **Faking the trajectory to hide latency is forbidden by §22 and §32.1.**

### 8.4 Windows-specific caveats

- `soundfile` depends on libsndfile; wheel availability must be verified.
- PyTorch install command differs by platform and CPU/GPU; must be pinned in the manifest once verified.
- FFmpeg is not pip-installed on Windows; path configuration must be documented.
- Redis has no first-class native Windows build; Docker is the expected route.

---

## §9 — Risks

Ranked by expected impact on demo success.

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| **R1** | **PARTIALLY DISCHARGED (2026-08-28).** Two of six experts now have real, executing models: E2 `mo-thecreator/Deepfake-audio-detection` and E4 `microsoft/wavlm-base-plus-sv`, both pinned and vendored. **Still outstanding:** E1 (no AASIST weights *or* architecture code) and E3 (backbone loads but no trained spoof probe) — both report `MODEL_UNAVAILABLE`. **Licences NOT fully reviewed:** the WavLM repo declares no licence. Both live models are architecture SUBSTITUTIONS (not AASIST/RawNet2/ECAPA). **No dataset and no evaluation set were acquired, so no accuracy figure exists.** | Certain (partially open) | Critical | Acquire AASIST weights and train the E3 probe; complete the licence review before any non-demo use. See `docs/MODEL_INVENTORY.md`. |
| **R2** | **CPU inference cannot meet the 100–250 ms fast clock.** | High | High | Split expert execution across the two clocks; reduce frame rate; measure early. Never fabricate the trajectory. |
| **R3** | **The demo produces a wrong result live.** §36 correctly forbids the scenario engine from setting scores, so a genuine misdetection is possible on stage. | Medium | High | Curate fixtures the models actually handle; rehearse with Playwright (A39); pre-agree an honest verbal response to a miss. **Do not solve this by hardcoding.** |
| **R4** | **Cloned-voice fixture is unavailable, unlawful, or unconsented.** | Medium | High | Secure a consenting voice donor early; document consent. |
| **R5** | **No Indic-language fixtures**, weakening the PS's multilingual requirement. | High | Medium | Present §33's honest framing: *"language-agnostic at the feature layer, with language-specific models that can be expanded progressively."* Never claim broad language support. |
| **R6** | **Fusion degenerates into `average(scores)`** under time pressure. §8 forbids this explicitly. | Medium | High | Implement §8.1/§8.2 first, before the UI; unit-test decay and weighting behaviour. |
| **R7** | **UI hardcodes values** to look good, violating A32. | Medium | Critical (credibility) | Assert in Playwright that values change with scenario; code review the frontend for literals. |
| **R8** | **Phase boundary leak** — a downstream phase reaching for raw audio, violating P2. | Medium | High | Enforce with contract types and a dedicated test that Phase III+ modules never import audio libraries. |
| **R9** | **Four source documents missing**; scope may shift once they are written. | Certain (present state) | Medium | Generate them from `SYMPHONY_REFERENCE.md` and freeze before implementation (§14). |
| **R10** | **`ContextVector` / `Decision` / WS events unfrozen**, blocking Phase IV and the frontend. | Certain | Medium | Freeze in the build specification before coding those layers. |
| **R11** | Windows environment failures — FFmpeg on `PATH`, libsndfile wheels, Redis. | Medium | Medium | Docker Compose as the primary run path; document a bare-metal fallback. |
| **R12** | **DISCHARGED (2026-08-28).** Weights are vendored to `assets/models/` by `scripts/fetch_models.py` with a sha256 manifest; `models_offline` sets `HF_HUB_OFFLINE`/`TRANSFORMERS_OFFLINE` before the lazy transformers import, so nothing is fetched at runtime. **Verified** by loading and running inference with `HF_HOME` pointed at a nonexistent directory. Re-check before demo day with `python scripts/fetch_models.py --verify-only`. | Low (mitigated) | Critical | Run `--verify-only` as a pre-demo gate. |
| **R13** | `PS.txt` encoding corruption reproduced into slides or the UI. | Low | Low | Repair the file before quoting it. |
| **R14** | Over-claiming during the presentation — implying telecom/banking integration or an accuracy number. | Medium | Critical (integrity) | Rehearse the §29 and §38.1 disclosure lines verbatim. |

---

## §10 — Ambiguities requiring a decision

Each is an **open question with a recommendation**, not a silent resolution. Items §10.1–§10.8 need sign-off before or during implementation.

**§10.1 — Product name: VoiceShield or VOICEGUARD?**
§24, §30.1 and §32.1 say *VoiceShield*; §32's header mockup says *VOICEGUARD*. **Recommendation: VoiceShield** — it appears in the product definition, the repository tree, and the SDK class name, so VOICEGUARD is almost certainly a stale draft. *Needs confirmation.*

**§10.2 — UI risk bands vs. VoiceBelief bands.**
§8.6 freezes `GENUINE / UNCERTAIN / SUSPICIOUS / SYNTHETIC_HIGH_CONFIDENCE`; §26.1, §32 and §35 use `LOW / MEDIUM / HIGH / CRITICAL`. **Recommendation: both are correct and describe different objects** — the four frozen bands describe the *VoiceBelief* (Phase III, voice evidence only); the four UI bands describe the *Decision risk* (Phase IV, voice + context). This distinction is exactly P5. It should be made explicit in the frozen spec and visibly labelled in the UI, or judges will read it as an inconsistency. *Needs confirmation.*

**§10.3 — `ContextVector` is never frozen as a schema.**
§9.1 describes five dimensions but gives no schema block, unlike the other contracts. **Recommendation: freeze it using the §9.1 field list (reproduced in §5.4) before Phase IV implementation begins.** *Blocking for Phase IV.*

**§10.4 — WebSocket event types are never enumerated.**
§12 names the two channels but not the message set. Because A32 forbids the UI inventing values, every panel in §32.1 needs a corresponding event. **Recommendation: freeze an event set covering risk update, evidence update, timeline event, transaction status, recommendation, language detection, privacy state, and session lifecycle.** *Blocking for the frontend.*

**§10.5 — Are E5 and E6 absent, or computed-but-unscored?**
§25's internal slice omits both; the PS demands both. **Recommendation: compute E5 prosodic features (they are cheap DSP and the UI has a Prosody card in §32.1) but emit `p_beh = ABSTAIN` since no calibrated model exists. E6 absent entirely, `p_rep = ABSTAIN`.** Keep both fields in `EvidenceVector`. This is honest and satisfies the UI without fabricating a score. *Needs confirmation.*

**§10.6 — `PS.md` vs `PS.txt`.**
The brief named `PS.md`; the file is `PS.txt`. §30.1 places `docs/PS.md` in the tree. **Recommendation: create `docs/PS.md` as a clean, encoding-repaired copy and retain `PS.txt` as the untouched original.** *Not blocking.*

**§10.7 — Is Redis mandatory for Profile A?**
P3 names Redis Streams as *the* decoupling mechanism and §18 lists Redis in Profile A. An in-process queue would be simpler on a single machine. **Recommendation: keep Redis.** P3 is a locked principle, §23's master diagram places Redis Streams between Phase I and II, and removing it would be an architecture change requiring §22 review. It also materially strengthens the "production-shaped" claim. *Needs confirmation only if setup proves obstructive.*

**§10.8 — Which repository tree governs, §30 or §30.1?**
§30 is the internal-round tree (top-level `ingestion/`, `signal_processing/`, `models/`, `context/`, `decision/`). §30.1 is the "final demo-day folder" with those nested under `backend/`. **Recommendation: §30.1**, since it is labelled as the post-build-program state and matches the `docs/` layout being adopted here. *Needs confirmation.*

**§10.9 — Scenario 3 — RESOLVED.**
§35.2 explicitly left this open. **Decision: Scenario 3 is the poor-quality-audio → `UNCERTAIN` → `STEP_UP` case** (A37). Rationale: it directly demonstrates P4 (*probability ≠ confidence*) and the §22 abstention semantics, which are the most defensible parts of the architecture, at far lower implementation risk than partial-spoof localisation. **Partial-spoof localisation (B3) is retained as the documented stretch target**, consistent with §8.4's own warning not to claim a localisation resolution until measured.

---

## §11 — Items requiring a real implementation

Derived from §28's "Real" column. Simulating any of these would make the demo dishonest.

1. **Audio ingestion** — actual streaming, chunking, buffering of WAV/microphone input.
2. **Audio preprocessing** — actual resampling, normalisation, VAD, quality estimation.
3. **Feature extraction** — actual spectrogram, log-mel, MFCC, prosodic features.
4. **Anti-spoofing inference** — an actual model producing an actual score from the actual audio.
5. **Speaker embedding and comparison** — actual embeddings, actual cosine similarity.
6. **Fusion arithmetic** — actual quality-conditioned weighting, calibration, log-odds accumulation with decay.
7. **Uncertainty computation** — actual confidence, actually separate from probability (P4).
8. **Risk calculation** — actual combination of voice belief and context.
9. **Policy and state machine** — actual tier-conditioned thresholds and actual state transitions.
10. **Action emission** — actual `ALLOW`/`WARN`/`STEP_UP`/`HOLD`/`ESCALATE` decisions derived from the pipeline.
11. **WebSocket streaming** — actual live transport, not polled fake updates.
12. **Backend APIs** — actual FastAPI endpoints per §5.7.
13. **Frontend** — actual rendering of actual backend state (A32).
14. **Evidence hash chain** — actual `previous_hash` linkage.
15. **Privacy lifecycle** — actual buffer expiry; raw audio genuinely not persisted by default (§10.3).

**The binding rule (§36):** the scenario engine *"must not directly set the risk score. It may only select the audio fixture, provide context, provide transaction context, and start the session. The real pipeline must produce the result."*

---

## §12 — Items that may legitimately be simulated

Each entry carries the disclosure obligation. Per §36 the UI must display:

```text
DEMO MODE
This environment uses controlled test audio and simulated transaction context.
```

| # | Simulated | Why legitimate | Required disclosure |
|---|---|---|---|
| S1 | **Telephony boundary** — WAV/mic instead of PSTN/SIP/RTP | §29 makes this a deliberate prototype boundary; P1 guarantees the adapter is swappable | §29/§38.1 line: *"the telephony boundary is simulated using a real-time audio stream. The ingestion interface is deliberately decoupled from the detection pipeline so that the same backend can later accept SIP/RTP or enterprise communication streams."* |
| S2 | **Transaction / banking system** — a simulator panel | §26, §39; real banking integration and real fund movement are category D | State that no bank is connected and no money moves |
| S3 | **Caller identity, CNAP, number reputation** | §21 maps CNAP to "simulated adapter" for the internal round | Label the context panel as simulated |
| S4 | **Behavioural context** (urgency, secrecy, callback refusal) supplied by the scenario | §9.1 fields exist; no NLU is in scope, and §16 bars an LLM from the detection path | Label as scenario-supplied |
| S5 | **Alert delivery** — SMS/email/push not actually sent | B7 | Show the alert in-UI only; do not imply delivery |
| S6 | **MFA and call-back actions** — buttons that record an intent | §21 "action adapter" is production-grade | Show as recommended actions, not executed ones |
| S7 | **Enrollment reference audio** — a curated sample rather than a real enrollment programme | E4 needs a reference; a real enrollment corpus is B6 | State that enrollment is a single curated reference |
| S8 | **Curated demo recordings** rather than arbitrary live calls | §28 lists "curated demo recordings" under Controlled | Covered by the `DEMO MODE` banner |
| S9 | **Deterministic scenario orchestration** | §28 lists this under Controlled | Covered by the `DEMO MODE` banner |

**Absolute boundary:** simulation may supply *inputs and downstream effects*. It may **never** touch a probability, a confidence, a belief, a risk score, or a band. Those come from the pipeline or they are marked `UNCERTAIN` / `MODEL_UNAVAILABLE` / `ABSTAIN`.

---

## §13 — Traceability matrix

Extends §20 with the scope classification §20 lacks.

| PS requirement | Architecture element | Cat. | Real / Simulated |
|---|---|---|---|
| Real-time audio analysis | Phase I + WebSocket ingestion | A | Real |
| Telephony (PSTN) | SIP/RTP adapter | D | **Not built** |
| VoIP | WebRTC/SIP adapter | D | **Not built** |
| Collaboration platforms | SDK/audio adapter | C | **Not built** |
| Synthetic speech detection | E1 / E2 / E3 | A | Real |
| Acoustic artefacts | E1 | A | Real |
| Spectral signatures | E1 | A | Real |
| Raw waveform patterns | E2 | A | Real |
| Neural synthesis patterns | E3 | A | Real |
| Speaker identity | E4 | A | Real |
| Prosody / behaviour | E5 | **B1** | Features real; score abstains |
| Replay detection | E6 | **B2** | Abstains |
| Cross-session consistency | E4 + reference store | **B6** | Single curated reference only |
| Dynamic risk score | Phase III belief engine | A | Real |
| Contextual enrichment | Phase IV context service | A | Real logic, simulated values |
| Caller metadata | Context service | A / S3 | Simulated |
| Transaction context | Context service | A / S2 | Simulated |
| Historical fraud indicators | Context service | A / S3 | Simulated |
| Threshold-based alerting | Phase IV tiers + policy | A | Real |
| Real-time alerts | Phase V + event stream | A | Real in-UI |
| Multi-channel alerts (SMS/email) | Alert adapters | **B7** | **Not built** |
| Pre-transaction warning prompt | Recommendation panel | A | Real |
| Secondary verification / call-back | Action adapter | A / S6 | Emission real, execution simulated |
| MFA | Action adapter | A / S6 | Emission real, execution simulated |
| Supervisor escalation | Action adapter | A / S6 | Emission real, execution simulated |
| High-value transaction protection | Transaction tiers 0–4 | A | Real |
| Configurable workflows | Policy engine | A (basic) / C (full) | Real, limited |
| Privacy — minimal retention | Phase V privacy lifecycle | A | Real |
| Edge / on-device inference | Deployment profile | **B13** | **Not built** |
| Feature-only logging | Evidence architecture | A | Real |
| REST API | API layer | A | Real |
| gRPC | Internal/enterprise integration | **B8** | **Not built** |
| SDK | SDK layer | **B9** | **Not built** |
| Indian languages | SSL + language layer | **B5** | Architecture only; no validated claim |
| Indian accents | Data/training/evaluation strategy | **B5** | **No data, no claim** |
| Code switching | Phase I tagging + III.5 guard | **B4** | **Not built** |
| Partial spoof | Frame logits + III.4 localisation | **B3** | Stretch target |
| Explainability | V.1 explanation service | A | Real |
| Compliance evidence | V.2 evidence record | A | Real (local signing) |
| Feedback loop | V.4 | **B16** | **Not built** |
| Drift detection | V.5 | **B16** | **Not built** |
| Scalability | Stateless I/II/IV + workers | C | Architectural only |
| Deployment | Docker → Kubernetes | A (Docker) / C1 (K8s) | Docker real |
| Banking system integration | Action/context adapters | **D** | **Not built — simulator only** |
| Telecom operator integration | Ingress adapters | **D** | **Not built** |

---

## §14 — Readiness verdict and next artifacts

### 14.1 Verdict

**NOT READY to begin application code.** The architecture is unusually well specified and internally coherent, but four preconditions are unmet:

1. Four of the six named source documents do not exist (R9).
2. No models, datasets, or audio fixtures have been acquired, and no licence review has occurred (R1).
   *Update 2026-08-28 (L3 build): partially addressed. Two models are now vendored and
   executing (E2, E4) and synthetic audio fixtures exist. Still true: **no dataset and no
   evaluation set have been acquired, so no accuracy figure exists anywhere**; the licence
   review is incomplete (the WavLM repo declares no licence); E1 and E3 have no usable
   model. See `docs/MODEL_INVENTORY.md`.*
3. Two contracts — `ContextVector` and `Decision` — and the WebSocket event set are not frozen (R10).
4. The §41 machine-executable implementation specification does not exist. §41 states plainly: *"Do not give an agent the architecture and immediately say 'build everything.'"*

### 14.2 Files to create next, in order

**Stage 0 — specification (before any code):**

| Order | File | Content basis |
|---|---|---|
| 1 | `docs/IMPLEMENTATION_READINESS.md` | *This document.* |
| 2 | `docs/PS.md` | Encoding-repaired copy of `PS.txt`; original retained untouched. |
| 3 | `docs/ARCHITECTURE.md` | Extracted from `SYMPHONY_REFERENCE.md` Part A. |
| 4 | `docs/EXECUTION_TECH_STACK.md` | §31/§31.1 + §6 of this report, with versions **verified**, not guessed. |
| 5 | `docs/DEMO_SCOPE.md` | The A/B/C/D classification in §2 of this report. |
| 6 | `docs/DEMO_SCENARIOS.md` | The three frozen scenarios, with Scenario 3 = UNCERTAIN. |
| 7 | `docs/EXECUTABLE_ARCHITECTURE.md` | The §41 machine-executable spec: repository tree, module boundaries, **every** Pydantic schema (including the newly frozen `ContextVector` and `Decision`), every Redis stream, every endpoint, **every WebSocket event**, every model interface, every table, every config variable, every Docker service, every test, every fixture, startup/shutdown behaviour, failure/abstention semantics, dependency verification matrix. |

**Stage 1 — first code (only after Stage 0 sign-off):** repository skeleton per §30.1, `.gitignore`, `README.md`, `.env.example`, git initialisation, dependency manifests with **verified** versions, and the five contracts as Pydantic models with tests asserting phase isolation (P2).

### 14.3 Proposed implementation sequence

Governed by the source's own final priority (§1217): **"get one complete end-to-end path running before expanding the system."**

| Step | Work | Gate to pass |
|---|---|---|
| 0 | Stage 0 documents; acquire and licence-review models; secure consented fixtures | Weights vendored locally; offline load verified |
| 1 | Repo skeleton, contracts as Pydantic models, fixtures | P2 isolation test passes |
| 2 | Phase I → `FrameObject` → Redis Stream | Frames flow; P3 verified (capture does not block) |
| 3 | Phase II with **E1 only**, end-to-end | One real score from real audio |
| 4 | Add E2, E3, E4; `EvidenceVector` complete with E5/E6 abstaining | Latency measured against the fast clock |
| 5 | Phase III: weighting, calibration, log-odds decay, two clocks, uncertainty | Trajectory is monotone-ish and explicable, not jumpy |
| 6 | Phase IV: context, tiers, policy, state machine, actions | Tier 3/4 demonstrably tightens thresholds |
| 7 | Phase V: explanation, evidence record, hash chain, privacy | Chain verifies; raw audio provably not persisted |
| 8 | Frontend — seven panels, all values from WebSocket | Zero hardcoded values (A32) |
| 9 | Scenario engine — fixtures and context only | Audit that it cannot write a score (§36) |
| 10 | Playwright rehearsal; offline cold-start drill | Full run passes with no network |

---

## §15 — The binding contract

Reproduced from `SYMPHONY_REFERENCE.md` §22, and binding on every subsequent implementation step:

> **No developer or AI agent may modify the five phase boundaries, cross-phase contracts, model roles, or decision semantics without first modifying the architecture specification and obtaining review.**

> **No score may be fabricated to make the demo work.**

> If a model isn't available → `MODEL_UNAVAILABLE`
> If audio is insufficient → `UNCERTAIN`
> If the speaker is not enrolled → `E4 = ABSTAIN`
> If codec identification is uncertain → `codec = UNKNOWN`

> *Those behaviours are much more credible than silently inventing values. Graceful abstention, uncertainty handling and honest disclosure of limitations are required.*

---

*End of report. No application code was written, and no source document was modified, in producing it.*

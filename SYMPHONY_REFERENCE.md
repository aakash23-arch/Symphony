# SYMPHONY / VoiceShield — Final Master Architecture

**Real-Time Voice Integrity & Impersonation Defense**
**SIH26104 — AI-Powered Real-Time Detection and Prevention of Voice Cloning Impersonation Attacks**

---

### Document scope

This document consolidates three passes of architectural work into one master reference:

1. The **executive/production architecture** (five-phase Symphony layer, frozen contracts, security, storage, MLOps, deployment profiles).
2. The **internal-round vertical slice** (the smallest system that demonstrates the complete security story end-to-end).
3. The **updated/locked technology stack** for both the production target and the internal prototype.

Nothing has been added beyond the source material and nothing has been removed. Where the three passes described the same component at different levels of detail, the production-grade description is treated as canonical and the prototype-grade version is retained separately under the internal-round sections.

---

# PART A — THE PRODUCTION ARCHITECTURE

## 1. Executive architectural decision

The final product is **not a mobile application**.

It is an **AI voice-security platform** sitting between a communication/audio source and the systems or people that need to act on the result.

```text
             AUDIO / CALL SOURCES
 ┌───────────────────────────────────────────┐
 │ PSTN / SIP / RTP                          │
 │ VoIP / WebRTC                             │
 │ Enterprise collaboration                  │
 │ Contact-centre systems                    │
 │ SDK / microphone                          │
 │ Recorded / forensic audio                 │
 └─────────────────────┬─────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                 SYMPHONY VOICE SECURITY LAYER               │
│                                                             │
│ I   INTAKE       → condition the signal                     │
│ II  ANALYSIS     → independent forensic experts             │
│ III FUSION       → evidence → voice belief                  │
│ IV  DECISION     → voice + context → action                 │
│ V   ASSURANCE    → explanation + evidence + learning        │
│                                                             │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
              SECURITY OUTPUT PLANE
 ┌────────────────────────────────────────────────────────────┐
 │ Enterprise dashboard                                       │
 │ Banking transaction system                                 │
 │ Contact-centre UI                                          │
 │ SOC/SIEM                                                   │
 │ SMS/email/push notification                                │
 │ API / SDK consumer                                         │
 │ Supervisor / analyst                                       │
 │ Automated hold / escalation / MFA                          │
 └────────────────────────────────────────────────────────────┘
```

This resolves the earlier ambiguity about the endpoint: **the detector is an infrastructure/security layer, not inherently a handset app.**

---

## 2. Architectural principles — LOCK THESE

These are non-negotiable.

### P1 — Audio source independence

The detection system must not care whether audio originated from PSTN, SIP/RTP, VoIP, WebRTC, enterprise collaboration, microphone, or an uploaded recording. **All sources terminate in the same canonical ingestion contract.**

### P2 — Phase isolation

The five phases remain independently testable.

```text
I → II → III → IV → V
             ↑       │
             └───────┘
```

Phase V closes the learning/assurance loop.

The contract rule is absolute: **a phase may only consume fields declared by its input object; if a downstream phase wants raw audio, the architecture has leaked.**

### P3 — Capture never waits for ML

Audio acquisition must never block because inference is slow.

```text
Audio → Ingress → Buffer → Redis Streams → Analysis workers
```

Redis Streams is the decoupling mechanism; Phase I must not stall behind downstream inference.

### P4 — Probability ≠ confidence

Never render `30% spoof + high confidence` as equivalent to `30% spoof + low confidence`.
**Low confidence means "we don't know", not "probably genuine."**

### P5 — Protect actions, not recordings

The final decision is not *"Is this WAV fake?"* It is:

> **"Given the voice evidence and the requested action, should this action be trusted?"**

That is the architectural distinction between a deepfake detector and a fraud-prevention system.

---

## 3. Complete system architecture

```text
                         ┌───────────────────────┐
                         │   EXTERNAL SOURCES    │
                         ├───────────────────────┤
                         │ PSTN/SIP/RTP          │
                         │ WebRTC                │
                         │ Enterprise SDK        │
                         │ Contact Centre        │
                         │ Microphone            │
                         │ File / Forensics      │
                         └───────────┬───────────┘
                                     │
                                     ▼
                    ┌─────────────────────────────┐
                    │      INGESTION GATEWAY      │
                    │                             │
                    │ SIP/RTP adapter             │
                    │ WebRTC adapter              │
                    │ SDK adapter                 │
                    │ File adapter                │
                    │ Audio normalisation         │
                    │ Authentication              │
                    │ Session creation            │
                    └─────────────┬───────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────────┐
                    │      STREAM BUFFER          │
                    │      Redis Streams          │
                    └─────────────┬───────────────┘
                                  │
                    ╔═════════════╧══════════════╗
                    ║                            ║
                    ▼                            ▼
             ┌──────────────┐             Context events
             │   PHASE I    │
             │   INTAKE     │
             └──────┬───────┘
                    │ FrameObject
                    ▼
             ┌──────────────┐
             │   PHASE II   │
             │   ANALYSIS   │
             │              │
             │ E1 Spectral  │
             │ E2 Raw       │
             │ E3 SSL       │
             │ E4 Speaker   │
             │ E5 Prosody   │
             │ E6 Replay    │
             └──────┬───────┘
                    │ EvidenceVector
                    ▼
             ┌──────────────┐
             │  PHASE III   │
             │   FUSION     │
             │              │
             │ weighting    │
             │ calibration  │
             │ accumulation │
             │ localisation │
             │ code-switch  │
             │ uncertainty  │
             └──────┬───────┘
                    │ VoiceBelief
                    ▼
             ┌──────────────┐
             │   PHASE IV   │◄──────── Context Service
             │  DECISION    │
             │              │
             │ risk fusion  │
             │ tier policy  │
             │ state machine│
             │ actions      │
             └──────┬───────┘
                    │ Decision
                    ▼
             ┌──────────────┐
             │   PHASE V    │
             │  ASSURANCE   │
             │              │
             │ explanation  │
             │ evidence     │
             │ privacy      │
             │ feedback     │
             │ drift        │
             └──────┬───────┘
                    │
        ┌───────────┼────────────┐
        ▼           ▼            ▼
     Dashboard   API/SDK     Action systems
        │                        │
        ▼                        ▼
    Analyst UI            MFA / HOLD / ESCALATE
```

---

## 4. Phase I — INTAKE / "Listen"

Phase I remains intact: stream gateway, channel profiling, quality estimation, VAD/pre-roll, diarisation-lite and language/code-switch tagging.

### 4.1 Complete boundary

```text
Source Adapter
      ↓
Ingress Authentication
      ↓
Session Manager
      ↓
Jitter Buffer
      ↓
Packet-loss handling
      ↓
PCM Normalisation
      ↓
Resampling
      ↓
Channel Profiler
      ↓
Quality Estimator
      ↓
VAD
      ↓
Speaker-turn segmentation
      ↓
Language / code-switch tagging
      ↓
FrameObject
      ↓
Redis Stream
```

### 4.2 Supported source adapters

**Production:** SIP/RTP · WebRTC/SRTP · enterprise audio SDK · contact-centre integration · telecom gateway
**Development/demo:** microphone · WAV/FLAC · real-time replay simulator

These are deliberately interchangeable.

---

## 5. Canonical FrameObject — frozen contract

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

No downstream component should directly depend on SIP, WebRTC, microphone APIs, etc.

---

## 6. Phase II — ANALYSIS / "Score"

Phase II is an independent multi-expert forensic layer.

| Expert | Question |
|---|---|
| E1 Spectro-temporal | Are spectral/synthesis artefacts present? |
| E2 Raw waveform | Are waveform-level anomalies present? |
| E3 SSL | Does a multilingual learned representation indicate spoofing? |
| E4 Speaker | Does this sound like the claimed/enrolled speaker? |
| E5 Prosody/behaviour | Is natural conversational behaviour inconsistent? |
| E6 Replay/liveness | Is this potentially replayed audio rather than generated speech? |

Six independent expert roles, with different failure modes.

### 6.1 Final ML architecture

```text
                    FrameObject
                         │
       ┌─────────────────┼────────────────────┐
       │                 │                    │
       ▼                 ▼                    ▼
 Spectrogram          Raw PCM             SSL embedding
       │                 │                    │
       ▼                 ▼                    ▼
 E1 model             E2 model             E3 model
       │                 │                    │
       └────────────┬────┴────────────┬───────┘
                    │                 │
                    ▼                 ▼
              E4 Speaker          E5 Prosody
                    │                 │
                    └────────┬────────┘
                             ▼
                         E6 Replay
                             │
                             ▼
                     EvidenceVector
```

**Critical architectural rule: the experts do not consume each other's outputs.** This maintains genuine evidence independence rather than giving one ensemble six names.

### 6.2 Model implementation strategy (frozen)

**E1 — Spectro-temporal**
AASIST-style spectro-temporal architecture.
Input: log-mel / LFCC / spectral representation.
Output: `p_spec`, `frame_logits_spec[]`, `confidence_spec`

**E2 — Raw waveform**
Raw PCM → learned waveform representation → temporal model.
Output: `p_raw`, `frame_logits_raw[]`, `confidence_raw`

**E3 — SSL**
Frozen multilingual SSL backbone. Recommended architectural family: **WavLM / XLS-R-class representation.**

```text
selected hidden layers
       ↓
lightweight probe
       ↓
spoof classifier
```

Probe frozen SSL layers rather than blindly assuming the final layer is optimal.

**E4 — Speaker verification**

```text
caller/reference audio → ECAPA-style speaker encoder → embedding_reference
current call           → ECAPA-style speaker encoder → embedding_current
                          cosine similarity
                                ↓
                        speaker consistency
```

This is deliberately **not** another spoof classifier. It answers a different question: *is this actually the claimed person?*

**E5 — Prosody / behavioural**
Features: F0, energy, pause distribution, speaking rate, turn latency, jitter/shimmer where measurable, conversational timing.
This remains a **weak supporting expert, never proof of human speech.**

**E6 — Replay / liveness**
Detect replay characteristics, re-recording artefacts, channel/room inconsistencies, playback signatures. Covers an attack class that is neither conventional TTS nor voice conversion.

---

## 7. EvidenceVector — frozen contract

```text
EvidenceVector
{
    session_id
    frame_id

    p_spec
    p_raw
    p_ssl
    p_spk
    p_beh
    p_rep

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

This is the original frozen contract (six probabilities, frame logits, confidence values, quality, codec and language fields) expanded with the operational provenance a real system requires.

---

## 8. Phase III — FUSION / "Harmony"

This is the heart of Symphony. **Do not reduce it to `average(scores)`.**

```text
EvidenceVector
       ↓
Quality-conditioned weighting
       ↓
Calibration
       ↓
Temporal accumulation
       ↓
Evidence decay
       ↓
Partial-spoof localisation
       ↓
Code-switch guard
       ↓
Uncertainty estimation
       ↓
VoiceBelief
```

### 8.1 Quality-conditioned expert weighting

The system already knows sample rate, codec, packet loss, noise, clipping and speech quality. Therefore:

```text
weight_i = f(q_t, codec_vec, expert reliability)      NOT      weight_i = constant
```

A narrowband 8 kHz signal should reduce reliance on evidence that depends heavily on information above the available bandwidth.

Initial documented weights must be treated as **engineering priors only**, not measured model parameters, until calibration data establishes them.

### 8.2 Temporal belief engine

This is the mechanism that creates the real-time behaviour.

```text
frame 1 → evidence
frame 2 → evidence
frame 3 → evidence
frame 4 → evidence
...
                ↓
        accumulated belief
                ↓
         risk trajectory
```

Conceptually:

```text
log O_t = decay(log O_(t-1)) + bounded evidence contribution
P_spoof = O / (1 + O)
```

Bayesian log-odds accumulation with evidence decay.

**Why this matters:** the judge sees `12% → 19% → 31% → 44% → 61% → 78% → 91%` instead of a score that jumps around randomly.

### 8.3 Two-clock architecture

Implement explicitly.

**Fast clock — 100–250 ms:** live UI, provisional score, frame evidence, trajectory.
**Slow clock — 1–3 second rolling evidence window:** action-grade decision, stronger confidence, policy enforcement.

Do not pretend that a single instantaneous score is the final decision.

### 8.4 Partial-spoof localisation

A flagship capability.

```text
frame logits → temporal smoothing → threshold → contiguous-span merging → synthetic segments
```

```text
Call timeline

0s ───────────────────────────────────────── 60s

       HUMAN SPEECH
              │
              ▼
         ┌──────────┐
         │ SYNTHETIC│
         │ 41–45s   │
         └──────────┘
                   │
                   ▼
              HUMAN SPEECH
```

**Do not claim a particular localisation resolution until measured.** Performance degrades for very short synthetic segments.

### 8.5 Code-switch stability guard

Essential for the Indian context.

```text
language boundary detected
          ↓
spoof score changes
          ↓
is change corroborated?
      /          \
    NO            YES
    ↓              ↓
dampen            retain
    ↓              ↓
switch_damped     evidence
```

The guard must log **every** damped event, so you can measure whether it is suppressing genuine attacks or correctly suppressing language-switch false positives.

### 8.6 VoiceBelief — frozen output

```text
VoiceBelief
{
    session_id

    P_spoof
    confidence

    band

    q_call

    spans[]

    trajectory[]

    contributing_experts[]

    uncertainty_reason

    switch_damping_events[]

    model_versions[]

    timestamp
}
```

Possible bands: `GENUINE` · `UNCERTAIN` · `SUSPICIOUS` · `SYNTHETIC_HIGH_CONFIDENCE`

Do not force `fake / real` when the evidence does not justify it.

---

## 9. Phase IV — DECISION / "Conductor"

This layer must be **separate from voice detection.**

```text
VoiceBelief + ContextVector
      ↓
Risk Fusion
      ↓
Transaction Sensitivity
      ↓
Policy Engine
      ↓
State Machine
      ↓
Action
```

### 9.1 Context architecture

**Identity:** claimed identity · verified identity · enrollment status · CNAP state · identity mismatch
**Number:** reputation · age · known-fraud status · port history
**Transaction:** amount · transaction type · beneficiary novelty · velocity · historical deviation
**Behaviour:** urgency · secrecy · callback refusal · verification bypass · unusual request
**Technical:** device signal · network origin · VoIP/mobile indicator · codec

### 9.2 Transaction sensitivity (five tiers, frozen)

| Tier | Example | Default response |
|---|---|---|
| 0 | Informational | Monitor |
| 1 | Account information | Warn |
| 2 | Credential/security action | Step-up |
| 3 | Financial transaction | Step-up / hold |
| 4 | Privileged authorisation | Hold / escalate |

The effective threshold must become **more conservative as transaction sensitivity increases.**

### 9.3 Risk model

Gradient-boosted decision model + explicit policy layer. Use **XGBoost** for contextual risk modelling — **but it must not have the final say.**

```text
ML risk model → transaction sensitivity → policy rules → state machine → action
```

This prevents an opaque model from directly deciding whether a financial transaction executes.

### 9.4 Risk state machine

```text
UNKNOWN
   │
   ▼
MONITORING
   │
   ├──────────────► TRUSTED
   │
   ├──────────────► VERIFY
   │
   └──────────────► HIGH_RISK
                         │
                 ┌───────┴───────┐
                 ▼               ▼
               HOLD          ESCALATE
                 │
                 ▼
              REVIEWED
```

Action classes: `ALLOW` · `WARN` · `STEP_UP` · `HOLD` · `ESCALATE` · `ACTIVE_LIVENESS`

### 9.5 Active liveness

A fallback, not the primary detector.

```text
UNCERTAIN → challenge          NEVER:   every call → challenge
```

The challenge should be **dynamically generated/semantic**, never a permanently known phrase — this ordering minimises friction while avoiding a trivially pre-synthesised fixed phrase.

---

## 10. Phase V — ASSURANCE / "Coda"

Five concrete services: **V.1 Explanation · V.2 Evidence · V.3 Privacy · V.4 Feedback · V.5 MLOps/Drift.**

### 10.1 Explanation service

```text
WHY WAS THIS CALL FLAGGED?

Synthetic speech evidence       +34
Speaker mismatch                +23
Transaction sensitivity         +18
New beneficiary                 +12
Behavioural cue                  +7

Risk                            94
Confidence                      91
```

The UI must distinguish **model attribution** from **causal proof.**

Never say: *"These frequencies prove it is fake."*
Say: *"These are the features contributing to the model's decision."*

### 10.2 Evidence record

Every action-grade decision produces:

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

A signed, append-only, hash-chained record containing decision, belief, context, model version and previous hash.

### 10.3 Privacy architecture

```text
RAW AUDIO
   │
   ▼
short-lived buffer
   │
   ├──► inference
   │
   ▼
automatic expiry

PERSISTENT STORAGE
   │
   ├── feature vectors
   ├── risk events
   ├── decisions
   ├── evidence records
   └── approved speaker embeddings
```

**Never make raw audio persistence the default.** Short-lived raw audio buffers, feature/risk persistence, embedding-based speaker storage, edge processing options.

### 10.4 MLOps architecture

The biggest missing piece in simplified versions. The complete product requires:

```text
Data → Data validation → Dataset version → Training → Evaluation → Calibration
     → Model registry → Canary deployment → Monitoring → Drift detection
     → Human feedback → Retraining
```

### 10.5 Dataset architecture

Maintain explicit dataset dimensions:

```text
A Speaker-disjoint
B Generator-disjoint
C Channel-disjoint
D Language-disjoint
E Compound attacks
F Partial-spoof
G Code-switch density
```

**Do not randomly split audio and call that evaluation.**

### 10.6 Generator-control experiment

When comparing languages:

```text
Generator A                 Generator B
 ├── Hindi                   ├── Hindi
 ├── Marathi                 ├── Marathi
 └── Indian English          └── Indian English
```

Keep generator family constant when evaluating language effects — otherwise the **language effect may actually be a generator effect.**

---

## 11. Security architecture

Must surround the entire system.

```text
                 API Gateway
                     │
              Authentication
                     │
              Authorization
                     │
            Rate limiting
                     │
                     ▼
              Application APIs
                     │
       ┌─────────────┼─────────────┐
       ▼             ▼             ▼
   Audio plane   Context plane  Action plane
       │             │             │
       └─────────────┼─────────────┘
                     ▼
                Audit plane
```

Implement: OAuth2/OIDC-compatible authentication · JWT access tokens · RBAC · service-to-service authentication · TLS · secrets outside source code · encrypted storage · API rate limiting · input validation · audit logging · dependency scanning · container scanning · model checksum/version verification · signed model artifacts · replay protection · session expiry.

---

## 12. API architecture

The external API should be deliberately small.

**Sessions**
```http
POST /v1/sessions
GET  /v1/sessions/{id}
POST /v1/sessions/{id}/start
POST /v1/sessions/{id}/stop
```

**Live audio**
```http
WS /v1/sessions/{id}/audio
```

**Live security state**
```http
WS /v1/sessions/{id}/events
```

**Evidence**
```http
GET /v1/sessions/{id}/evidence
GET /v1/sessions/{id}/timeline
```

**Risk**
```http
GET /v1/sessions/{id}/risk
```

**Context**
```http
POST /v1/sessions/{id}/context
```

**Actions**
```http
POST /v1/sessions/{id}/actions/verify
POST /v1/sessions/{id}/actions/hold
POST /v1/sessions/{id}/actions/escalate
```

---

## 13. SDK architecture

```text
VoiceShieldClient
 ├── start_session()
 ├── stream_audio()
 ├── get_risk()
 ├── get_evidence()
 ├── get_decision()
 └── subscribe_events()
```

The SDK should **never expose the internal ML implementation.** A bank should not need to know whether E1 is AASIST, another model, or a future model.

---

## 14. Storage architecture

| Data | Storage |
|---|---|
| Session state | PostgreSQL |
| Context/transaction | PostgreSQL |
| Evidence records | PostgreSQL |
| Hash-chain records | PostgreSQL + immutable export |
| Redis stream | Redis |
| Short-lived audio | local/object ephemeral store |
| Model artefacts | object storage |
| Dataset | object storage |
| Metrics | Prometheus |
| Logs | Loki/OpenSearch-class system |
| Dashboard | Grafana + application UI |

For the internal prototype, **SQLite can replace PostgreSQL and local files can replace object storage** — but the architecture must not be redesigned around SQLite.

---

## 15. Final production technology stack (frozen)

**Frontend:** React · TypeScript · Vite · Tailwind CSS · shadcn/ui · Recharts · WebSocket client

**API:** Python · FastAPI · Pydantic · Uvicorn

**Real-time transport:** WebSocket · Redis Streams

**Audio:** FFmpeg · soundfile · librosa · NumPy · SciPy

**DSP:** NumPy · SciPy · librosa

**Deep learning:** PyTorch · Hugging Face Transformers · SpeechBrain

**Models:**
- E1: AASIST-style architecture
- E2: raw-waveform anti-spoof model
- E3: WavLM/XLS-R-class SSL backbone + lightweight probe
- E4: ECAPA-TDNN speaker encoder
- E5: prosodic/behavioural model
- E6: replay/liveness detector

**Fusion:** NumPy / SciPy · scikit-learn calibration · custom temporal belief engine

**Context risk:** XGBoost

**Backend persistence:** PostgreSQL · Redis

**Observability:** Prometheus · Grafana · structured JSON logging · OpenTelemetry

**Testing:** pytest · pytest-asyncio · Playwright

**Security:** OAuth2/OIDC · JWT · TLS · RBAC

**Packaging:** Docker · Docker Compose

**CI/CD:** GitHub · GitHub Actions

**MLOps:** MLflow · DVC

**Production orchestration:** Kubernetes — *a deployment target, not a prerequisite for the SIH prototype.*

### 15.1 One-line version (the answer if a judge asks "what exactly is your technology stack?")

> React + TypeScript frontend; Python/FastAPI real-time backend; WebSockets + Redis Streams for streaming; FFmpeg/librosa/NumPy/SciPy for audio and DSP; PyTorch with AASIST-style, raw-waveform, SSL and ECAPA-based models for forensic analysis; XGBoost for contextual risk fusion; PostgreSQL/Redis for state; MLflow/DVC for model lifecycle; Prometheus/Grafana/OpenTelemetry for observability; Docker for deployment and Kubernetes as the production scaling target.

---

## 16. What I would NOT add

Freeze these out unless a genuine requirement appears:

Kafka · RabbitMQ · Celery · Spark · Kubernetes for internal demo · GraphQL · MongoDB · Elasticsearch as primary database · microservices for every class · mobile application · custom telecom hardware · custom FPGA/DSP hardware · LLM in the core detection path · blockchain

**In particular: no LLM for voice authenticity.** An LLM can potentially assist with explanation, analyst summaries, and behavioural-language interpretation — but the core anti-spoof decision must remain an audio ML/DSP pipeline.

---

## 17. Production deployment topology

```text
                        INTERNET / TELCO
                              │
                              ▼
                       Load Balancer
                              │
                              ▼
                       API Gateway
                              │
               ┌──────────────┴──────────────┐
               │                             │
               ▼                             ▼
         Session API                    Audio Gateway
               │                             │
               │                         Redis Streams
               │                             │
               │                  ┌──────────┼──────────┐
               │                  ▼          ▼          ▼
               │                 I1         I2         In
               │                  │          │          │
               │                  └──────────┼──────────┘
               │                             ▼
               │                        Phase II
               │                     ML worker pool
               │                             │
               │                             ▼
               │                        Phase III
               │                       state store
               │                             │
               │                             ▼
               │                        Phase IV
               │                             │
               │                 ┌───────────┼────────────┐
               │                 ▼           ▼            ▼
               │             Core bank    Identity      Policy
               │                 │
               │                 ▼
               │              Decision
               │
               └──────────────────────► Phase V
                                           │
                              ┌────────────┼────────────┐
                              ▼            ▼            ▼
                           Evidence     Metrics      Feedback
```

---

## 18. Deployment profiles

How the enormous production architecture reconciles with the SIH reality.

**Profile A — Internal SIH:** React · FastAPI · Redis · SQLite · PyTorch · local model files · WebSocket · Docker Compose. *One machine is sufficient.*

**Profile B — Pilot deployment:** React · FastAPI · Redis · PostgreSQL · GPU inference worker · object storage · Prometheus · Grafana

**Profile C — Enterprise:** Kubernetes · multiple ingestion workers · Redis cluster · PostgreSQL HA · GPU inference pool · object storage · model registry · observability · IAM · SIEM integration · enterprise communication adapters

**The logical architecture does not change between these profiles.** That is exactly what you want.

---

## 19. Endpoint / output architecture

The final output is not just a number.

```text
                    Decision
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
     Machine          Human         Audit
     output           output        output
        │              │              │
        ▼              ▼              ▼
     REST/API       Dashboard     Evidence record
     WebSocket      Alert         Hash-chain
        │           Recommendation Signature
        │
        ▼
Bank / Telecom / Enterprise
```

This directly fulfils the PS requirement for APIs/SDKs and integration into banking, enterprise communication and telecom environments.

---

## 20. Traceability to the problem statement

| PS requirement | Final architecture |
|---|---|
| Real-time audio | Phase I + WebSocket/stream ingestion |
| Telephony | SIP/RTP adapter |
| VoIP | WebRTC/SIP adapter |
| Collaboration platforms | SDK/audio adapter |
| Synthetic speech | E1/E2/E3 |
| Acoustic artefacts | E1 |
| Spectral signatures | E1 |
| Raw waveform patterns | E2 |
| Neural synthesis patterns | E3 |
| Speaker identity | E4 |
| Prosody | E5 |
| Replay | E6 |
| Cross-session consistency | E4 + session/reference store |
| Dynamic risk | Phase III |
| Context | Phase IV |
| Caller metadata | Context service |
| Transaction context | Context service |
| Fraud indicators | Context service |
| Real-time alerts | Phase V + event stream |
| Secondary verification | Phase IV |
| MFA | action adapter |
| Callback | action adapter |
| Supervisor escalation | action adapter |
| High-value transaction protection | transaction tiers |
| Privacy | Phase V |
| Minimal audio retention | privacy lifecycle |
| Edge inference | deployment profile |
| Feature-only logging | evidence architecture |
| REST API | API layer |
| gRPC | internal/enterprise integration where required |
| SDK | SDK layer |
| Indian languages | SSL + language layer |
| Indian accents | data/training/evaluation strategy |
| Code switching | I.6 + III.5 |
| Partial spoof | frame logits + III.4 |
| Explainability | V.1 |
| Compliance evidence | V.2 |
| Feedback | V.4 |
| Drift | V.5 |
| Scalability | stateless I/II/IV + scalable workers |
| Deployment | Docker → Kubernetes progression |

The five-phase structure establishes the same end-to-end mapping: intake, independent analysis, fusion, contextual decision and assurance.

---

## 21. Production-grade versus prototype-grade

This distinction must be explicit.

| Capability | Internal SIH | Production |
|---|---|---|
| Audio source | WAV/mic | SIP/RTP/WebRTC/enterprise |
| Redis | single node | HA/cluster |
| DB | SQLite | PostgreSQL HA |
| ML | selected real models | trained/validated model suite |
| GPU | optional | inference pool |
| Language | selected Indic languages | expanded validated set |
| CNAP | simulated adapter | telecom integration |
| Transaction | simulator | banking API |
| Evidence | JSON/hash chain | signed immutable store |
| Privacy | local buffers | governed retention |
| Monitoring | basic metrics | full observability |
| MLOps | manual | registry + automated pipeline |
| Deployment | Docker Compose | Kubernetes |
| Security | local auth | enterprise IAM |
| Testing | fixtures | full adversarial evaluation |

---

## 22. The final architectural contract

> **No developer or AI agent may modify the five phase boundaries, cross-phase contracts, model roles, or decision semantics without first modifying the architecture specification and obtaining review.**

And:

> **No score may be fabricated to make the demo work.**

If a model isn't available → `MODEL_UNAVAILABLE`
If audio is insufficient → `UNCERTAIN`
If the speaker is not enrolled → `E4 = ABSTAIN`
If codec identification is uncertain → `codec = UNKNOWN`

Those behaviours are much more credible than silently inventing values. Graceful abstention, uncertainty handling and honest disclosure of limitations are required.

---

## 23. The five-phase master architecture in one diagram

```text
╔══════════════════════════════════════════════════════════════════════╗
║                         SYMPHONY                                     ║
║          REAL-TIME VOICE SECURITY & IMPERSONATION DEFENSE            ║
╚══════════════════════════════════════════════════════════════════════╝

 CALL / AUDIO SOURCE
        │
        ▼
┌──────────────────────────────────────────────────────────────────────┐
│ I — INTAKE "LISTEN"                                                  │
│                                                                      │
│ Stream Gateway → Channel Profile → Quality → VAD → Turns → Language  │
│                                                                      │
│                         FrameObject Fₜ                               │
└────────────────────────────────┬─────────────────────────────────────┘
                                 │
                           Redis Streams
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│ II — ANALYSIS "SCORE"                                                │
│                                                                      │
│ E1 Spectral   E2 Raw   E3 SSL   E4 Speaker   E5 Prosody   E6 Replay  │
│                                                                      │
│                      EvidenceVector Eₜ                               │
└────────────────────────────────┬─────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│ III — FUSION "HARMONY"                                               │
│                                                                      │
│ Quality Weight → Calibration → Belief Accumulation → Localisation    │
│                     → Code-Switch Guard → Uncertainty                │
│                                                                      │
│                       VoiceBelief Vₜ                                 │
└────────────────────────────────┬─────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│ IV — DECISION "CONDUCTOR"                                            │
│                                                                      │
│ Voice Belief + Caller + Number + Transaction + Behaviour + Device    │
│                         ↓                                            │
│              Risk Model + Tier + Policy + State Machine              │
│                         ↓                                            │
│              ALLOW / WARN / VERIFY / HOLD / ESCALATE                 │
└────────────────────────────────┬─────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│ V — ASSURANCE "CODA"                                                 │
│                                                                      │
│ Explain → Evidence → Privacy → Feedback → Drift → Recalibration      │
│                                                                      │
│                         EvidenceRecord                               │
└────────────────────────────────┬─────────────────────────────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              ▼                  ▼                  ▼
         HUMAN UI            SYSTEM API          AUDIT/MLOPS
         Dashboard           Banking             Evidence
         Alerts              Telecom             Feedback
         Recommendations     Enterprise          Drift
```

This is the frozen master architecture. It preserves the existing work rather than replacing it, while filling the gaps that appear when an implementation team tries to turn Symphony into an actual product: source adapters, API boundaries, security, persistence, model lifecycle, observability, deployment profiles, action adapters, data governance, MLOps and operational failure handling.

It still obeys the original architectural insight: **five phases, concurrent execution, two clocks, independent forensic experts, evidence accumulation, contextual decisioning, and an assurance loop — not one giant "deepfake classifier."**

And the single most important engineering priority stands: **get one complete end-to-end path running before expanding the system.**

---

# PART B — THE INTERNAL-ROUND IMPLEMENTATION

## 24. The winning principle

> **Build the smallest system that demonstrates the complete security story end-to-end, rather than the largest system that demonstrates isolated technical components.**

Do not attempt to build the entire production system for the internal round. Build a **small, exceptionally polished vertical slice** of it that makes the judges *feel* that the complete system already exists behind it.

**Product: VoiceShield — Real-Time Voice Integrity & Impersonation Defense**

The judge sees one scenario:

> **"The CFO is calling the finance employee and asking for an urgent ₹25 lakh transfer."**

---

## 25. The internal-round implementation subset

Despite the complete architecture above, implement this first:

```text
             MICROPHONE / WAV
                    │
                    ▼
               Phase I
                    │
               FrameObject
                    │
               Redis Stream
                    │
                    ▼
               Phase II
          ┌─────────┼─────────┐
          ▼         ▼         ▼
        E1/E2      E3        E4
          │         │         │
          └─────────┼─────────┘
                    ▼
               Phase III
                    │
          live risk trajectory
                    │
                    ▼
               Phase IV
                    │
            transaction tier
                    │
                    ▼
               Phase V
                    │
          explanation + audit
                    │
                    ▼
               React UI
```

The other components are **adapters or future deployment implementations, not architectural omissions.**

---

## 26. The demo pipeline (five-layer executable form)

```text
                 DEMO AUDIO SOURCE
          ┌──────────────────────────┐
          │ Genuine / AI-cloned call │
          │ WAV / microphone stream  │
          └────────────┬─────────────┘
                       ↓
              ┌─────────────────┐
              │ 1. INTAKE       │
              │ Audio stream    │
              │ VAD             │
              │ Quality         │
              │ Segmentation    │
              └────────┬────────┘
                       ↓
              ┌─────────────────┐
              │ 2. EVIDENCE     │
              │ DSP features    │
              │ Spectral model  │
              │ SSL model       │
              │ Speaker model   │
              │ Prosody         │
              └────────┬────────┘
                       ↓
              ┌─────────────────┐
              │ 3. VOICE BELIEF │
              │ Authenticity    │
              │ Spoof score     │
              │ Speaker match   │
              └────────┬────────┘
                       ↓
              ┌─────────────────┐
              │ 4. RISK ENGINE  │
              │ Voice + Context │
              │ Transaction     │
              │ Caller metadata │
              └────────┬────────┘
                       ↓
              ┌─────────────────┐
              │ 5. RESPONSE     │
              │ Risk: 91%       │
              │ HIGH RISK       │
              │ STOP / VERIFY   │
              └─────────────────┘
                       ↓
        ┌──────────────┼──────────────┐
        ↓              ↓              ↓
   Security UI     Transaction     Alert
                   simulator       / escalation
```

That is **the entire PS in miniature.** This preserves the Symphony-style conceptual structure while making the demo executable.

### 26.1 Expanded demo layer specification

```text
┌───────────────────────────────────────────────────────────────┐
│                    DEMO AUDIO SOURCE                          │
│ WAV / prerecorded call / microphone stream                    │
└──────────────────────────────┬────────────────────────────────┘
                               ▼
┌───────────────────────────────────────────────────────────────┐
│ LAYER 1 — AUDIO INGESTION                                     │
│ Audio loader / streamer · Chunking · Timestamping             │
│ Buffering · WebSocket stream · VAD · Audio-quality estimation │
└──────────────────────────────┬────────────────────────────────┘
                               ▼
┌───────────────────────────────────────────────────────────────┐
│ LAYER 2 — SIGNAL PROCESSING                                   │
│ Resampling · Normalization · Spectrogram · Log-mel features   │
│ MFCC · Pitch / F0 · Energy · Pause / speaking-rate features   │
│ Prosody features                                              │
└──────────────────────────────┬────────────────────────────────┘
                               ▼
┌───────────────────────────────────────────────────────────────┐
│ LAYER 3 — ML / VOICE EVIDENCE                                 │
│ Anti-spoofing model · Speaker embedding / verification        │
│ Acoustic analysis · SSL representation · Prosodic analysis    │
│ Temporal evidence                                             │
└──────────────────────────────┬────────────────────────────────┘
                               ▼
┌───────────────────────────────────────────────────────────────┐
│ LAYER 4 — VOICE BELIEF + CONTEXTUAL RISK                      │
│ Evidence fusion · Speaker consistency · Synthetic probability │
│ Caller metadata · Transaction value · Beneficiary novelty     │
│ Behavioural/context risk · Confidence / uncertainty           │
│ Temporal smoothing                                            │
└──────────────────────────────┬────────────────────────────────┘
                               ▼
┌───────────────────────────────────────────────────────────────┐
│ LAYER 5 — DECISION / RESPONSE                                 │
│ LOW / MEDIUM / HIGH / CRITICAL                                │
│ Continue · Warn · Step-up verification · Hold transaction     │
│ Escalate                                                      │
└──────────────────────────────┬────────────────────────────────┘
                               │
                 ┌─────────────┼──────────────┐
                 ▼             ▼              ▼
          Security UI    Transaction UI   Notification
```

---

## 27. What the judge should actually experience

**Do not start by showing architecture diagrams. Start with a scenario.**

### Screen 1 — "Incoming call"

```text
INCOMING CALL

Arjun Mehta — Chief Financial Officer

Registered contact
High-value transaction request
₹25,00,000
Beneficiary: New Account

Live analysis active
```

Then show the audio waveform moving. Underneath, the system begins populating:

```text
VOICE INTEGRITY

Acoustic Analysis       ████████░░  82%
Prosody Analysis        ███████░░░  76%
Speaker Consistency     █████████░  89%
Synthetic Speech        █████████░  91%
```

**Don't make the screen immediately say FAKE. Let the evidence accumulate.**

### The killer moment — the risk score evolves

```text
00:04       Risk 18%     LOW
00:07       Risk 31%     LOW
00:11       Risk 54%     MEDIUM
00:15       Risk 73%     HIGH
00:18       Risk 91%     CRITICAL
```

The judge sees: *the system isn't simply classifying a recording, it is continuously evaluating a live security event.* This directly supports the PS's requirement for dynamic, near-real-time risk scoring.

### Then expose the reason — "Why is this risky?"

```text
DETECTION EXPLANATION

✓ Speech stream successfully analyzed

⚠ Synthetic speech characteristics
  detected in spectral representation

⚠ Prosody deviation
  unusual pitch/pausing pattern

⚠ Speaker inconsistency
  current embedding differs from
  registered speaker profile

⚠ High-risk transaction context

⚠ New beneficiary

──────────────────────────────

Overall impersonation risk
                    91%

Confidence
                    HIGH
```

You are not saying *"Our AI says it's fake."* You are saying: **"Our system reached this security decision because these independent signals collectively indicate elevated risk."** That is much more defensible.

### Then trigger the actual security response — the climax

```text
CRITICAL — POSSIBLE VOICE IMPERSONATION

Do not authorize the transaction based solely on this call.

Recommended verification

[ CALL REGISTERED NUMBER ]

[ REQUEST MFA ]

[ ESCALATE TO SUPERVISOR ]
```

And the simulated transaction system changes:

```text
TRANSACTION STATUS

₹25,00,000

████████████████████

STATUS:
      ⛔ ON HOLD

Reason:
VOICE IMPERSONATION RISK
```

That one interaction demonstrates **Detection → Risk → Decision → Prevention**, which is far more powerful than showing an ML accuracy number.

### The full demo story

```text
Incoming audio → Audio ingestion → Signal processing → Multiple ML analyses
   → Voice belief → Contextual risk engine → 91% impersonation risk
   → CRITICAL ALERT → Transaction placed ON HOLD
   → Employee prompted for secondary verification
```

Then the same workflow with a genuine voice:

```text
Genuine call → 8% risk → LOW → No intervention
```

Complete story: **detect → explain → score → intervene → prevent.**

---

## 28. Real versus controlled — the hybrid architecture

For the internal round, use a hybrid architecture. Not fake. Not fully production-grade. **A real ML-backed system with controlled demo orchestration.**

**Real:** actual audio ingestion · actual audio preprocessing · actual feature extraction · actual anti-spoofing model · actual speaker embedding · actual risk calculation · actual WebSocket streaming · actual frontend · actual backend APIs

**Controlled:** curated demo recordings · predefined transaction context · limited supported audio formats · local/demo deployment · deterministic scenario orchestration · a small set of languages/accent samples

This gives credibility without burning the entire development window.

---

## 29. Deliberately avoiding real telecom integration

For the internal round, don't spend time on `PSTN → SIP carrier → PBX → RTP → AI`. Instead:

```text
                  DEMO MODE

WAV / microphone
       ↓
Audio Stream Simulator
       ↓
WebSocket
       ↓
Your actual ingestion layer
       ↓
Actual ML
       ↓
Actual risk engine
       ↓
Actual dashboard
```

The architecture remains compatible with future SIP/RTP ingestion. The explanation to judges:

> **"For the internal prototype, the telephony boundary is simulated using a real-time audio stream. The ingestion interface is deliberately decoupled from the detection pipeline so that the same backend can later accept SIP/RTP or enterprise communication streams."**

That is a technically sound answer, and it makes the scope limitation sound like what it actually is: **a deliberate prototype boundary, not an accidental missing feature.**

---

## 30. Internal-round repository structure

Make the repository itself reflect the architecture.

```text
voiceshield/
│
├── frontend/
│   ├── dashboard/
│   ├── components/
│   ├── charts/
│   └── websocket/
│
├── backend/
│   ├── api/
│   ├── websocket/
│   ├── session/
│   └── risk/
│
├── ingestion/
│   ├── audio_stream.py
│   ├── vad.py
│   ├── buffering.py
│   └── quality.py
│
├── signal_processing/
│   ├── preprocessing.py
│   ├── spectrogram.py
│   ├── mfcc.py
│   └── prosody.py
│
├── models/
│   ├── spoof_detector/
│   ├── speaker_verifier/
│   ├── prosody_model/
│   └── fusion/
│
├── context/
│   ├── caller.py
│   ├── transaction.py
│   └── reputation.py
│
├── decision/
│   ├── risk_engine.py
│   ├── thresholds.py
│   └── actions.py
│
├── demo/
│   ├── scenarios/
│   ├── audio/
│   └── simulator.py
│
├── tests/
│
├── docs/
│   ├── architecture.md
│   └── demo-script.md
│
└── docker-compose.yml
```

Major advantage: **when a judge asks "where is the ML?" you can literally navigate to it.**

### 30.1 Final demo-day folder (after the full agent build program)

```text
VoiceShield/
│
├── frontend/
│
├── backend/
│   ├── api/
│   ├── ingestion/
│   ├── signal_processing/
│   ├── models/
│   ├── evidence/
│   ├── speaker/
│   ├── context/
│   ├── risk/
│   ├── decision/
│   └── demo/
│
├── tests/
│
├── demo/
│   ├── audio/
│   ├── scenarios/
│   └── recordings/
│
├── docs/
│   ├── PS.md
│   ├── ARCHITECTURE.md
│   ├── EXECUTABLE_ARCHITECTURE.md
│   ├── EXECUTION_TECH_STACK.md
│   ├── DEMO_SCOPE.md
│   ├── DEMO_SCENARIOS.md
│   ├── QA_FINDINGS.md
│   ├── JUDGE_REVIEW.md
│   └── FINAL_REHEARSAL.md
│
├── scripts/
│
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

---

## 31. Internal-round technology stack

Don't over-engineer it.

| Component | Choice |
|---|---|
| Frontend | **React + TypeScript + Vite** |
| UI | **Tailwind CSS + shadcn/ui** |
| Charts | **Recharts** |
| Backend | **Python + FastAPI** |
| Real-time | **WebSockets** |
| Audio | **FFmpeg + librosa + soundfile** |
| DSP | **NumPy + SciPy** |
| ML | **PyTorch** |
| Speaker verification | **SpeechBrain / ECAPA-TDNN** |
| Anti-spoofing | **AASIST or suitable pretrained anti-spoof model** |
| Audio representation | **log-mel spectrogram + SSL embeddings** |
| Database | **SQLite for internal demo** |
| Production-shaped API | **REST + WebSocket** |
| Packaging | **Docker Compose** |
| Testing | **pytest + Playwright** |
| Version control | **Git + GitHub** |

The critical point: **don't build a distributed Kubernetes monster for an internal college round.** Make the architecture *production-shaped* while keeping the implementation compact.

### 31.1 Preferred execution stack for the agent build (unless a concrete compatibility issue requires a change)

**Frontend:** React · TypeScript · Vite · Tailwind CSS · shadcn/ui · Recharts
**Backend:** Python · FastAPI · Uvicorn · Pydantic
**Realtime:** WebSocket
**Audio:** FFmpeg · librosa · soundfile · NumPy · SciPy
**ML:** PyTorch · SpeechBrain where useful · an appropriate anti-spoofing implementation/model
**Testing:** pytest · Playwright
**Storage:** SQLite for demo persistence
**Packaging:** Docker Compose where practical

The stack must remain simple enough for a student team to run locally. For every dependency specify: purpose · version policy · installation method · whether mandatory · whether GPU required · whether internet required · licensing considerations · fallback if unavailable. **Do not invent package versions** — if a library/model/version cannot be verified from the environment or official documentation, mark it as requiring verification rather than guessing.

---

## 32. The dashboard — only four major areas

Don't turn it into an aircraft cockpit.

**Header:** VOICEGUARD — *Real-Time Voice Integrity & Impersonation Defense*
**Main card:** Current call — caller / duration / language / transaction
**Center:** Huge — `91%` · **CRITICAL IMPERSONATION RISK**
**Lower section:** Four evidence cards — **Acoustic | Prosody | Speaker | Context** — and a timeline:

```text
00:04  Audio received
00:07  Synthetic artifact detected
00:11  Speaker inconsistency detected
00:15  High-risk transaction identified
00:18  Risk crossed critical threshold
00:19  Transaction placed on hold
```

That's enough.

### 32.1 Full panel specification (for the frontend build)

```text
HEADER
VoiceShield
Real-Time Voice Integrity & Impersonation Defense
Live status indicator

CALL PANEL
Caller · Number · Call duration · Language · Call source · Transaction context

CENTRAL RISK PANEL
Large risk score · Risk band · Confidence · Current action

EVIDENCE PANEL
Acoustic · Synthetic speech · Speaker consistency · Prosody · Audio quality

TIMELINE
Live event stream

TRANSACTION PANEL
Amount · Beneficiary · Status · Security action

RECOMMENDATION PANEL
Human-readable recommended action
```

**Design principles:** dark professional security-console aesthetic · restrained typography · strong hierarchy · minimal clutter · excellent spacing · clear status colors · responsive layout · accessible contrast · subtle animation only where useful · no unnecessary gradients · no decorative elements that distract from the security decision.

Create a clear visual distinction between `LOW` · `MEDIUM` · `HIGH` · `CRITICAL` · `UNCERTAIN`.
**Do not hardcode demo values.** All displayed values must come from backend state, over WebSocket, updating without page refresh.

---

## 33. The multilingual-India requirement, made visible

Don't merely write "supports Indian languages." Have the UI show:

```text
LANGUAGE DETECTED

Hindi
Marathi
Indian English

Code-switching detected
```

For the demo, use Hindi/Marathi/Indian English samples if you have reliable audio. Don't claim *"we support every Indian language."* Instead:

> **"The architecture is language-agnostic at the feature layer, with language-specific models that can be expanded progressively."**

---

## 34. The privacy moment

A tiny but very effective panel:

```text
PRIVACY MODE

Raw audio retention       OFF
Feature logging           ON
Speaker embedding         EPHEMERAL
Audit event               STORED

✓ Audio processed locally
✓ Raw recording discarded
✓ Only security evidence retained
```

This directly connects to the PS's privacy requirement.

---

## 35. Demo scenarios

### 35.1 The two-call comparison — highest-value visual

**Scenario A — Genuine executive**

```text
CEO voice → Analysis → Risk: 8% → GREEN → Transaction proceeds
```

**Scenario B — AI-cloned executive**

```text
Cloned CEO voice → Analysis → Risk: 91% → RED → Transaction blocked
```

Then put them side-by-side:

| | Genuine | Impersonation |
|---|---:|---:|
| Acoustic | Normal | Suspicious |
| Prosody | Consistent | Deviant |
| Speaker | Match | Mismatch |
| Context | Normal | High risk |
| **Overall risk** | **8%** | **91%** |
| **Action** | Proceed | **Verify** |

### 35.2 The three frozen scenarios

**Scenario 1 — Genuine:** CFO · ₹25 lakh · known beneficiary · genuine voice → Risk `LOW` → Action `ALLOW`

**Scenario 2 — Full voice clone:** CFO · ₹25 lakh · new beneficiary · synthetic voice → Risk `HIGH/CRITICAL` → Action `HOLD + ESCALATE`

**Scenario 3 — Partial spoof:**

```text
human conversation
       ↓
synthetic transaction instruction
       ↓
human conversation
```

The UI identifies:

```text
Synthetic segment:
41.2s – 44.6s
```

**That is the demo to make the centrepiece.**

*(For the agent-built demo scenario engine, the third scenario is defined as an uncertain/poor-audio case producing `UNCERTAIN / STEP-UP VERIFICATION` — see the prompts document. Both are valid third scenarios; pick one as the built default and keep the other as the stretch target.)*

---

## 36. Judge mode / demo control

Build this. Put a small **DEMO CONTROL** button somewhere unobtrusive. It opens:

```text
SELECT ATTACK SCENARIO

○ Genuine Executive Call

● AI Voice Clone
  └── High-value transaction

○ Poor-quality call
  └── Uncertain classification

○ Speaker mismatch
```

Then: **START SIMULATION** — and the entire system runs.

This protects against the nightmare scenario: *"the model didn't detect it during the live demo."* **You aren't faking the ML result; you're controlling the input scenario so the demo remains reproducible.**

The scenario engine must **not** directly set the risk score. It may only select the audio fixture, provide context, provide transaction context, and start the session. **The real pipeline must produce the result.**

Display in the UI:

```text
DEMO MODE
This environment uses controlled test audio and simulated transaction context.
```

---

## 37. Playwright — the demo reliability weapon

Not an AI coding tool. Use it to automatically verify:

```text
Open dashboard
       ↓
Start genuine call
       ↓
Verify GREEN
       ↓
Start cloned call
       ↓
Verify risk rises
       ↓
Verify RED alert
       ↓
Verify transaction becomes HOLD
```

Then you aren't discovering a broken demo **in front of the judges.**

---

## 38. Presentation sequences

### 38.1 The five-and-a-half-minute version

Give the judges **zero technical explanation initially.**

**0:00–0:30 — Problem**
> "Today, hearing your CEO's voice is no longer proof that you're actually speaking to your CEO."

Immediately show the incoming call.

**0:30–1:15 — Genuine call** — Risk **8% — LOW** — transaction proceeds.

**1:15–2:00 — Attack** — same executive, same request, cloned voice. Risk starts increasing.

**2:00–2:30 — Detection** — **91% — CRITICAL.** Explain: acoustic anomaly · prosodic anomaly · speaker mismatch · contextual risk.

**2:30–3:00 — Prevention** — Transaction: **₹25,00,000 → ON HOLD**

**3:00–4:00 — Architecture** — now reveal:

```text
INGEST → PROCESS → DETECT → VERIFY → SCORE → ACT
```

**4:00–5:00 — Technical credibility** — DSP · anti-spoofing · speaker embeddings · contextual risk · real-time WebSocket architecture · privacy · multilingual design · API-first integration.

**5:00–5:30 — Future**
> "Today's prototype uses a controlled real-time audio stream. The same ingestion contract is designed to accept SIP/RTP, VoIP and enterprise communication streams."

### 38.2 The compressed three-minute version

Rehearse until nobody on the team needs to think about which button to press.

**00:00** — *"This is a voice impersonation attack."* Show incoming CFO call.
**00:15** — Audio begins streaming. *"The system doesn't trust caller ID or voice familiarity. It continuously analyzes the call."*
**00:30** — Show evidence accumulating: **Acoustic → Prosody → Speaker → Context**
**00:50** — Risk climbs: **18 → 37 → 61 → 84 → 91**
**01:10** — RED: **CRITICAL — POSSIBLE VOICE IMPERSONATION**
**01:20** — Transaction: **₹25,00,000 — ON HOLD**
**01:30** — Show explanation: synthetic speech indicators · speaker inconsistency · high-risk transaction context
**01:50** — Run genuine call: **Risk: 8% — LOW.** Transaction proceeds.
**02:10** — Now explain:
> "The important distinction is that this isn't merely an AI deepfake classifier. The detector produces evidence, the evidence becomes a voice belief, and the decision engine combines that with the action being requested."

**02:30** — Show architecture:

```text
INGEST → PROCESS → ANALYZE → VERIFY → SCORE → ACT
```

**02:45** — End with:
> **"The internal prototype uses controlled real-time audio rather than a live telecom carrier. The ingestion boundary is deliberately separated from the detection and decision pipeline, allowing the same security engine to later accept SIP/RTP, VoIP, enterprise communication and telecom streams."**

---

## 39. What NOT to build for the internal round

Just as important. Do **not** spend the internal-round week building:

Android + iOS apps · real telecom carrier integration · complete banking integration · Kubernetes · microservices everywhere · distributed GPU inference · full SIEM integration · 15-language support · custom deepfake model from scratch · production-grade authentication infrastructure · actual financial transaction execution · elaborate admin panels

Those belong to the **Grand Finale / production architecture**, not the internal proof.

---

## 40. What you should actually have at the end

```text
                  VOICESHIELD
        Real-Time Voice Integrity Platform

                      │
                Start Call
                      │
                      ▼
              ┌──────────────┐
              │ Audio Stream │
              └──────┬───────┘
                     ↓
                REAL ML PIPELINE
                     ↓
             ┌───────────────┐
             │ Risk: 91%     │
             │ CRITICAL      │
             └───────┬───────┘
                     ↓
          ┌───────────────────────┐
          │ POSSIBLE IMPERSONATION│
          └──────────┬────────────┘
                     ↓
             TRANSACTION HOLD
                     ↓
             SECONDARY VERIFY
```

And behind that polished interface:

**React → WebSocket → FastAPI → Audio Pipeline → DSP → ML Models → Evidence Vector → Voice Belief → Context → Risk Engine → Action API**

That is the **smallest demo worth putting in front of SIH judges.**

You're not building a flashy frontend *pretending* to be a voice-security system. You're building a **real, narrow vertical slice of the architecture**, then presenting it as the first executable manifestation of the larger system. That gives the best ratio of **technical credibility : visual impact : implementation time : judge comprehensibility.**

---

## 41. The next execution step

Do not give an agent the architecture and immediately say "build everything."

The next artifact should be a **machine-executable implementation specification** containing:

- exact repository tree
- exact Python/TypeScript module boundaries
- every Pydantic schema
- every Redis Stream
- every API endpoint
- every WebSocket event
- every model interface
- every database table
- every configuration variable
- every Docker service
- every test
- every demo fixture
- exact startup/shutdown behaviour
- failure/abstention semantics
- a dependency installation + verification matrix

The gated prompt sequence that produces this is in the companion document: **`VoiceShield_Agent_Build_Prompts.md`**.

# EXECUTABLE ARCHITECTURE — INTERNAL-ROUND DEMO

**Project:** SYMPHONY / VoiceShield — Real-Time Voice Integrity & Impersonation Defense
**Problem Statement:** SIH **26104**
**Scope:** Deployment **Profile A** (internal SIH, single machine) only.
**Status:** Specification. **No application code exists. This document writes none.**

---

## §0 — Purpose, authority and limits

### 0.1 What this document is

`SYMPHONY_REFERENCE.md` §41 requires a machine-executable implementation specification before any agent is told to build. This is that document, narrowed to the internal-round vertical slice defined by `docs/IMPLEMENTATION_READINESS.md` category **A**.

It defines boundaries, components, contracts, failure behaviour and test method precisely enough that implementation is transcription rather than invention.

### 0.2 What this document is NOT

- Not a production architecture. That is `SYMPHONY_REFERENCE.md` Part A and remains unchanged.
- Not a claim that anything is built. **Nothing is built.**
- Not a source of new requirements. Every element traces to `PS.txt`, `SYMPHONY_REFERENCE.md`, or the readiness report.
- Not permission to alter frozen terminology, phase boundaries or contracts (§22 of the reference).

### 0.3 Honesty constraints (unchanged, still binding)

No accuracy figure, dataset name, benchmark, telecom integration, or banking integration is claimed anywhere. No library version is stated — the readiness report marks all as `REQUIRES VERIFICATION`. Per §22:

> **No score may be fabricated to make the demo work.**

### 0.4 Ambiguities adopted here, pending sign-off

The readiness report §10 listed open questions. To make this document executable, the recommended resolutions are **adopted provisionally** and marked. Reversing any of them is a documented spec change, not a code change.

| Ref | Adopted | Status |
|---|---|---|
| §10.1 | Product name **VoiceShield** | Pending sign-off |
| §10.2 | Two band vocabularies are **different objects**: `VoiceBelief.band` (voice evidence) vs `Decision.risk_band` (voice + context) | Pending sign-off |
| §10.3 | `ContextVector` **frozen here** — §6.4 | **Resolved by this document** |
| §10.4 | WebSocket event set **frozen here** — §8 | **Resolved by this document** |
| §10.5 | E5 computes features, emits `ABSTAIN`; E6 absent, emits `ABSTAIN` | Pending sign-off |
| §10.6 | `PS.txt` retained; `docs/PS.md` to be a repaired copy | Pending |
| §10.7 | **Redis retained** — P3 is a locked principle | Adopted |
| §10.8 | Repository tree **§30.1** (backend/-nested) | Pending sign-off |
| §10.9 | Scenario 3 = poor audio → `UNCERTAIN` → `STEP_UP` | **Decided** |
| — | `Decision` contract **frozen here** — §6.5 | **Resolved by this document** |

---

## §1 — System boundaries

### 1.1 The boundary diagram

```text
╔══════════════════════════════════════════════════════════════════════════╗
║                        OUTSIDE THE SYSTEM                                ║
║                                                                          ║
║   Real telephony (PSTN/SIP/RTP)   ·   Real VoIP carriers                 ║
║   Real banking / core banking     ·   Real fund movement                 ║
║   Real SMS / email / push gateways ·  Real MFA providers                 ║
║   Real CNAP / number-reputation feeds                                    ║
║   Real enrollment programme       ·   Model training infrastructure      ║
║                                                                          ║
║   NOT BUILT. NOT CONNECTED. NOT CLAIMED.                                 ║
╚══════════════════════════════════════════════════════════════════════════╝
                                    │
        ┌───────────────────────────┴───────────────────────────┐
        │            SIMULATION BOUNDARY (§12)                  │
        │  Replaced for the demo by adapters that supply        │
        │  INPUTS and absorb OUTPUTS — never scores.            │
        └───────────────────────────┬───────────────────────────┘
                                    │
╔═══════════════════════════════════▼══════════════════════════════════════╗
║                        INSIDE THE SYSTEM                                 ║
║                                                                          ║
║  L1 Audio Ingestion → L2 Signal Processing → L3 ML/Evidence              ║
║      → L4 Voice Belief + Contextual Risk → L5 Decision + Output          ║
║                                                                          ║
║  + REST API, WebSocket transport, SQLite storage, React console          ║
║  ALL REAL. ALL EXECUTED. NO HARDCODED VALUES.                            ║
╚══════════════════════════════════════════════════════════════════════════╝
```

### 1.2 Trust boundaries

| Boundary | Rule |
|---|---|
| Browser ↔ API | Untrusted client. All displayed state originates server-side. The browser may **start** a session and **select** a scenario; it may never submit a score, belief, risk or band. |
| API ↔ Analysis worker | Redis Streams. The only channel. `FrameObject` in, nothing back. |
| Analysis ↔ Decision worker | Redis Streams. `EvidenceVector` only. **Carries no PCM** — this is P2 enforced physically, not by convention. |
| System ↔ Simulator | The simulator is *inside* the process tree but *outside* the scoring path. §11 defines the enforced prohibition. |
| System ↔ Disk | Raw audio is never written to durable storage. §13. |

### 1.3 The replaceability guarantee (P1)

The demo audio source must be replaceable by SIP/RTP/VoIP ingestion **without rewriting L2–L5**. This is guaranteed structurally, not by intention:

```text
    WavFileSource ─┐
    MicrophoneSource ─┼──► AudioSource protocol ──► L1 pipeline ──► FrameObject ──► Redis
    WebSocketSource ─┘                                                    │
                                                                          │
    [future] SipRtpSource ──────────┘                          L2–L5 consume ONLY this
    [future] WebRtcSource ──────────┘                          and never import an
                                                               audio-source module.
```

Three enforced conditions:

1. **One protocol.** Every source implements the same `AudioSource` interface (§4, C-01). Adding SIP/RTP means adding one class.
2. **One exit.** L1 has exactly one output type, `FrameObject`. No source-specific field escapes; source identity survives only as the opaque `source_type` string.
3. **An import guard test.** No module in L2–L5 may import `soundfile`, `sounddevice`, any source adapter, or any transport library. Enforced by an automated test (§15.3), not by review.

**Consequence:** the SIP/RTP work is *one adapter plus jitter/packet-loss handling*, and the readiness report keeps it in category **D** (not built). The architecture is ready for it; the demo does not pretend to have it.

---

## §2 — Layer model

### 2.1 The two vocabularies and how they map

Both are frozen and neither may be renamed. They are **different decompositions of the same pipeline**, and confusing them is the most likely source of architectural drift.

- **Phases I–V** (`SYMPHONY_REFERENCE.md` §1–23) are the *contract* decomposition — they name the frozen objects.
- **Layers L1–L5** (§26.1) are the *execution* decomposition — they name the demo's build order.

```text
LAYER          PHASE            PRODUCES              PROCESS ROLE
────────────────────────────────────────────────────────────────────────
L1 Ingestion   Phase I          FrameObject           api
L2 Signal      Phase I tail /   FeatureBundle         analysis-worker
               Phase II front   (internal, not frozen)
L3 ML/Evidence Phase II         EvidenceVector        analysis-worker
L4 Belief+Risk Phase III        VoiceBelief           decision-worker
               + Phase IV front ContextVector, RiskAssessment
L5 Decision    Phase IV tail    Decision              decision-worker
               + Phase V        EvidenceRecord
```

**Note the non-alignment:** L4 spans Phase III entirely plus the context/risk-fusion front half of Phase IV; L5 covers the policy/state-machine tail of Phase IV plus all of Phase V. This is inherent to the source documents and is stated explicitly so no implementer "fixes" it by collapsing a boundary.

**`FeatureBundle` is an internal L2→L3 structure, not a frozen contract.** It is the only inter-component object in this document that may be changed without a §22 review, because it never crosses a phase boundary.

### 2.2 Layer isolation rules

| Rule | Statement | Enforcement |
|---|---|---|
| **I1** | L2–L5 never touch a transport or source library | Import guard test (§15.3) |
| **I2** | L4–L5 never touch PCM | `EvidenceVector` has no PCM field; the decision worker is a separate process that never reads the frame stream |
| **I3** | A layer consumes only the fields its input object declares (P2) | Pydantic models with `extra="forbid"`; contract tests |
| **I4** | No layer may import a layer above it | Import guard test (§15.3) |
| **I5** | The simulator may not write to any scoring field | Field-provenance test (§11.3) |

---

## §3 — Runtime architecture

### 3.1 Process topology

```text
┌───────────────────────────────────────────────────────────────────────┐
│  HOST (one machine — Profile A)                                       │
│                                                                       │
│  ┌─────────────┐        ┌──────────────────────────────────────────┐  │
│  │  browser    │◄──WS──►│  PROCESS 1: api                          │  │
│  │  React SPA  │◄─REST─►│  FastAPI + Uvicorn                       │  │
│  └─────────────┘        │  · REST surface                          │  │
│                         │  · WS /audio  (ingress)                  │  │
│                         │  · WS /events (egress relay)             │  │
│                         │  · L1 ingestion pipeline                 │  │
│                         │  · demo simulator (fixture+context only) │  │
│                         └───────┬──────────────────────────▲───────┘  │
│                                 │ XADD vs:frames           │ SUBSCRIBE│
│                                 ▼                          │          │
│                         ┌───────────────────────────────────────────┐ │
│                         │  REDIS  (streams + pubsub + session state)│ │
│                         │  · vs:frames      (PCM lives here, TTL)   │ │
│                         │  · vs:evidence    (NO PCM)                │ │
│                         │  · vs:events:{sid} (pubsub)               │ │
│                         │  · vs:session:{sid} (hash)                │ │
│                         └───────┬──────────────────────────▲────────┘ │
│                                 │ XREADGROUP vs:frames     │          │
│                                 ▼                          │          │
│                         ┌──────────────────────┐           │          │
│                         │  PROCESS 2:          │           │          │
│                         │  analysis-worker     │           │          │
│                         │  L2 + L3  (stateless)│           │          │
│                         │  → XADD vs:evidence  │           │          │
│                         └───────┬──────────────┘           │          │
│                                 │ XREADGROUP vs:evidence   │          │
│                                 ▼                          │          │
│                         ┌──────────────────────┐           │          │
│                         │  PROCESS 3:          │           │          │
│                         │  decision-worker     │───────────┘          │
│                         │  L4 + L5 (stateful)  │  PUBLISH events      │
│                         │  → SQLite            │                      │
│                         └───────┬──────────────┘                      │
│                                 ▼                                     │
│                         ┌──────────────────────┐                      │
│                         │  SQLite (file)       │                      │
│                         └──────────────────────┘                      │
└───────────────────────────────────────────────────────────────────────┘
```

### 3.2 Why three processes and why this is not microservices

The user constraint is explicit: no microservices without concrete benefit, no Kubernetes, no cloud. This topology complies.

**It is one codebase, one dependency set, one version, one image, one repository.** The three roles are **entrypoints into the same package**, selected by argument:

```text
python -m voiceshield api
python -m voiceshield analysis-worker
python -m voiceshield decision-worker
python -m voiceshield all-in-one     # dev/debug only, single process
```

They share models, contracts, config and logging. There is no per-service database, no service discovery, no independent deployment, no network API between them — only Redis, which the architecture already mandates.

**Concrete justification for each split:**

| Split | Justification | Source |
|---|---|---|
| api ↔ analysis | **P3 — "Capture never waits for ML."** Audio acquisition must not block on inference. This is a *locked principle*, not a preference. Without a process boundary, a slow forward pass stalls the WebSocket read loop. | P3, §3, §23 |
| analysis ↔ decision | Separates **stateless** heavy inference from **stateful** per-session belief accumulation. This is what makes I2 physically true (the decision worker never receives PCM) and is the honest basis for the "stateless workers scale" claim without building any scaling. | P2, §21 |

**`all-in-one` mode exists** so a developer can debug the full path under one debugger. It is **not** the demo run mode, because it cannot honour P3.

### 3.3 Scaling posture (stated, not built)

`analysis-worker` is stateless and could be replicated via the Redis consumer group. `decision-worker` holds per-session belief state and **runs as exactly one instance**; replicating it would require session-affinity partitioning, which is **not built and not claimed**. Profile A runs one of each.

---

## §4 — Components

Format for every component:
**Does · Does NOT · Input · Output · Consumed by · Failure behaviour · Test method**

Failure behaviour obeys §22: abstain, never invent.

---

### L1 — AUDIO INGESTION (Phase I, `api` process)

---

**C-01 `ingestion.source.AudioSource`** — source protocol
- **Does:** define the single interface every audio source implements: `open()`, `read_chunk() -> bytes|None`, `close()`, and static descriptors `source_type`, `native_sample_rate`, `channels`.
- **Does NOT:** decode, resample, buffer, detect speech, or know anything about sessions.
- **Input:** none (constructor config only).
- **Output:** raw byte chunks + descriptors.
- **Consumed by:** C-05, C-06.
- **Failure behaviour:** `open()` raises `SourceUnavailable`; the session enters `FAILED` with reason code `SOURCE_UNAVAILABLE`. No frames are emitted. **The UI shows the failure; it does not show a score.**
- **Test method:** protocol conformance test parameterised over all implementations; a `FakeSource` yielding a known sine sequence proves the contract without audio hardware.

**C-02 `ingestion.source.WavFileSource`**
- **Does:** read a WAV fixture and yield chunks **paced in wall-clock time** so the demo is a stream, not a batch job.
- **Does NOT:** loop, seek, transcode non-WAV formats, or normalise (that is C-07).
- **Input:** file path, chunk duration.
- **Output:** byte chunks at the file's native rate.
- **Consumed by:** C-05.
- **Failure behaviour:** missing/unreadable file → `SourceUnavailable(FIXTURE_MISSING)`.
- **Test method:** unit test asserting chunk count, ordering and elapsed-time pacing within tolerance.

**C-03 `ingestion.source.MicrophoneSource`**
- **Does:** capture from the host microphone.
- **Does NOT:** exist on the critical demo path. WAV fixtures are the reliable route (readiness R3).
- **Input:** device index, chunk duration.
- **Output:** byte chunks.
- **Consumed by:** C-05.
- **Failure behaviour:** no device / permission denied → `SourceUnavailable(NO_CAPTURE_DEVICE)`. **Must not crash the API process.**
- **Test method:** skipped-by-default integration test; unit test of the error path with a stubbed device layer.

**C-04 `ingestion.source.WebSocketSource`**
- **Does:** accept PCM chunks pushed by the browser over `WS /v1/sessions/{id}/audio`.
- **Does NOT:** trust client-declared sample rate without validation; accept any non-audio field.
- **Input:** binary WS frames + a declared audio header.
- **Output:** byte chunks.
- **Consumed by:** C-05.
- **Failure behaviour:** malformed header → close with `AUDIO_FORMAT_REJECTED`; mid-stream gap → emit frames with `packet_loss` set, **never interpolate invented audio**.
- **Test method:** WS integration test pushing a known buffer and asserting frame equivalence with `WavFileSource`.

**C-05 `ingestion.session.SessionManager`**
- **Does:** create/start/stop sessions; own session lifecycle state; bind exactly one `AudioSource` per session; allocate `session_id`; write session state to Redis and SQLite.
- **Does NOT:** compute anything about audio content; decide risk; outlive the process for in-flight audio.
- **Input:** session create request (§7), scenario selection (§11).
- **Output:** session record; lifecycle events.
- **Consumed by:** C-06, C-47, C-49.
- **Failure behaviour:** duplicate start → `409`; stop on unknown session → `404`; abrupt source death → session `FAILED`, terminal event published, **no synthesised final score**.
- **Test method:** state-machine unit tests over the legal lifecycle transitions.

**C-06 `ingestion.buffering.FrameAssembler`**
- **Does:** accumulate source chunks into fixed-duration frames with monotonic `frame_id`, `t_start`, `t_end`; apply the jitter buffer; track packet loss.
- **Does NOT:** resample, normalise, or classify.
- **Input:** byte chunks + source descriptors.
- **Output:** timestamped raw frames.
- **Consumed by:** C-07.
- **Failure behaviour:** underrun → emit a frame flagged with elevated `packet_loss` and reduced `q_t`; **never zero-pad silently and never fabricate continuity**.
- **Test method:** unit tests for exact framing boundaries, monotonicity, and underrun flagging.

**C-07 `signal_processing.preprocessing.Normaliser`**
- **Does:** decode to float PCM, downmix to mono, resample to the canonical rate, apply amplitude normalisation.
- **Does NOT:** denoise, enhance, or apply any transform that could mask synthesis artefacts. **This is a hard rule** — aggressive enhancement destroys the evidence L3 depends on.
- **Input:** raw timestamped frame.
- **Output:** canonical float PCM.
- **Consumed by:** C-08, C-09, C-10, C-13.
- **Failure behaviour:** unsupported rate/format → `FRAME_REJECTED`, frame dropped, counter incremented, session continues.
- **Test method:** golden-vector test — known input, asserted output rate/shape/range; explicit test that no spectral enhancement is applied.

**C-08 `ingestion.channel.ChannelProfiler`**
- **Does:** estimate `codec_vec`, `bandwidth`, `packet_loss` from the signal and source metadata.
- **Does NOT:** guess a codec when the source is a WAV file with no codec history.
- **Input:** canonical PCM + source descriptors.
- **Output:** channel descriptors.
- **Consumed by:** C-13, and via `EvidenceVector` by C-29 (weighting).
- **Failure behaviour:** **emits `codec = UNKNOWN`** per §22. For file input this is the *expected* value, not an error.
- **Test method:** assert `UNKNOWN` for file sources; assert bandwidth estimation on synthetic band-limited signals.

**C-09 `ingestion.quality.QualityEstimator`**
- **Does:** compute `q_t` ∈ [0,1] from SNR estimate, clipping ratio, effective bandwidth and level.
- **Does NOT:** decide anything about authenticity. Quality is *not* evidence of spoofing.
- **Input:** canonical PCM + channel descriptors.
- **Output:** `q_t` + component sub-scores.
- **Consumed by:** C-13; critically by C-29 and C-32 — **this is what makes Scenario 3 work.**
- **Failure behaviour:** on estimator error, `q_t = None` and downstream treats quality as unknown → widens uncertainty. Never defaults to a flattering value.
- **Test method:** monotonicity tests — added noise must lower `q_t`; clipped input must lower `q_t`; a degraded fixture must produce materially lower `q_t` than its clean counterpart.

**C-10 `ingestion.vad.VoiceActivityDetector`**
- **Does:** classify each frame `is_speech`.
- **Does NOT:** identify who is speaking; transcribe; decide language.
- **Input:** canonical PCM.
- **Output:** boolean + margin.
- **Consumed by:** C-13; L3 skips inference on non-speech frames.
- **Failure behaviour:** detector failure → `is_speech = True` (fail-open into analysis, which is the conservative direction for a *security* system) with a logged warning.
- **Test method:** unit test on speech/silence fixtures; assert non-speech frames do not reach the experts.

**C-11 `ingestion.turns.TurnSegmenter`** — diarisation-lite
- **Does:** mark `speaker_turn` index and `overlap_flag` using energy/pause heuristics.
- **Does NOT:** perform real speaker diarisation or identify speakers. **Naming it diarisation in the UI would be a production claim.**
- **Input:** canonical PCM + VAD output.
- **Output:** turn index, overlap flag.
- **Consumed by:** C-13.
- **Failure behaviour:** on failure, single-turn assumption with `overlap_flag = None`.
- **Test method:** unit test on a two-speaker fixture; assert turn index changes at the known boundary.

**C-12 `ingestion.language.LanguageTagger`**
- **Does:** populate `lang_t` and `switch_flag`.
- **Does NOT:** claim multilingual support. Readiness **B5**: no Indic fixtures exist and no validated language capability is claimed.
- **Input:** canonical PCM.
- **Output:** `lang_t` (defaults to `UNKNOWN`), `switch_flag` (defaults `False`).
- **Consumed by:** C-13; C-35 (deferred guard).
- **Failure behaviour:** **`lang_t = UNKNOWN` is the default and the honest state for this demo.** The UI language panel must render `UNKNOWN` rather than a plausible-looking guess.
- **Test method:** assert `UNKNOWN` is emitted when no tagger model is loaded; assert the UI renders that state.

**C-13 `ingestion.frame.FrameObjectAssembler`**
- **Does:** assemble the frozen `FrameObject` (§6.1) from all L1 outputs; validate it.
- **Does NOT:** add any field not in the frozen contract.
- **Input:** all C-07…C-12 outputs.
- **Output:** validated `FrameObject`.
- **Consumed by:** C-14.
- **Failure behaviour:** validation error → frame dropped, `FRAME_INVALID` logged and counted; **session continues**, because one bad frame must not end a call.
- **Test method:** contract test asserting field-for-field equality with §6.1 and rejection of extra fields.

**C-14 `ingestion.publisher.FramePublisher`**
- **Does:** `XADD` the `FrameObject` to `vs:frames` with `MAXLEN ~ N`, which **is** the short-lived raw-audio buffer (§13).
- **Does NOT:** wait for a consumer. P3.
- **Input:** `FrameObject`.
- **Output:** Redis stream entry.
- **Consumed by:** C-19 (analysis worker).
- **Failure behaviour:** Redis unavailable → session `DEGRADED`, `INGEST_BACKPRESSURE` event, capture continues and frames are dropped oldest-first. **Capture never blocks.**
- **Test method:** integration test asserting publish latency stays bounded while a deliberately slow consumer runs.

---

### L2 — SIGNAL PROCESSING (`analysis-worker`)

---

**C-15 `signal_processing.spectrogram.SpectralFeatures`**
- **Does:** compute STFT, log-mel, and LFCC representations.
- **Does NOT:** classify; cache across sessions; apply enhancement.
- **Input:** `FrameObject.pcm`.
- **Output:** feature arrays in `FeatureBundle`.
- **Consumed by:** C-20 (E1).
- **Failure behaviour:** computation error → `FeatureBundle.spectral = None` → **E1 abstains**. Does not abort the frame.
- **Test method:** golden-array test against fixed input; shape/dtype assertions.

**C-16 `signal_processing.cepstral.CepstralFeatures`**
- **Does:** compute MFCC and deltas.
- **Does NOT:** classify.
- **Input:** `FrameObject.pcm`.
- **Output:** `FeatureBundle.cepstral`.
- **Consumed by:** C-20, C-23.
- **Failure behaviour:** as C-15.
- **Test method:** golden-array test.

**C-17 `signal_processing.prosody.ProsodyFeatures`**
- **Does:** compute F0 contour, energy contour, pause distribution, speaking rate, turn latency, and jitter/shimmer where measurable.
- **Does NOT:** produce `p_beh`. Readiness **B1** — features are real; the calibrated score is deferred.
- **Input:** `FrameObject.pcm` + turn metadata.
- **Output:** `FeatureBundle.prosody`.
- **Consumed by:** C-24 (which abstains) and **the UI Prosody panel, explicitly labelled as descriptive features, not a verdict.**
- **Failure behaviour:** unvoiced/short frame → fields `None`, no error.
- **Test method:** F0 accuracy on a synthetic tone of known pitch; pause detection on a fixture with known silences.

**C-18 `signal_processing.bundle.FeatureBundle`**
- **Does:** carry L2 outputs to L3 for one frame; declare which representations are present.
- **Does NOT:** cross a phase boundary — **it is internal and not a frozen contract** (§2.1).
- **Input:** C-15…C-17.
- **Output:** itself.
- **Consumed by:** C-19.
- **Failure behaviour:** a `None` representation is legal and means "this expert must abstain".
- **Test method:** covered by expert abstention tests.

---

### L3 — ML / EVIDENCE GENERATION (Phase II, `analysis-worker`)

---

**C-19 `models.registry.ExpertRegistry` + `models.base.Expert`**
- **Does:** define the uniform expert interface — `expert_id`, `required_features`, `score(bundle) -> ExpertResult`; own registration, model loading and per-expert timeout enforcement.
- **Does NOT:** let one expert see another's output. **§6.1 of the reference: experts do not consume each other's outputs.**
- **Input:** `FeatureBundle`.
- **Output:** `list[ExpertResult]`.
- **Consumed by:** C-26.
- **Failure behaviour:** an expert that raises, times out, or has no weights returns `ExpertResult(status=MODEL_UNAVAILABLE, p=None, confidence=None)`. **One dead expert never kills the pipeline and never becomes a default probability.**
- **Test method:** an `ExplodingExpert` fixture must not break the run; a test asserts no expert's output appears in another's input signature.

**C-20 `models.e1_spectral`** — E1 spectro-temporal
- **Does:** run the AASIST-style model over spectral input; emit `p_spec`, `frame_logits_spec[]`, `confidence_spec`.
- **Does NOT:** decide, threshold, or accumulate over time. It is a per-frame evidence producer.
- **Input:** `FeatureBundle.spectral`.
- **Output:** `ExpertResult`.
- **Consumed by:** C-26.
- **Failure behaviour:** `MODEL_UNAVAILABLE` if weights absent — the **expected state until acquisition (readiness R1)**.
- **Test method:** deterministic-output test on a fixed tensor with a seeded stub; smoke test on a real fixture once weights exist. **No accuracy assertion** — no evaluation set exists.

**C-21 `models.e2_raw`** — E2 raw waveform
- **Does:** run the raw-waveform model on PCM; emit `p_raw`, `frame_logits_raw[]`, `confidence_raw`.
- **Does NOT:** consume spectral features or E1 output.
- **Input:** `FrameObject.pcm` via bundle.
- **Output:** `ExpertResult`.
- **Consumed by:** C-26.
- **Failure behaviour / Test:** as C-20.

**C-22 `models.e3_ssl`** — E3 SSL
- **Does:** run a frozen multilingual SSL backbone (WavLM/XLS-R-class), take **selected hidden layers**, run a lightweight probe → `p_ssl`.
- **Does NOT:** fine-tune the backbone; assume the final layer is optimal (§6.2 explicitly warns against this).
- **Input:** PCM via bundle.
- **Output:** `ExpertResult`.
- **Consumed by:** C-26.
- **Failure behaviour:** `MODEL_UNAVAILABLE`. This is the largest model and the most likely to breach the fast-clock budget → see §3, C-31.
- **Test method:** layer-selection config test; latency benchmark recorded, not asserted as a claim.

**C-23 `models.e4_speaker`** — E4 speaker verification
- **Does:** compute an ECAPA-style embedding for the current audio and cosine-compare it to the enrolled reference; emit `p_spk` and the raw similarity.
- **Does NOT:** act as another spoof classifier. §6.2: *"it answers a different question: is this actually the claimed person?"*
- **Input:** PCM via bundle + reference embedding from C-27.
- **Output:** `ExpertResult`.
- **Consumed by:** C-26.
- **Failure behaviour:** **no enrolled reference → `status = ABSTAIN`** per §22 (`E4 = ABSTAIN`). Not a low score, not a high score — an abstention.
- **Test method:** same-speaker pair scores higher than different-speaker pair on fixtures (a *relative* assertion, not an accuracy claim); abstention test with enrollment removed.

**C-24 `models.e5_prosody`** — E5 prosody/behaviour
- **Does:** accept prosody features and return `ExpertResult(status=DEFERRED, p_beh=None)`.
- **Does NOT:** produce a score. Readiness **B1**. §6.2 already calls it *"a weak supporting expert, never proof of human speech."*
- **Input:** `FeatureBundle.prosody`.
- **Output:** abstaining `ExpertResult`.
- **Consumed by:** C-26.
- **Failure behaviour:** always abstains by design — this **is** the behaviour, and it must be visible in the UI, not hidden.
- **Test method:** assert `p_beh is None` and that C-29 assigns it zero weight.

**C-25 `models.e6_replay`** — E6 replay/liveness
- **Does:** exist as a registered, abstaining expert so the contract field `p_rep` remains populated with an explicit status.
- **Does NOT:** score. Readiness **B2**.
- **Input / Output / Consumed by:** as C-24.
- **Failure behaviour:** always `DEFERRED`.
- **Test method:** assert the field exists and abstains; assert the contract was **not** shortened by removing it (§22).

**C-26 `evidence.assembler.EvidenceVectorAssembler`**
- **Does:** assemble the frozen `EvidenceVector` (§6.2) from all six `ExpertResult`s plus quality, codec, language, latency and model versions; publish to `vs:evidence`.
- **Does NOT:** weight, calibrate, fuse, threshold — **and does not include PCM** (I2).
- **Input:** `list[ExpertResult]` + `FrameObject` metadata.
- **Output:** `EvidenceVector`.
- **Consumed by:** C-28 (decision worker).
- **Failure behaviour:** if **every** expert abstains, still publishes with all probabilities `None` — L4 will then produce `UNCERTAIN`, which is the correct answer.
- **Test method:** contract test; **an explicit test that the serialised message contains no PCM field** — this is the physical proof of P2.

**C-27 `models.loader.ModelLoader` + `speaker.enrollment.EnrollmentStore`**
- **Does:** load model artefacts from local disk, verify checksums, record `model_versions[]`, hold the enrolled reference embedding.
- **Does NOT:** download at runtime. **Weights must be vendored locally (readiness R12) — the demo must cold-start offline.**
- **Input:** model directory, enrollment fixture.
- **Output:** loaded models, reference embedding.
- **Consumed by:** C-19…C-23.
- **Failure behaviour:** missing artefact → that expert is registered as `MODEL_UNAVAILABLE` and **the API startup log states plainly which experts are unavailable.** Startup does not silently proceed as if all six are live.
- **Test method:** startup test with an empty model directory asserting graceful degradation and an accurate availability report.

---

### L4 — VOICE BELIEF + CONTEXTUAL RISK (Phase III + Phase IV front, `decision-worker`)

---

**C-28 `fusion.calibration.Calibrator`**
- **Does:** map raw expert outputs to calibrated probabilities.
- **Does NOT:** claim to be fitted. **No calibration data exists (readiness §7.4)** — the shipped mapping is an identity/prior and must be labelled `CALIBRATION: PRIOR_ONLY` in logs and in `model_versions[]`.
- **Input:** `EvidenceVector`.
- **Output:** calibrated probabilities.
- **Consumed by:** C-29.
- **Failure behaviour:** unknown expert → pass through uncalibrated, flagged.
- **Test method:** monotonicity test (calibration must not invert ordering); a test asserting the `PRIOR_ONLY` flag is present.

**C-29 `fusion.weighting.QualityConditionedWeighting`**
- **Does:** compute `weight_i = f(q_t, codec_vec, expert_reliability)` per §8.1 — notably reducing reliance on bandwidth-dependent evidence for narrowband audio.
- **Does NOT:** use constant weights, and **does NOT average scores.** §8 forbids reducing fusion to `average(scores)` (readiness **R6**).
- **Input:** calibrated probabilities + `q_t` + `codec_vec` + expert statuses.
- **Output:** weight vector; abstaining/deferred experts receive weight `0`.
- **Consumed by:** C-30.
- **Failure behaviour:** all weights zero (every expert abstained) → signals C-30 to hold belief flat and C-32 to report maximal uncertainty.
- **Test method:** assert narrowband input lowers the weight of bandwidth-dependent experts; assert abstaining experts get exactly zero; **assert the function is not equal to a uniform mean** on a crafted input.

**C-30 `fusion.belief.TemporalBeliefEngine`**
- **Does:** implement §8.2 — `log O_t = decay(log O_(t-1)) + bounded evidence contribution`, `P_spoof = O / (1 + O)`; maintain `trajectory[]`.
- **Does NOT:** jump on a single frame (contributions are **bounded**); persist belief across sessions.
- **Input:** weighted calibrated evidence.
- **Output:** `P_spoof`, `trajectory[]`.
- **Consumed by:** C-32, C-33.
- **Failure behaviour:** gap in evidence → decay applies, belief drifts toward the prior. It does **not** freeze and does not reset.
- **Test method:** a sustained-evidence sequence must produce a **monotone-ish rising** trajectory (this is the §8.2 "12→19→31→44→61→78→91" behaviour); a single outlier frame must not spike the belief; a silence gap must decay it.

**C-31 `fusion.clocks.TwoClockScheduler`**
- **Does:** run the **fast clock (100–250 ms)** for provisional UI state and the **slow clock (1–3 s rolling window)** for action-grade decisions (§8.3).
- **Does NOT:** let a fast-clock value drive a `HOLD`/`ESCALATE`. §8.3: *"Do not pretend that a single instantaneous score is the final decision."*
- **Input:** belief updates.
- **Output:** two tagged streams — `provisional` and `action_grade`.
- **Consumed by:** C-33, C-40, C-46.
- **Failure behaviour:** if inference exceeds the fast budget (readiness **R2**), the scheduler **reduces which experts run on the fast clock** and marks affected updates `degraded_clock=True`. It **never** back-fills a missed tick with an invented value.
- **Test method:** timing test asserting action-grade decisions never derive from a single frame; degraded-mode test under an artificially slow expert.

**C-32 `fusion.uncertainty.UncertaintyEstimator`**
- **Does:** compute `confidence` separately from `P_spoof`, and set `uncertainty_reason` — from expert disagreement, abstention count, low `q_t`, and short observation window.
- **Does NOT:** conflate the two. **P4: low confidence means "we don't know", not "probably genuine."**
- **Input:** expert statuses, weights, `q_t`, elapsed speech duration.
- **Output:** `confidence`, `uncertainty_reason`.
- **Consumed by:** C-33.
- **Failure behaviour:** it is itself the failure-handling path; on internal error it returns minimum confidence with reason `UNCERTAINTY_ESTIMATOR_ERROR`.
- **Test method:** **the Scenario 3 test** — degraded audio must yield low confidence while `P_spoof` stays mid-range, and the band must be `UNCERTAIN`. A test asserts high-`P_spoof`/low-confidence and low-`P_spoof`/low-confidence render differently (P4).

**C-33 `fusion.belief.VoiceBeliefAssembler`**
- **Does:** assemble the frozen `VoiceBelief` (§6.3), including band assignment over `GENUINE | UNCERTAIN | SUSPICIOUS | SYNTHETIC_HIGH_CONFIDENCE`.
- **Does NOT:** force a binary verdict. §8.6: *"Do not force fake / real when the evidence does not justify it."* Does **not** know about transactions — that is L5's concern (P5).
- **Input:** C-30, C-32 outputs + `q_call`.
- **Output:** `VoiceBelief`.
- **Consumed by:** C-38, C-43, C-44, C-46.
- **Failure behaviour:** insufficient evidence → `band = UNCERTAIN`, never `GENUINE` by default.
- **Test method:** contract test; band-boundary tests; assert `spans[]` and `switch_damping_events[]` are present-but-empty (B3/B4 deferred, fields retained).

**C-34 `fusion.localisation.PartialSpoofLocaliser`** — **DEFERRED (B3)**
- **Does:** exist as a no-op returning `spans = []`.
- **Does NOT:** localise. §8.4: *"Do not claim a particular localisation resolution until measured."*
- **Failure behaviour:** always returns empty; the UI must not render a span panel implying capability.
- **Test method:** assert empty and that no UI element claims localisation.

**C-35 `fusion.codeswitch.CodeSwitchGuard`** — **DEFERRED (B4)**
- **Does:** exist as a pass-through returning `switch_damping_events = []`.
- **Does NOT:** damp. Requires language tagging that C-12 does not provide in this demo.
- **Test method:** assert pass-through and empty event list.

**C-36 `context.providers.*`** — identity, number, transaction, behaviour, technical
- **Does:** supply the five §9.1 context dimensions through a uniform `ContextProvider` interface, backed for this demo by the scenario definition.
- **Does NOT:** contact any real CNAP feed, reputation service, or bank. **Simulated — readiness S3/S4.** Does not touch audio.
- **Input:** `session_id`, scenario context.
- **Output:** context fields, each carrying `provenance = SIMULATED`.
- **Consumed by:** C-37.
- **Failure behaviour:** a missing field is `None` with `provenance = UNAVAILABLE`; it is **never defaulted to a benign value**, because a benign default silently lowers risk.
- **Test method:** assert every field carries provenance; assert `provenance != REAL` anywhere in this build.

**C-37 `context.assembler.ContextVectorAssembler`**
- **Does:** assemble the `ContextVector` (§6.4, **frozen by this document**).
- **Does NOT:** score or weight.
- **Input:** provider outputs.
- **Output:** `ContextVector`.
- **Consumed by:** C-38, C-44.
- **Failure behaviour:** validation failure → `CONTEXT_UNAVAILABLE`; risk fusion proceeds on voice evidence alone and the decision is flagged `context_degraded`.
- **Test method:** contract test; degraded-context test.

**C-38 `risk.fusion.RiskFusion`**
- **Does:** combine `VoiceBelief` and `ContextVector` into a `RiskAssessment` — `risk_score`, `risk_confidence`, and per-factor `contributions[]` (the §10.1 breakdown).
- **Does NOT:** decide the action. **P5 separation: this produces a number; C-40 decides.** Does not use XGBoost (readiness **B10** — deferred; the demo uses an explicit, inspectable weighted model).
- **Input:** `VoiceBelief` + `ContextVector`.
- **Output:** `RiskAssessment`.
- **Consumed by:** C-39, C-40, C-43.
- **Failure behaviour:** if `VoiceBelief.band == UNCERTAIN`, risk is computed **but** `risk_confidence` is capped, and C-40 is forbidden from issuing a confident `ALLOW`.
- **Test method:** assert contributions sum coherently to the score; assert identical voice evidence yields higher risk at tier 4 than tier 0 inputs.

---

### L5 — DECISION + OUTPUT (Phase IV tail + Phase V, `decision-worker`)

---

**C-39 `decision.tiers.TransactionSensitivity`**
- **Does:** map the requested action to tiers 0–4 and select the tier-conditioned threshold set. §9.2: **thresholds become more conservative as sensitivity rises.**
- **Does NOT:** infer the tier from audio content.
- **Input:** transaction context.
- **Output:** tier + threshold set.
- **Consumed by:** C-40.
- **Failure behaviour:** unknown transaction type → **tier 4 (most conservative)**. Fail-safe, not fail-open.
- **Test method:** assert threshold monotonicity across tiers; assert the unknown-type default is 4.

**C-40 `decision.policy.PolicyEngine`**
- **Does:** apply explicit, inspectable rules over `RiskAssessment` + tier + thresholds; emit the action class; carry `policy_version`.
- **Does NOT:** let a model have the final say. §9.3: *"it must not have the final say"* — *"This prevents an opaque model from directly deciding whether a financial transaction executes."*
- **Input:** `RiskAssessment`, tier, thresholds, state.
- **Output:** action + `reason_codes[]`.
- **Consumed by:** C-41.
- **Failure behaviour:** policy evaluation error → `STEP_UP` (safe middle), reason `POLICY_ERROR`. Never `ALLOW`.
- **Test method:** rule-table tests; **an audit test asserting no code path lets `RiskAssessment` alone select `ALLOW` at tiers 3–4 without passing the policy layer.**

**C-41 `decision.state.RiskStateMachine`**
- **Does:** enforce the §9.4 state graph — `UNKNOWN → MONITORING → {TRUSTED|VERIFY|HIGH_RISK} → {HOLD|ESCALATE} → REVIEWED`.
- **Does NOT:** permit undeclared transitions or silent regressions from `HOLD`.
- **Input:** current state + policy action.
- **Output:** new state + transition record.
- **Consumed by:** C-42, C-46, C-44.
- **Failure behaviour:** illegal transition → rejected, logged `ILLEGAL_TRANSITION`, state unchanged.
- **Test method:** exhaustive legal/illegal transition matrix test.

**C-42 `decision.actions.ActionEmitter`**
- **Does:** emit `ALLOW | WARN | STEP_UP | HOLD | ESCALATE | ACTIVE_LIVENESS` as structured decisions, and drive the simulated transaction panel and simulated alert record.
- **Does NOT:** execute anything real — no bank call, no SMS, no MFA, no call-back. **Readiness S2/S5/S6.**
- **Input:** state + action.
- **Output:** `Decision` (§6.5) + action-intent records.
- **Consumed by:** C-44, C-46.
- **Failure behaviour:** adapter failure → intent recorded as `DELIVERY_SIMULATED_FAILED`; the decision itself stands.
- **Test method:** assert no network egress occurs on any action; assert intents are recorded.

**C-43 `assurance.explanation.ExplanationService`**
- **Does:** produce the §10.1 contribution breakdown, distinguishing **model attribution** from **causal proof**.
- **Does NOT:** ever emit language like *"These frequencies prove it is fake."* §10.1 mandates *"These are the features contributing to the model's decision."* **No LLM is involved** (§16).
- **Input:** `RiskAssessment.contributions`, `VoiceBelief`, `ContextVector`.
- **Output:** ordered, human-readable factors with signed weights.
- **Consumed by:** C-46, C-44.
- **Failure behaviour:** missing contributions → renders *"Explanation unavailable"* rather than a plausible narrative.
- **Test method:** a **lexical test** asserting no output string matches forbidden proof-claiming phrasing.

**C-44 `assurance.evidence.EvidenceRecorder`**
- **Does:** build the frozen `EvidenceRecord` (§6.6) for every action-grade decision; compute `record_hash` over the canonical serialisation including `previous_hash`; sign with a local key; append to SQLite.
- **Does NOT:** claim to be an enterprise immutable signed store (that is category **C7**). The UI must say *"local hash chain"*.
- **Input:** decision, belief, context, risk, versions.
- **Output:** persisted, chained record.
- **Consumed by:** C-47 (`GET /evidence`), audit tooling.
- **Failure behaviour:** hash/append failure → decision still emitted, `EVIDENCE_WRITE_FAILED` raised and surfaced. **Evidence failure must be loud, never swallowed.**
- **Test method:** chain-verification test over N records; tamper test — mutating record *k* must break verification at *k+1*.

**C-45 `assurance.privacy.PrivacyController`**
- **Does:** enforce §10.3 — raw audio only in the bounded Redis buffer with TTL; features/decisions/evidence persisted; speaker embedding ephemeral; expose the §34 privacy state.
- **Does NOT:** write PCM to SQLite or to any file. **Ever.**
- **Input:** lifecycle events.
- **Output:** expiry actions + privacy state.
- **Consumed by:** C-46 (privacy panel).
- **Failure behaviour:** if expiry cannot be confirmed, raises `PRIVACY_EXPIRY_UNVERIFIED` and the UI privacy panel shows the **degraded** state rather than a reassuring one.
- **Test method:** **a test that scans the SQLite file and the working tree for PCM-shaped blobs after a full session and asserts none exist.** This is the enforceable form of the privacy claim.

**C-46 `assurance.events.EventPublisher`**
- **Does:** publish the frozen WebSocket event set (§8) to `vs:events:{session_id}`; assign monotonic `seq`.
- **Does NOT:** compute anything; publish an event type not declared in §8.
- **Input:** L4/L5 outputs.
- **Output:** event envelopes.
- **Consumed by:** C-49 → browser.
- **Failure behaviour:** subscriber absent → events still published and retained briefly for late joiners; publish failure is logged and counted, never faked at the UI.
- **Test method:** schema test per event type; `seq` monotonicity test.

---

### CROSS-CUTTING

---

**C-47 `api.rest`** — FastAPI REST surface (§7)
- **Does:** expose exactly the §12 endpoints; validate every request with Pydantic.
- **Does NOT:** expose an endpoint that accepts a score, belief, risk or band from the client. **No such endpoint exists in the specification, and adding one is a §22 violation.**
- **Input / Output:** §7.
- **Consumed by:** the SPA and any API consumer.
- **Failure behaviour:** typed error envelope (§13.2); no stack traces to the client.
- **Test method:** endpoint contract tests; a **negative test** asserting there is no route accepting a risk value.

**C-48 `api.ws_audio`** — `WS /v1/sessions/{id}/audio`
- **Does:** accept binary PCM from the browser and feed C-04.
- **Does NOT:** accept JSON control messages that alter scoring.
- **Failure behaviour:** protocol violation → close with a typed code; session marked `DEGRADED`, not silently ended.
- **Test method:** WS integration test including malformed-input rejection.

**C-49 `api.ws_events`** — `WS /v1/sessions/{id}/events`
- **Does:** subscribe to `vs:events:{id}` and relay envelopes to the browser unchanged.
- **Does NOT:** compute, enrich, reformat or interpolate. **It is a relay, and this matters** — any transformation here would be a place to fabricate a value.
- **Failure behaviour:** on disconnect the client reconnects and replays from the last `seq`; gaps are marked `gap_detected` in the UI, **not smoothed over**.
- **Test method:** reconnect test asserting gaps are visible rather than hidden.

**C-50 `storage.repository`** — SQLite persistence (§12)
- **Does:** persist sessions, context, decisions, evidence records, timeline events, and scenario runs.
- **Does NOT:** persist PCM (C-45). Does not become the architecture — §14: *"the architecture must not be redesigned around SQLite."*
- **Failure behaviour:** write failure → `STORAGE_UNAVAILABLE`; the live pipeline continues, the UI shows persistence degraded. Detection must not stop because a disk is full.
- **Test method:** repository tests against a temp DB; a degraded-storage test asserting the pipeline survives.

**C-51 `demo.simulator.ScenarioEngine`** — see §11
- **Does:** select the audio fixture, supply context and transaction context, and start the session. **Nothing else.**
- **Does NOT:** set, adjust, bias, threshold, override or hint any score, belief, risk, confidence or band. §36 is absolute.
- **Failure behaviour:** unknown scenario → `404`; missing fixture → `SourceUnavailable(FIXTURE_MISSING)` with no session started.
- **Test method:** **§11.3 provenance test** — the enforcing test of this entire document.

**C-52 `config.Settings`**
- **Does:** load typed configuration from environment/`.env`; validate at startup; expose a redacted config dump.
- **Does NOT:** contain secrets in source (§11 of the reference).
- **Failure behaviour:** invalid config → **refuse to start** with a precise message. Fail fast at boot, never mid-call.
- **Test method:** invalid-config startup test.

**C-53 `obs.logging`** — see §14
- **Does:** structured JSON logging with correlation IDs.
- **Does NOT:** log PCM, or log raw audio paths in a way that implies retention.
- **Test method:** a log-scrubbing test asserting no audio payload appears in any log record.

**C-54 `frontend/`** — React console — see §10
- **Does:** render the seven §32.1 panels purely from WebSocket state.
- **Does NOT:** hold business logic, thresholds, band boundaries, or **any hardcoded demo value** (A32).
- **Failure behaviour:** missing field → renders an explicit empty/unknown state, never a placeholder number.
- **Test method:** **§10.3 no-hardcoded-values test** plus Playwright end-to-end.

---

## §5 — Dependency graph

### 5.1 Module dependency DAG

```text
config ──────────────────────────────────────────────► (all)
obs.logging ─────────────────────────────────────────► (all)
contracts ───────────────────────────────────────────► (all)

L1  ingestion.source ──► ingestion.session ──► ingestion.buffering
                                                    │
                                                    ▼
                                       signal_processing.preprocessing
                                                    │
                    ┌───────────────┬───────────────┼───────────────┐
                    ▼               ▼               ▼               ▼
            ingestion.channel  ingestion.quality  ingestion.vad  ingestion.turns
                    └───────────────┴───────┬───────┴───────────────┘
                                            ▼
                                 ingestion.language
                                            ▼
                                 ingestion.frame ──► ingestion.publisher
                                                            │
                                            ═══ REDIS vs:frames ═══
                                                            │
L2                          signal_processing.{spectrogram,cepstral,prosody}
                                                            ▼
                                                signal_processing.bundle
                                                            │
L3                                                  models.registry
                                                            │
                        ┌──────┬──────┬──────┬──────┬───────┤
                        ▼      ▼      ▼      ▼      ▼       ▼
                       e1     e2     e3     e4     e5      e6   ◄── models.loader
                        └──────┴──────┴──────┴──────┴───────┘
                                                            ▼
                                                 evidence.assembler
                                                            │
                                          ═══ REDIS vs:evidence (NO PCM) ═══
                                                            │
L4                                              fusion.calibration
                                                            ▼
                                                fusion.weighting
                                                            ▼
                                    fusion.belief ◄──► fusion.clocks
                                                            ▼
                                              fusion.uncertainty
                                                            ▼
                                    fusion.belief (VoiceBelief assembler)
                                                            │
                     context.providers ──► context.assembler │
                                            └───────┬────────┘
                                                    ▼
                                             risk.fusion
                                                    │
L5                                          decision.tiers
                                                    ▼
                                            decision.policy
                                                    ▼
                                            decision.state
                                                    ▼
                                           decision.actions
                                                    │
                        ┌───────────────┬───────────┼───────────────┐
                        ▼               ▼           ▼               ▼
              assurance.explanation  assurance.  assurance.   assurance.events
                                      evidence    privacy            │
                                          │                          ▼
                                    storage.repository       ═══ REDIS pubsub ═══
                                                                     │
                                                              api.ws_events ──► frontend
```

### 5.2 Forbidden edges (enforced by test §15.3)

| Forbidden | Reason |
|---|---|
| L2/L3/L4/L5 → `ingestion.source.*` | P1 replaceability |
| L2/L3/L4/L5 → `soundfile`, `sounddevice`, transport libs | I1 |
| L4/L5 → any PCM-bearing structure | I2 / P2 |
| any expert → any other expert | §6.1 evidence independence |
| `fusion.*` → `context.*` | Phase III must not see context (P5) |
| `decision.*` → `models.*` | the decision layer must not reach into ML |
| `demo.simulator` → any scoring module | §11 |
| `frontend` → any threshold/band constant | A32 |

---

## §6 — Data contracts

Frozen contracts are reproduced from `SYMPHONY_REFERENCE.md` and **must not be shortened, extended or renamed** (§22). Two contracts marked *described but never frozen* in the readiness report are frozen here.

All models: Pydantic, `extra="forbid"`, explicit `Optional` for every abstainable field.

### 6.1 `FrameObject` — frozen (reference §5)

```text
FrameObject {
    session_id : str
    frame_id   : int              # monotonic per session

    pcm         : float32[]       # canonical rate, mono
    sample_rate : int

    t_start : float               # seconds from session start
    t_end   : float

    codec_vec   : CodecDescriptor | UNKNOWN
    bandwidth   : float | None
    packet_loss : float | None

    q_t : float | None            # [0,1]; None = unknown

    is_speech    : bool
    speaker_turn : int | None
    overlap_flag : bool | None

    lang_t      : str             # ISO tag or "UNKNOWN"
    switch_flag : bool

    source_type : str             # opaque: "wav" | "mic" | "ws" | future "sip_rtp"

    created_at : datetime
}
```

**`source_type` is the only trace of origin permitted downstream, and it is opaque.** No consumer may branch on it for scoring logic.

### 6.2 `EvidenceVector` — frozen (reference §7)

```text
EvidenceVector {
    session_id : str
    frame_id   : int

    p_spec : float | None         # E1   None ⇒ see expert_statuses
    p_raw  : float | None         # E2
    p_ssl  : float | None         # E3
    p_spk  : float | None         # E4   ABSTAIN when not enrolled
    p_beh  : float | None         # E5   DEFERRED in this demo
    p_rep  : float | None         # E6   DEFERRED in this demo

    frame_logits       : dict[str, float[]]
    expert_confidences : dict[str, float | None]
    expert_statuses    : dict[str, ExpertStatus]

    q_t       : float | None
    codec_vec : CodecDescriptor | UNKNOWN

    lang_t      : str
    switch_flag : bool

    inference_latency_ms : dict[str, float]

    model_versions : list[str]

    timestamp : datetime
}

ExpertStatus = OK | ABSTAIN | DEFERRED | MODEL_UNAVAILABLE | TIMEOUT | ERROR
```

**Contains no PCM.** This is the physical enforcement of P2/I2.
`expert_statuses` is the addition that makes abstention machine-readable; it is an operational-provenance field of the kind reference §7 already anticipates, and it removes any need to encode abstention as a fake number.

### 6.3 `VoiceBelief` — frozen (reference §8.6)

```text
VoiceBelief {
    session_id : str

    P_spoof    : float | None
    confidence : float            # SEPARATE from P_spoof — P4

    band : GENUINE | UNCERTAIN | SUSPICIOUS | SYNTHETIC_HIGH_CONFIDENCE

    q_call : float | None

    spans      : Span[]           # [] in this demo (B3)
    trajectory : TrajectoryPoint[]

    contributing_experts : ExpertContribution[]

    uncertainty_reason : str | None

    switch_damping_events : DampingEvent[]   # [] in this demo (B4)

    model_versions : list[str]
    clock          : FAST | SLOW             # which clock produced this
    timestamp      : datetime
}
```

### 6.4 `ContextVector` — **FROZEN BY THIS DOCUMENT** (resolves readiness §10.3)

Fields taken from reference §9.1; every field carries provenance so a simulated value can never be mistaken for a real one.

```text
ContextVector {
    session_id : str

    identity : {
        claimed_identity   : str | None
        verified_identity  : str | None
        enrollment_status  : ENROLLED | NOT_ENROLLED | UNKNOWN
        cnap_state         : str | None
        identity_mismatch  : bool | None
    }

    number : {
        reputation         : float | None
        age_days           : int | None
        known_fraud_status : bool | None
        port_history       : bool | None
    }

    transaction : {
        amount               : Decimal | None
        currency             : str | None
        transaction_type     : str | None
        beneficiary_novelty  : NEW | KNOWN | UNKNOWN
        velocity             : float | None
        historical_deviation : float | None
    }

    behaviour : {
        urgency              : bool | None
        secrecy              : bool | None
        callback_refusal     : bool | None
        verification_bypass  : bool | None
        unusual_request      : bool | None
    }

    technical : {
        device_signal        : str | None
        network_origin       : str | None
        voip_mobile_indicator: VOIP | MOBILE | LANDLINE | UNKNOWN
        codec                : CodecDescriptor | UNKNOWN
    }

    provenance : dict[str, REAL | SIMULATED | UNAVAILABLE]   # per field path
    timestamp  : datetime
}
```

**In this build every populated field's provenance is `SIMULATED`.** A test asserts no field claims `REAL` (§11.3).

### 6.5 `Decision` — **FROZEN BY THIS DOCUMENT**

```text
RiskAssessment {
    session_id      : str
    risk_score      : float           # [0,1]
    risk_confidence : float
    risk_band       : LOW | MEDIUM | HIGH | CRITICAL | UNCERTAIN
    contributions   : RiskContribution[]    # {factor, weight, direction}
    context_degraded: bool
    timestamp       : datetime
}

Decision {
    decision_id : str
    session_id  : str

    voice_belief_ref : str            # VoiceBelief identity
    risk             : RiskAssessment

    transaction_tier : 0 | 1 | 2 | 3 | 4

    action : ALLOW | WARN | STEP_UP | HOLD | ESCALATE | ACTIVE_LIVENESS
    state  : UNKNOWN | MONITORING | TRUSTED | VERIFY | HIGH_RISK
           | HOLD | ESCALATE | REVIEWED

    reason_codes   : str[]
    policy_version : str
    clock          : SLOW             # action-grade only — §8.3

    recommended_verifications : str[]  # e.g. CALL_REGISTERED_NUMBER, REQUEST_MFA
    timestamp : datetime
}
```

**`Decision.risk_band` uses `LOW|MEDIUM|HIGH|CRITICAL|UNCERTAIN`** while `VoiceBelief.band` uses the four evidence bands. Per adopted §10.2 these describe **different objects** — voice evidence versus voice+context risk — and the UI must label both so the distinction reads as intent, not inconsistency.

**Action-grade decisions are `clock = SLOW` only.** Fast-clock updates produce provisional UI state, never a `Decision`.

### 6.6 `EvidenceRecord` — frozen (reference §10.2)

```text
EvidenceRecord {
    record_id : str

    session_id : str
    call_id    : str

    timestamp : datetime

    model_versions : list[str]

    codec         : CodecDescriptor | UNKNOWN
    audio_quality : float | None

    expert_scores : dict[str, {p, confidence, status}]

    voice_belief : VoiceBelief

    context_features    : ContextVector
    transaction_context : TransactionContext

    risk       : float
    confidence : float

    action         : ActionClass
    policy_version : str
    reason_codes   : str[]

    previous_hash : str
    record_hash   : str
    signature     : str
}
```

Chain rule: `record_hash = H(canonical_json(record_without_hash_and_signature) || previous_hash)`. First record uses the genesis constant. Canonical serialisation must be deterministic (sorted keys, fixed float format) or verification is meaningless.

---

## §7 — API contracts

Exactly the §12 surface. Nothing added. §12: *"The external API should be deliberately small."*

| Method | Path | Request | Response | Notes |
|---|---|---|---|---|
| `POST` | `/v1/sessions` | `{source_type, scenario_id?, caller_ref?}` | `201 {session_id, state}` | Creates; does not start |
| `GET` | `/v1/sessions/{id}` | — | `200 SessionState` | |
| `POST` | `/v1/sessions/{id}/start` | — | `202 {state}` | Opens source, begins L1 |
| `POST` | `/v1/sessions/{id}/stop` | — | `202 {state}` | Graceful drain |
| `GET` | `/v1/sessions/{id}/risk` | — | `200 RiskAssessment` | Latest action-grade |
| `GET` | `/v1/sessions/{id}/evidence` | — | `200 EvidenceRecord[]` | Chain-verifiable |
| `GET` | `/v1/sessions/{id}/timeline` | — | `200 TimelineEvent[]` | The §32 timeline |
| `POST` | `/v1/sessions/{id}/context` | `ContextVector` (partial) | `202` | **Context only. Rejects any scoring field.** |
| `POST` | `/v1/sessions/{id}/actions/verify` | `{method}` | `202 {intent_id}` | Simulated |
| `POST` | `/v1/sessions/{id}/actions/hold` | `{reason}` | `202 {intent_id}` | Simulated |
| `POST` | `/v1/sessions/{id}/actions/escalate` | `{to}` | `202 {intent_id}` | Simulated |

**Demo-only, clearly namespaced:**

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/v1/demo/scenarios` | List the three frozen scenarios |
| `POST` | `/v1/demo/scenarios/{scenario_id}/run` | Create + start a session with that fixture and context |
| `GET` | `/v1/health` | Liveness + **per-expert availability report** |

`POST /v1/sessions/{id}/context` **must reject** any request body containing a key matching `p_*`, `risk*`, `confidence`, `band`, `P_spoof`, or `score` — with `422 SCORING_FIELD_REJECTED`. This is a hard API-level guard against the failure mode §36 warns about.

### 7.1 Error envelope

```text
{ "error": { "code": str, "message": str, "session_id": str|null,
             "correlation_id": str, "retriable": bool } }
```

---

## §8 — WebSocket message contracts

**Resolves readiness §10.4.** Two channels (reference §12). Every panel in §32.1 maps to exactly one event type; the frontend may render nothing that lacks an event here.

### 8.1 `WS /v1/sessions/{id}/audio` — ingress

- **Client → server:** binary PCM frames, preceded by one JSON header `{type:"audio.header", sample_rate, channels, encoding}`.
- **Server → client:** `{type:"audio.ack", frames_received, dropped}` and `{type:"error", ...}` only.
- Any other client message type → close `4400 AUDIO_PROTOCOL_VIOLATION`.

### 8.2 `WS /v1/sessions/{id}/events` — egress

Envelope for every message:

```text
{ v: 1, type: <EventType>, session_id: str, seq: int, ts: iso8601, payload: {...} }
```

`seq` is monotonic per session; the client detects gaps and displays them (C-49).

### 8.3 The frozen event set

| `type` | Clock | Payload | Renders |
|---|---|---|---|
| `session.state` | — | `{state, source_type, started_at, demo_mode: bool}` | Header, DEMO MODE banner |
| `call.info` | — | `{caller, number, duration_s, language, source}` | Call panel |
| `evidence.update` | FAST | `{frame_id, experts: {id: {p, confidence, status}}, q_t}` | Evidence panel |
| `belief.update` | FAST | `{P_spoof, confidence, band, trajectory_point, uncertainty_reason}` | Risk trajectory chart |
| `risk.update` | SLOW | `RiskAssessment` | Central risk panel |
| `decision.update` | SLOW | `Decision` | Action + state |
| `explanation.update` | SLOW | `{factors:[{label, weight, direction}], risk, confidence}` | Explanation panel |
| `timeline.event` | — | `{t, code, label, severity}` | Timeline |
| `transaction.update` | SLOW | `{amount, currency, beneficiary, status, reason}` | Transaction panel |
| `recommendation.update` | SLOW | `{headline, verifications:[...]}` | Recommendation panel |
| `language.update` | FAST | `{lang_t, switch_flag, code_switch_detected}` | Language panel |
| `privacy.state` | — | `{raw_audio_retention, feature_logging, speaker_embedding, audit_event, degraded}` | Privacy panel |
| `model.availability` | — | `{experts:{id:status}}` | Honest capability disclosure |
| `error` | — | error envelope | Error surface |

**No other event type may be emitted, and the frontend must ignore unknown types rather than guessing.**

**`model.availability` is deliberately part of the demo surface.** If E1 has no weights, the judge sees that stated — which is what §22 requires and what makes the rest of the display trustworthy.

---

## §9 — ML inference contracts

### 9.1 The expert interface

```text
Expert (protocol) {
    expert_id         : "E1".."E6"
    required_features : list[FeatureKey]
    model_version     : str | None
    is_available      : bool

    score(bundle: FeatureBundle) -> ExpertResult
}

ExpertResult {
    expert_id     : str
    status        : OK | ABSTAIN | DEFERRED | MODEL_UNAVAILABLE | TIMEOUT | ERROR
    p             : float | None      # MUST be None unless status == OK
    confidence    : float | None
    frame_logits  : float[] | None
    latency_ms    : float
    model_version : str | None
    detail        : str | None
}
```

### 9.2 Invariants (each individually tested)

| # | Invariant |
|---|---|
| **M1** | `status != OK` ⇒ `p is None`. **An abstention may never be represented as a number.** |
| **M2** | An expert never receives another expert's output (reference §6.1). |
| **M3** | An expert never receives context, transaction data, or scenario identity. A model must not be able to learn *which scenario is running*. |
| **M4** | An expert is pure with respect to session order — no cross-session state. |
| **M5** | Every expert enforces a timeout; exceeding it yields `TIMEOUT`, never a partial score. |
| **M6** | Model artefacts load from local disk only; no runtime download (R12). |
| **M7** | `model_version` is recorded on every result and propagates to `EvidenceRecord`. |

**M3 is the single most important integrity invariant in this document.** If the scenario identity could reach an expert, the demo would be capable of cheating, and every result would become unfalsifiable.

### 9.3 What is NOT claimed

- No accuracy, EER, AUC, precision or recall figure — **no evaluation set exists** (readiness §7.5).
- No calibration is fitted — weights are **engineering priors** per reference §8.1 (readiness §7.4).
- No language-specific validation — readiness **B5**.
- No localisation resolution — reference §8.4 forbids the claim until measured.

Tests assert *relative* and *structural* properties (ordering, monotonicity, abstention) — **never absolute performance.**

---

## §10 — Frontend / backend boundary

### 10.1 The rule

Reference §32.1: **"Do not hardcode demo values. All displayed values must come from backend state, over WebSocket, updating without page refresh."**

### 10.2 Division of responsibility

| Concern | Backend | Frontend |
|---|---|---|
| Scores, beliefs, risk, bands, confidence | **Owns entirely** | Renders only |
| Thresholds and band boundaries | **Owns entirely** | **Must not know them** |
| Timeline event text and severity | **Owns** | Renders |
| Explanation factor labels and weights | **Owns** | Renders |
| Recommended verifications | **Owns** | Renders as buttons |
| Transaction status | **Owns** | Renders |
| Colour mapping for a band | — | Owns (presentation only) |
| Layout, animation, accessibility | — | Owns |
| Reconnect, gap display | — | Owns |

The frontend receives a **band name** and maps it to a colour. It never receives a number and decides the band. That single rule keeps every security-relevant judgement server-side.

### 10.3 Panels (reference §32.1) → event source

| Panel | Fed by |
|---|---|
| Header + live status | `session.state`, `model.availability` |
| Call panel | `call.info` |
| Central risk panel | `risk.update`, `decision.update` |
| Evidence panel (Acoustic · Synthetic · Speaker · Prosody · Quality) | `evidence.update` |
| Risk trajectory chart | `belief.update` |
| Timeline | `timeline.event` |
| Transaction panel | `transaction.update` |
| Recommendation panel | `recommendation.update` |
| Language panel | `language.update` |
| Privacy panel | `privacy.state` |
| DEMO MODE banner | `session.state.demo_mode` |

**Design constraints (reference §32.1):** dark security-console aesthetic, restrained typography, strong hierarchy, minimal clutter, clear status colours, accessible contrast, subtle animation only where useful.

**Enforcement test:** a static check over `frontend/src` asserting no numeric literal is used as a risk, probability, threshold or band boundary, and that no component holds a mock/fixture data structure. A Playwright test asserts that two different scenarios produce different rendered values from the same code path.

---

## §11 — Demo simulator boundary

This is the boundary on which the demo's integrity rests. Reference §36:

> The scenario engine must **not** directly set the risk score. It may only select the audio fixture, provide context, provide transaction context, and start the session. **The real pipeline must produce the result.**

### 11.1 What the simulator may do

1. Select which **audio fixture** is opened.
2. Supply **`ContextVector`** field values (all marked `SIMULATED`).
3. Supply **transaction context** (amount, beneficiary novelty, type).
4. **Start** the session.
5. Set the `demo_mode` flag that drives the mandatory UI banner.

### 11.2 What the simulator may NOT do

- Write `p_spec`, `p_raw`, `p_ssl`, `p_spk`, `p_beh`, `p_rep`, `P_spoof`, `confidence`, `band`, `risk_score`, `risk_band`, `action`, or `state`.
- Bias, scale, offset or threshold any of the above.
- Pass scenario identity into L2, L3 or L4 (invariant **M3**).
- Choose the outcome. **The scenario names an input, never an output.**

### 11.3 Enforcement (the decisive test)

Three independent mechanisms, because a single convention is not enough:

1. **Structural:** `ScenarioDefinition` contains only `{scenario_id, label, fixture_path, context, transaction, enrollment_ref}`. There is **no field capable of expressing a score.**
2. **Import guard:** `demo.*` may not import `fusion.*`, `risk.*`, `decision.*`, or `models.*` (§5.2).
3. **Provenance test:** run each scenario end-to-end and assert every scoring field in the resulting `EvidenceRecord` traces to a pipeline computation, and that mutating **only** the fixture changes the outcome while mutating **only** the scenario label does not.

### 11.4 The three frozen scenarios

| ID | Fixture | Context | Expected shape | Source |
|---|---|---|---|---|
| `S1_GENUINE` | Genuine executive call | CFO, ₹25 lakh, **known** beneficiary | Low risk → `ALLOW` | §35.2 |
| `S2_CLONE` | AI-cloned executive | CFO, ₹25 lakh, **new** beneficiary | High/critical → `HOLD` + `ESCALATE` | §35.2 |
| `S3_UNCERTAIN` | **Degraded/poor-quality call** | CFO, ₹25 lakh | `UNCERTAIN` → `STEP_UP` | §35.2, §36; readiness §10.9 |

**"Expected shape" is an expectation, not a guarantee.** Reference §36 accepts this trade explicitly: *"You aren't faking the ML result; you're controlling the input scenario so the demo remains reproducible."* If the pipeline disagrees with the expected shape, **the displayed result is the pipeline's** and the discrepancy is a finding to report honestly (readiness **R3**).

**Deferred stretch scenario:** `S4_PARTIAL_SPOOF` (human → synthetic instruction → human) is **not built** — requires C-34 (B3).

---

## §12 — Storage boundary

### 12.1 What lives where

| Data | Store | Lifetime | Rationale |
|---|---|---|---|
| Raw PCM | **Redis stream `vs:frames` only** | `MAXLEN` + TTL bounded | Reference §10.3 short-lived buffer |
| Frame metadata | Redis (in the entry) | With the frame | — |
| `EvidenceVector` | Redis stream `vs:evidence` | Bounded | Contains no PCM |
| Session state | Redis hash + SQLite | Session + audit | §14 |
| Context / transaction | SQLite | Retained | §14 |
| Decisions | SQLite | Retained | §14 |
| Evidence records + hash chain | SQLite | Retained | §14 |
| Timeline events | SQLite | Retained | §32 |
| Speaker embeddings | **Memory only, ephemeral** | Session | §34: "EPHEMERAL" |
| Model artefacts | Local filesystem | Static | §14 object storage → local files for Profile A |
| Logs | stdout / rotating file | Bounded | §14 |

### 12.2 The absolute rule

**PCM is never written to SQLite and never written to a durable file.** Reference §10.3: *"Never make raw audio persistence the default."* This build goes further — there is no non-default path either.

Enforced by C-45's test: after a full session, scan the database and working tree for audio-shaped payloads and assert none.

### 12.3 SQLite tables

`sessions` · `context_snapshots` · `decisions` · `evidence_records` (with `previous_hash`, `record_hash`, `signature`) · `timeline_events` · `action_intents` · `scenario_runs`

**No `audio` table exists, and none may be added.**

### 12.4 Not redesigning around SQLite

Reference §14: *"SQLite can replace PostgreSQL and local files can replace object storage — but the architecture must not be redesigned around SQLite."* Therefore all access goes through `storage.repository` interfaces; no SQLite-specific behaviour leaks into L1–L5.

---

## §13 — Error handling

### 13.1 The governing principle (reference §22)

> If a model isn't available → `MODEL_UNAVAILABLE`
> If audio is insufficient → `UNCERTAIN`
> If the speaker is not enrolled → `E4 = ABSTAIN`
> If codec identification is uncertain → `codec = UNKNOWN`

**Every error path resolves to an abstention or an explicit degraded state. No error path produces a number.**

### 13.2 Failure classes

| Class | Example | Behaviour | Surfaced as |
|---|---|---|---|
| **Fail-fast (boot)** | Invalid config, unreadable model dir | Refuse to start | Startup error |
| **Fail-safe (decision)** | Policy error, unknown transaction type | Most conservative option (`STEP_UP`; tier 4) | `reason_codes` |
| **Abstain (evidence)** | Missing weights, timeout, no enrollment | `status != OK`, `p = None` | `model.availability`, evidence panel |
| **Degrade (transport/storage)** | Redis slow, SQLite write fail | Continue detecting; mark degraded | `session.state.degraded` |
| **Drop (frame)** | Invalid frame, unsupported format | Drop one frame, count it | Metrics + log |
| **Terminate (session)** | Source unavailable | `FAILED` with reason; **no final score** | `error` event |

### 13.3 What must never happen

1. A default probability substituted for a missing model.
2. `GENUINE` returned because evidence was absent — that is `UNCERTAIN`.
3. `ALLOW` issued from a policy error.
4. A UI value rendered from a client-side default.
5. An evidence-write failure swallowed silently.
6. Interpolated audio invented to cover a gap.

### 13.4 Reason codes

Namespaced and stable, since they enter `EvidenceRecord.reason_codes[]`:
`VOICE_*` (e.g. `VOICE_SYNTHETIC_EVIDENCE`, `VOICE_SPEAKER_MISMATCH`, `VOICE_UNCERTAIN_LOW_QUALITY`) ·
`CTX_*` (`CTX_NEW_BENEFICIARY`, `CTX_HIGH_VALUE`, `CTX_BEHAVIOURAL_URGENCY`) ·
`POLICY_*` (`POLICY_TIER4_CONSERVATIVE`, `POLICY_ERROR`) ·
`SYS_*` (`SYS_MODEL_UNAVAILABLE`, `SYS_CONTEXT_UNAVAILABLE`, `SYS_STORAGE_DEGRADED`).

---

## §14 — Logging

### 14.1 Format

Structured JSON to stdout (reference §15: *structured JSON logging*). Every record: `ts`, `level`, `logger`, `msg`, `correlation_id`, `session_id?`, `frame_id?`, `component`, plus typed extras. Docker Compose captures stdout; **no external log service** — no cloud dependency.

### 14.2 Correlation

One `correlation_id` per session, propagated through the Redis message envelopes so a single call can be traced across all three processes.

### 14.3 What must never be logged

- PCM or any audio payload (C-53 test).
- Full fixture paths in a way implying retention.
- Secrets or keys (reference §11).
- A score presented as fact when its status is not `OK`.

### 14.4 Level policy

| Level | Use |
|---|---|
| `DEBUG` | Per-frame timings, feature shapes |
| `INFO` | Session lifecycle, action-grade decisions, model availability at boot |
| `WARNING` | Abstentions, degraded clock, dropped frames, damped events |
| `ERROR` | Storage/evidence failures, policy errors, illegal transitions |
| `CRITICAL` | Boot failure |

### 14.5 Metrics (basic only)

Readiness **B15** defers Prometheus. In-process counters exposed on `/v1/health`: frames ingested/dropped, per-expert latency and status counts, belief updates per clock, decisions by action, evidence records written, chain-verify status. **No Grafana, no external metrics backend, no cloud.**

---

## §15 — Test strategy

Reference §31: pytest + Playwright. Reference §37: Playwright is *"the demo reliability weapon."*

### 15.1 Layers of testing

| Level | Scope | Tool |
|---|---|---|
| **Unit** | One component in isolation | pytest |
| **Contract** | Every frozen schema, field-for-field vs §6 | pytest |
| **Invariant** | The architectural rules — the tests that matter most | pytest |
| **Integration** | Two adjacent layers across Redis | pytest-asyncio |
| **End-to-end** | Scenario → pipeline → API → UI | Playwright |
| **Rehearsal** | Full demo, offline cold start | Playwright + script |

### 15.2 Contract tests

For each of `FrameObject`, `EvidenceVector`, `VoiceBelief`, `ContextVector`, `Decision`, `EvidenceRecord`: assert exact field set (no additions, no removals), types, optionality, and rejection of extra fields.

### 15.3 Invariant tests — the architectural guardrails

| Test | Asserts | Guards |
|---|---|---|
| `test_import_guard` | No L2–L5 module imports a source adapter, `soundfile`, `sounddevice`, or a transport lib | P1, I1 |
| `test_no_pcm_downstream` | Serialised `EvidenceVector` contains no PCM; `decision-worker` never reads `vs:frames` | P2, I2 |
| `test_layer_direction` | No module imports a layer above it | I4 |
| `test_expert_independence` | No expert's output reaches another expert's input | §6.1 |
| `test_expert_blind_to_scenario` | Scenario identity is unreachable from L2–L4 | **M3** |
| `test_simulator_cannot_score` | `demo.*` imports nothing scoring-related; `ScenarioDefinition` has no score-capable field | §36 |
| `test_abstention_never_numeric` | `status != OK` ⇒ `p is None`, everywhere | **M1**, §22 |
| `test_no_hardcoded_ui_values` | No numeric literal in `frontend/src` acts as risk/threshold/band | A32 |
| `test_fusion_is_not_mean` | Weighting is not equivalent to a uniform average on crafted input | §8, R6 |
| `test_no_pcm_persisted` | No audio-shaped blob in SQLite or the tree after a session | §10.3 |
| `test_no_runtime_download` | No network egress during a full offline run | R12 |
| `test_context_provenance` | No context field claims `REAL` in this build | §11 |
| `test_policy_has_final_say` | No path lets risk alone produce `ALLOW` at tiers 3–4 | §9.3 |
| `test_explanation_no_proof_claims` | No output string claims causal proof | §10.1 |

### 15.4 Behavioural tests (relative, never absolute)

- Sustained synthetic evidence → **rising** trajectory (§8.2 behaviour).
- A single outlier frame → **no** spike.
- Degraded audio → lower `q_t` → lower confidence → band `UNCERTAIN`.
- Same speaker pair scores **higher** than different speaker pair (E4, relative only).
- Identical voice evidence → **higher** risk at tier 4 than tier 0.
- Removing enrollment → `E4 = ABSTAIN`, pipeline still completes.
- Removing all weights → every expert `MODEL_UNAVAILABLE`, band `UNCERTAIN`, action not `ALLOW`.

**No test asserts a specific accuracy.** Reference §7.5 of the readiness report: no evaluation set exists.

### 15.5 End-to-end (reference §37)

```text
Open dashboard → start S1_GENUINE → verify LOW/ALLOW and transaction proceeds
               → start S2_CLONE   → verify risk rises across ≥3 updates
                                  → verify CRITICAL alert
                                  → verify transaction shows ON HOLD
               → start S3_UNCERTAIN → verify UNCERTAIN band and STEP_UP
                                    → verify confidence renders as LOW, not as "genuine"
               → verify DEMO MODE banner present throughout
               → verify model.availability panel reflects real expert status
```

### 15.6 Rehearsal gate

Before demo day: full run with **networking disabled** and a cold cache, three consecutive times, all three scenarios. Any runtime download attempt fails this gate (R12).

---

## §16 — Startup sequence

### 16.1 Order (all three roles)

```text
1.  Load + validate config (C-52)        ── invalid ⇒ EXIT 1
2.  Initialise structured logging (C-53)
3.  Connect Redis                        ── unavailable ⇒ retry with backoff, then EXIT 1
4.  Open SQLite, run migrations          ── failure ⇒ EXIT 1
5.  Verify evidence hash chain integrity ── broken ⇒ log CRITICAL, start in read-only-evidence mode
6.  Role-specific init (16.2)
7.  Register signal handlers (SIGINT/SIGTERM)
8.  Announce readiness on /v1/health (api) or log READY (workers)
```

### 16.2 Role-specific

**`api`:** create Redis consumer groups if absent → mount REST routes → mount WS endpoints → load scenario definitions and **verify every fixture file exists** (missing fixture is a startup warning naming the file, not a silent failure) → serve.

**`analysis-worker`:** load model artefacts from local disk, verify checksums (C-27) → register available experts → **log an explicit availability table for E1–E6** → join `vs:frames` consumer group → warm each model with one dummy forward pass so the first real frame is not the slowest → consume.

**`decision-worker`:** load policy rules and `policy_version` → load calibration (flagging `PRIOR_ONLY`) → initialise the state machine → join `vs:evidence` consumer group → consume.

### 16.3 Startup honesty requirement

The `api` readiness response and the worker boot log **must state which experts are available and which are not.** A system that boots with four of six experts missing must say so at boot and in `model.availability`. Concealing it would make every subsequent display untrustworthy.

### 16.4 Order independence

The three roles may start in any order. Workers block on their consumer group; the API accepts sessions but reports `degraded` if no analysis worker has claimed frames within a bounded interval.

---

## §17 — Shutdown sequence

### 17.1 Graceful (SIGTERM / SIGINT)

```text
api:
  1. Stop accepting new sessions (503 on POST /v1/sessions)
  2. Close audio WS ingress; stop all AudioSources (C-01.close)
  3. Flush remaining frames to vs:frames
  4. Hold events WS open briefly so final events reach the UI
  5. Close events WS, Redis, SQLite
  6. EXIT 0

analysis-worker:
  1. Stop claiming new stream entries
  2. Finish in-flight frames (bounded by a drain timeout)
  3. XACK completed entries               ← unacked entries remain claimable
  4. Release models; EXIT 0

decision-worker:
  1. Stop claiming new evidence
  2. Finish in-flight fusion
  3. Write a terminal Decision + EvidenceRecord for each open session,
     with action reflecting the LAST COMPUTED state           ← never a synthesised verdict
  4. Publish session.state = TERMINATED
  5. XACK; close; EXIT 0
```

### 17.2 Privacy on shutdown

C-45 explicitly expires session audio buffers during shutdown. **Raw audio must not survive process exit.** If expiry cannot be confirmed, log `CRITICAL PRIVACY_EXPIRY_UNVERIFIED` — do not exit silently.

### 17.3 Abrupt termination

Redis stream entries are `MAXLEN`-bounded and TTL'd, so orphaned audio expires without intervention. On restart, sessions found in a non-terminal state are marked `INTERRUPTED` — **they are not resumed and no score is reconstructed for them.**

---

## §18 — Demo execution flow

### 18.1 The judge-facing sequence (reference §38.2)

```text
Operator opens dashboard
   → DEMO MODE banner visible; model.availability shown
   → DEMO CONTROL → select "Genuine Executive Call" → START SIMULATION
       POST /v1/demo/scenarios/S1_GENUINE/run
         → session created, context supplied (SIMULATED), fixture opened
         → L1 frames → Redis → L2/L3 real inference → EvidenceVector
         → L4 belief accumulates → trajectory rises slowly and settles low
         → L5 policy at tier 3 with KNOWN beneficiary → ALLOW
         → UI: low risk, transaction proceeds
   → DEMO CONTROL → "AI Voice Clone" → START SIMULATION
       POST /v1/demo/scenarios/S2_CLONE/run
         → SAME code path, SAME models, DIFFERENT fixture + NEW beneficiary
         → evidence accumulates; trajectory climbs across successive updates
         → slow clock crosses the tier-3 threshold → HOLD + ESCALATE
         → UI: critical band, explanation panel, transaction ON HOLD,
              recommended verifications rendered
   → DEMO CONTROL → "Poor-quality call" → START SIMULATION
       POST /v1/demo/scenarios/S3_UNCERTAIN/run
         → low q_t → weights reduced → confidence low → band UNCERTAIN
         → policy: UNCERTAIN at tier 3 ⇒ STEP_UP  (never ALLOW)
         → UI: shows "we don't know", not "probably genuine"   ← P4 demonstrated
```

### 18.2 Why the third scenario is the strongest technical moment

S1 and S2 show detection. **S3 shows the system declining to guess** — which is the behaviour §22 demands and the one most systems cannot demonstrate. It is the visible proof of P4 and of the abstention semantics running through every component in §4.

### 18.3 The disclosure obligations during the demo

Both lines are mandatory and quoted from the reference:

> *"For the internal prototype, the telephony boundary is simulated using a real-time audio stream. The ingestion interface is deliberately decoupled from the detection pipeline so that the same backend can later accept SIP/RTP or enterprise communication streams."* (§29)

> *"The architecture is language-agnostic at the feature layer, with language-specific models that can be expanded progressively."* (§33)

Plus, from this document: no bank is connected, no money moves, no accuracy figure exists, and the availability panel shows exactly which experts are running.

### 18.4 Failure conduct during the demo

If the pipeline produces an unexpected result (readiness **R3**), the displayed result stands and is explained honestly. **The system has no mechanism to override it** — §11.3 guarantees that, by construction. This is a feature of the design, and worth saying aloud.

---

## §19 — Repository layout

Per adopted §10.8 (reference §30.1).

```text
VoiceShield/
├── backend/
│   └── voiceshield/
│       ├── __main__.py           # role dispatch: api | analysis-worker | decision-worker | all-in-one
│       ├── config.py             # C-52
│       ├── obs/logging.py        # C-53
│       ├── contracts/            # §6 — all frozen Pydantic models
│       ├── ingestion/            # C-01..C-14   (L1)
│       ├── signal_processing/    # C-15..C-18   (L2)
│       ├── models/               # C-19..C-27   (L3)
│       ├── evidence/             # C-26
│       ├── speaker/              # C-27 enrollment
│       ├── fusion/               # C-28..C-35   (L4, Phase III)
│       ├── context/              # C-36..C-37   (L4, Phase IV front)
│       ├── risk/                 # C-38
│       ├── decision/             # C-39..C-42   (L5)
│       ├── assurance/            # C-43..C-46   (Phase V)
│       ├── storage/              # C-50
│       ├── api/                  # C-47..C-49
│       └── demo/                 # C-51
├── frontend/                     # C-54
├── tests/                        # §15
├── demo/{audio,scenarios,recordings}/
├── docs/
│   ├── PS.md
│   ├── ARCHITECTURE.md
│   ├── EXECUTABLE_ARCHITECTURE.md   ← this document
│   ├── EXECUTION_TECH_STACK.md
│   ├── DEMO_SCOPE.md
│   ├── DEMO_SCENARIOS.md
│   └── IMPLEMENTATION_READINESS.md
├── scripts/
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

### 19.1 Docker Compose services

`redis` · `api` · `analysis-worker` · `decision-worker` · `frontend` (dev server; static build in production-shaped mode).

**No Kubernetes. No cloud services. No external managed dependency of any kind.** Five containers on one machine, which is exactly Profile A.

---

## §20 — Traceability of this document

| Requirement asked for | Section |
|---|---|
| 1. System boundaries | §1 |
| 2. Components | §4 |
| 3. Responsibilities of every component | §4 (Does / Does NOT per component) |
| 4. Inputs and outputs | §4 (Input / Output / Consumed by) |
| 5. Data contracts | §6 |
| 6. API contracts | §7 |
| 7. WebSocket message contracts | §8 |
| 8. ML inference contracts | §9 |
| 9. Risk-engine contracts | §6.5, C-38–C-41 |
| 10. Frontend/backend boundaries | §10 |
| 11. Demo simulator boundary | §11 |
| 12. Storage boundary | §12 |
| 13. Error handling | §13 |
| 14. Logging | §14 |
| 15. Test strategy | §15 |
| 16. Startup sequence | §16 |
| 17. Shutdown sequence | §17 |
| 18. Dependency graph | §5 |
| 19. Runtime architecture | §3 |
| 20. Demo execution flow | §18 |
| L1–L5 distinguishable | §2, §4, §5 |
| Audio source replaceable by SIP/RTP | §1.3, C-01, §5.2 |
| No unjustified microservices | §3.2 |
| No Kubernetes | §19.1 |
| No cloud dependencies | §14.1, §14.5, §19.1 |
| No production claims | §0.3, §9.3, §11.4, §18.3 |

---

## §21 — The binding contract (unchanged)

From `SYMPHONY_REFERENCE.md` §22, binding on every implementation step that follows:

> **No developer or AI agent may modify the five phase boundaries, cross-phase contracts, model roles, or decision semantics without first modifying the architecture specification and obtaining review.**

> **No score may be fabricated to make the demo work.**

> If a model isn't available → `MODEL_UNAVAILABLE`
> If audio is insufficient → `UNCERTAIN`
> If the speaker is not enrolled → `E4 = ABSTAIN`
> If codec identification is uncertain → `codec = UNKNOWN`

---

*End of specification. No application code was written, and no source document was modified, in producing it.*

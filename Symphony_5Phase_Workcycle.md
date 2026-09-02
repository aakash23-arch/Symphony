# SYMPHONY — The Five-Phase Workcycle
## Core Framework Document · SIH26104 Real-Time Voice Cloning Detection

**Status:** Framework lock. Supersedes nothing in `SIH26104_Consolidated_Blueprint.md` — extends it.
**Relationship to blueprint:** The blueprint answers *what to build and why it wins*. This document answers *how the built thing behaves, second by second, on a live call*, and defines the interfaces that let four workstreams build in parallel without colliding.
**Scope note:** Everything marked ⚠ requires verification by the team before it appears on a slide.

---

## 0. Why "Symphony" is the right name (and how to use it)

A symphony is not a solo. It is a set of independent instrument families, each with a different physical mechanism for producing sound, playing simultaneously under one conductor, where the *meaning* emerges from the combination rather than from any single line.

That is a precise, non-decorative description of this architecture:

| Musical element | System element |
|---|---|
| Instrument families (strings, brass, woodwind, percussion) | Independent forensic experts — spectral, raw-waveform, SSL, speaker, prosody |
| Score | The evidence protocol — what each expert is asked to report and when |
| Conductor | The risk engine that weights experts by conditions and decides |
| Movements | The five phases of the workcycle |
| Coda | The audit and learning loop that closes back to the beginning |

**Use it once, on slide 3, in one sentence, then stop.** A metaphor that earns a nod is an asset; a metaphor repeated on every slide reads as compensation for thin engineering. The engineering here is not thin — let it speak.

### The upgraded one-sentence pitch

> **"Symphony is a real-time voice-security layer that listens to a live call, decides whether the voice is real, whether it is the claimed person, and whether the action being requested should be trusted — proven on Indian languages and Indian telephony, where the published state of the art fails outright."**

The final clause is no longer an assertion. See §11 / Moat A1 — it is now a citable published result.

---

## 1. The Workcycle at a Glance

Five phases. Not a pipeline — a **cycle**, because Phase V feeds back into Phases II, III and IV.

```
        ┌──────────────────────────────────────────────────────────┐
        │                                                          │
        ▼                                                          │
  ┌───────────┐   ┌───────────┐   ┌───────────┐   ┌───────────┐   │
  │  PHASE I  │──►│  PHASE II │──►│ PHASE III │──►│  PHASE IV │───┤
  │  INTAKE   │   │  ANALYSIS │   │  FUSION   │   │ DECISION  │   │
  │ "Listen"  │   │  "Score"  │   │ "Harmony" │   │"Conductor"│   │
  └───────────┘   └───────────┘   └───────────┘   └───────────┘   │
   Capture &       Parallel        Cross-expert    Context fusion  │
   conditioning    forensic        + temporal      + policy        │
                   experts         belief          + action        │
                                                                   │
                                  ┌───────────┐                    │
                                  │  PHASE V  │◄───────────────────┘
                                  │ ASSURANCE │
                                  │  "Coda"   │
                                  └─────┬─────┘
                                        │
                Explain · Audit · Calibrate · Retrain · Harden
                                        │
                                        └──► back to II / III / IV
```

| Phase | Name | One-line mandate | Owns the question |
|:--:|---|---|---|
| **I** | INTAKE | Turn a degraded network stream into clean, labelled, quality-scored evidence frames | *What am I actually hearing, and how good is it?* |
| **II** | ANALYSIS | Run independent forensic experts in parallel over each frame | *What does each instrument say, on its own?* |
| **III** | FUSION | Combine experts by condition, then accumulate belief across time | *What do they say together, and how sure am I so far?* |
| **IV** | DECISION | Fuse voice belief with caller, transaction and behavioural context; act | *Given everything, should this action be allowed?* |
| **V** | ASSURANCE | Explain the decision, preserve it as evidence, and feed learning back | *Can I prove why, and get better next time?* |

**Why exactly five.** Each boundary is a genuine change in the *type* of object being handled, which is what makes them clean service boundaries:

- I→II: raw signal becomes **conditioned frames + quality vector**
- II→III: frames become **independent expert scores**
- III→IV: scores become **a single calibrated belief with uncertainty**
- IV→V: belief becomes **an action taken**
- V→II/III/IV: action becomes **labelled experience**

If a proposed component doesn't change the object type, it belongs *inside* a phase, not as a sixth phase. This is the rule that keeps scope from creeping.

---

## 2. The Overlap Model — phases run concurrently, not sequentially

This is the most misunderstood property of the system and the one a technical judge will probe. **At any instant during a live call, all five phases are executing simultaneously on different slices of the same call.**

### 2.1 Concurrency timeline (single call, first 3 seconds)

```
  t=0ms      500ms       1000ms      1500ms      2000ms      2500ms     3000ms
  │           │           │           │           │           │          │
I ████████████████████████████████████████████████████████████████████████  continuous
  │                                                                       
II  ░░██░░██░░██░░██░░██░░██░░██░░██░░██░░██░░██░░██░░██░░██░░██░░██░░██    per hop (250ms)
  │   ▲                                                                    
III  ░░░███░░███░░███░░███░░███░░███░░███░░███░░███░░███░░███░░███░░███     per hop, stateful
  │      ▲                                                                 
IV    ░░░░░█░░░░░█░░░░░█░░░░░█░░░░░█░░░░░█░░░░░█░░░░░█░░░░░█░░░░░█░░░░░█    per hop + on event
  │        ▲                                                               
V     ░░░░░░▓░░░░░▓░░░░░▓░░░░░▓░░░░░▓░░░░░▓░░░░░▓░░░░░▓░░░░░▓░░░░░▓░░░░░▓   append-only
  │         ▲                                                              
  │         │
  │         └── first provisional risk published here (~300–500ms)
  │
  └── Phase I is *never* idle. Phases II–V lag it by one hop and repeat forever.
```

Legend: `█` active · `░` waiting for data · `▓` writing evidence

**Three consequences to state out loud when asked:**

1. **Phase I has no downstream dependency.** It must never block on Phase II. If inference is slow, frames queue or drop — audio capture does not stall. This is why Redis Streams sits between I and II rather than a direct function call.
2. **Phase III is the only stateful phase per call.** Phases I, II and IV are functionally stateless given their inputs, which is what makes horizontal scaling honest rather than aspirational. Session state lives in exactly one place.
3. **Phase IV can fire out of band.** A context event (new beneficiary added mid-call, transaction tier escalates) triggers a Phase IV re-decision *without* new audio. The risk score can rise while the caller is silent — and it should.

### 2.2 The two clocks

The blueprint's distinction between *inferential latency* and *evidence latency* is the reason the overlap model exists. Symphony runs two clocks against different budgets:

| Clock | Cadence | Purpose | Reliability |
|---|---|---|---|
| **Fast clock** | every 100–250 ms hop | provisional risk update, live UI, dashboard motion | low individually, useful in aggregate |
| **Slow clock** | 1–3 s rolling window | call-level verdict, action-grade decision | high, this is what policy acts on |

**Never let a slide imply a single number arrives at a single moment.** The defensible claim is: *sub-500 ms provisional update, action-grade verdict at 1–2 s of accumulated speech.* Both Pindrop and ValidSoft navigate exactly this gap publicly; naming it makes you look like you've read the field, not like you're hedging.

---

## 3. Master Architecture — Exhaustive

```
════════════════════════════════════════════════════════════════════════════════════════
  PHASE I — INTAKE ("Listen")                                    budget: 45–95 ms
════════════════════════════════════════════════════════════════════════════════════════
   SIP/RTP        WebRTC/SRTP      Enterprise SDK        Batch / Forensic
   (PSTN trunk)   (browser/app)    (AudioWorklet)        (uploaded file)
        │               │                 │                     │
        └───────────────┴────────┬────────┴─────────────────────┘
                                 ▼
                    ┌────────────────────────────┐
                    │  I.1  STREAM GATEWAY        │  jitter buffer, packet-loss
                    │       normalise to PCM      │  concealment, resample
                    └─────────────┬──────────────┘
                                  ▼
                    ┌────────────────────────────┐
                    │  I.2  CHANNEL PROFILER      │  codec ID (G.711 µ/A, AMR,
                    │       → codec_vec           │  AMR-WB, Opus), bandwidth,
                    └─────────────┬──────────────┘  bitrate, packet-loss %
                                  ▼
                    ┌────────────────────────────┐
                    │  I.3  QUALITY ESTIMATOR     │  SNR, clipping, reverb,
                    │       → q_t ∈ [0,1]         │  DC offset, silence ratio
                    └─────────────┬──────────────┘
                                  ▼
                    ┌────────────────────────────┐
                    │  I.4  VAD + PRE-ROLL BUFFER │  gate expensive inference;
                    │       speech / non-speech   │  keep 100ms pre-roll so
                    └─────────────┬──────────────┘  phoneme onsets aren't clipped
                                  ▼
                    ┌────────────────────────────┐
                    │  I.5  DIARISATION LITE      │  who is talking now?
                    │       + turn segmentation   │  caller / agent / overlap
                    └─────────────┬──────────────┘
                                  ▼
                    ┌────────────────────────────┐
                    │  I.6  LANGUAGE / CODE-SWITCH│  ⚑ MOAT A2
                    │       BOUNDARY TAGGER       │  frame-level lang ID,
                    │       → lang_t, switch_flag │  NOT utterance-level
                    └─────────────┬──────────────┘
                                  ▼
                         ═══ FRAME OBJECT F_t ═══
                    {pcm, t_start, t_end, codec_vec, q_t,
                     is_speech, speaker_turn, lang_t, switch_flag}
                                  │
                          [ Redis Stream: frames ]
                                  │
════════════════════════════════════════════════════════════════════════════════════════
  PHASE II — ANALYSIS ("Score")                                  budget: 30–110 ms
  ── five experts, executed in parallel, no expert sees another's output ──
════════════════════════════════════════════════════════════════════════════════════════
                                  │
      ┌───────────┬───────────────┼───────────────┬───────────────┐
      ▼           ▼               ▼               ▼               ▼
 ┌─────────┐ ┌─────────┐   ┌────────────┐  ┌───────────┐  ┌────────────┐
 │ E1      │ │ E2      │   │ E3         │  │ E4        │  │ E5         │
 │ SPECTRO-│ │ RAW     │   │ SSL        │  │ SPEAKER   │  │ PROSODY /  │
 │ TEMPORAL│ │ WAVEFORM│   │ FOUNDATION │  │ VERIF.    │  │ BEHAVIOUR  │
 ├─────────┤ ├─────────┤   ├────────────┤  ├───────────┤  ├────────────┤
 │CQT/LFCC │ │ x[n] →  │   │WavLM/XLSR  │  │ECAPA embed│  │F0 contour  │
 │log-spec │ │ sinc-   │   │(frozen)    │  │  ↓        │  │energy      │
 │  ↓      │ │ conv    │   │  ↓         │  │cos(e_c,e_r)│ │speech rate │
 │CNN enc  │ │  ↓      │   │PROBED LAYER│  │  ↓        │  │pause stats │
 │  ↓      │ │ res     │   │SELECTION ⚑ │  │calibrated │  │jitter/     │
 │graph    │ │ blocks  │   │(A8)        │  │likelihood │  │shimmer     │
 │attention│ │  ↓      │   │  ↓         │  │           │  │turn latency│
 │(AASIST) │ │ GRU/attn│   │proj head   │  │           │  │            │
 │  ↓      │ │  ↓      │   │  ↓         │  │           │  │            │
 │p_spec   │ │ p_raw   │   │p_ssl       │  │p_spk      │  │p_beh       │
 │+ frame  │ │ + frame │   │+ FRAME-LVL │  │           │  │            │
 │  logits │ │  logits │   │  LOGITS ⚑A3│  │           │  │            │
 └────┬────┘ └────┬────┘   └─────┬──────┘  └─────┬─────┘  └─────┬──────┘
      │           │              │               │              │
      │      ┌────┴──────────────┴───┐           │              │
      │      │ E6 REPLAY / LIVENESS   │          │              │
      │      │ channel + re-record    │          │              │
      │      │ artefacts → p_rep      │          │              │
      │      └────────────┬───────────┘          │              │
      └───────────┬───────┴──────────────────────┴──────────────┘
                  ▼
           ═══ EVIDENCE VECTOR E_t ═══
      {p_spec, p_raw, p_ssl, p_spk, p_beh, p_rep,
       frame_logits[], expert_confidences[], q_t, codec_vec, lang_t}
                  │
════════════════════════════════════════════════════════════════════════════════════════
  PHASE III — FUSION ("Harmony")                                 budget: <15 ms
════════════════════════════════════════════════════════════════════════════════════════
                  ▼
     ┌──────────────────────────────────┐
     │ III.1  QUALITY-CONDITIONED        │   w_i = f(q_t, codec_vec)
     │        EXPERT WEIGHTING           │   z_t = Σ w_i(q_t)·p_i
     │        (weights are a function    │   ← NOT a static average
     │         of channel, not fixed)    │
     └──────────────┬───────────────────┘
                    ▼
     ┌──────────────────────────────────┐
     │ III.2  CALIBRATION                │   temperature / isotonic;
     │        raw logit → true prob      │   a "0.8" must mean 0.8
     └──────────────┬───────────────────┘
                    ▼
     ┌──────────────────────────────────┐
     │ III.3  TEMPORAL BELIEF ACCUM.     │   log O_t = log O_{t-1} + log LR_t
     │        Bayesian log-odds          │   P_t = O_t / (1 + O_t)
     │        + evidence decay           │   ← the score that "rises live"
     └──────────────┬───────────────────┘
                    ▼
     ┌──────────────────────────────────┐
     │ III.4  SEGMENT LOCALISER  ⚑ A3    │   frame_logits → contiguous
     │        partial-spoof spans        │   synthetic spans + timestamps
     └──────────────┬───────────────────┘
                    ▼
     ┌──────────────────────────────────┐
     │ III.5  CODE-SWITCH STABILITY ⚑ A2 │   suppress score spikes that
     │        GUARD                      │   coincide with switch_flag
     └──────────────┬───────────────────┘   unless corroborated
                    ▼
     ┌──────────────────────────────────┐
     │ III.6  UNCERTAINTY BANDING        │   → GENUINE / UNCERTAIN /
     │        confidence ⟂ probability   │     SYNTHETIC-HIGH-CONF
     └──────────────┬───────────────────┘   never a forced binary
                    ▼
        ═══ VOICE BELIEF STATE V_t ═══
   {P_spoof, confidence, band, spans[], q_call, trajectory[]}
                    │
════════════════════════════════════════════════════════════════════════════════════════
  PHASE IV — DECISION ("Conductor")                              budget: <20 ms
════════════════════════════════════════════════════════════════════════════════════════
                    │
        ┌───────────┴───────────────────────────────┐
        ▼                                           ▼
 ┌──────────────────────────┐          ┌────────────────────────────┐
 │ CONTEXT INTELLIGENCE      │          │  VOICE BELIEF STATE V_t    │
 ├──────────────────────────┤          └─────────────┬──────────────┘
 │ • CNAP verified name ⚑ A5 │                        │
 │ • caller number reputation│                        │
 │ • number age / port hist. │                        │
 │ • device & network signals│                        │
 │ • transaction tier 0–4    │                        │
 │ • beneficiary novelty     │                        │
 │ • velocity / time-of-day  │                        │
 │ • social-engineering cues │                        │
 │   (urgency, callback      │                        │
 │    refusal, secrecy)      │                        │
 └────────────┬─────────────┘                        │
              └──────────────┬─────────────────────--┘
                             ▼
              ┌────────────────────────────────┐
              │ IV.1  RISK FUSION (XGBoost /    │  logit(R) = b + Σ w_k·x_k
              │       LightGBM + logit prior)   │  emits feature importances
              └───────────────┬────────────────┘
                              ▼
              ┌────────────────────────────────┐
              │ IV.2  TRANSACTION-SENSITIVITY   │  same R means different
              │       MODULATION                │  things at Tier 0 vs Tier 4
              └───────────────┬────────────────┘
                              ▼
              ┌────────────────────────────────┐
              │ IV.3  POLICY ENGINE +           │  UNKNOWN → MONITORING →
              │       RISK STATE MACHINE        │  TRUSTED / VERIFY / HIGH_RISK
              └───────────────┬────────────────┘
                              ▼
        ┌──────────┬──────────┼──────────┬───────────────┐
        ▼          ▼          ▼          ▼               ▼
     ALLOW       WARN     STEP-UP     HOLD &        ACTIVE LIVENESS
                          (MFA /      ESCALATE      CHALLENGE
                          callback)                 (semantic, not
                                                     fixed-phrase)
        └──────────┴──────────┴──────────┴───────────────┘
                              │
════════════════════════════════════════════════════════════════════════════════════════
  PHASE V — ASSURANCE ("Coda")                                   budget: async
════════════════════════════════════════════════════════════════════════════════════════
                              ▼
     ┌───────────────────────────────────────────────────┐
     │ V.1  EXPLANATION RENDERER                          │
     │      feature-importance bars · risk trajectory ·   │
     │      flagged spans on a timeline ⚑A3 · evidence    │
     │      list in plain language                        │
     └────────────────────┬──────────────────────────────┘
                          ▼
     ┌───────────────────────────────────────────────────┐
     │ V.2  COMPLIANCE EVIDENCE RECORD  ⚑ MOAT A6         │
     │      signed, append-only, hash-chained:            │
     │      call_id · model_version · codec · q · scores  │
     │      · context features · decision · timestamp     │
     │      → designed as a "reasonable precautions"      │
     │        artifact under Indian regulation ⚠verify    │
     └────────────────────┬──────────────────────────────┘
                          ▼
     ┌───────────────────────────────────────────────────┐
     │ V.3  PRIVACY LIFECYCLE                             │
     │      raw audio buffer auto-expires (seconds);      │
     │      only feature vectors + risk events persist;   │
     │      speaker embeddings, never enrollment audio    │
     └────────────────────┬──────────────────────────────┘
                          ▼
     ┌───────────────────────────────────────────────────┐
     │ V.4  ANALYST FEEDBACK LOOP                         │
     │      confirmed fraud / confirmed false positive →  │
     │      labelled sample                               │
     └────────────────────┬──────────────────────────────┘
                          ▼
     ┌───────────────────────────────────────────────────┐
     │ V.5  RECALIBRATION & HARDENING                     │
     │      threshold re-tuning · drift detection ·       │
     │      new-generator ingestion · red-team replay     │
     └────────────────────┬──────────────────────────────┘
                          │
        ┌─────────────────┼──────────────────┐
        ▼                 ▼                  ▼
   → Phase II         → Phase III        → Phase IV
   (retrain /         (recalibrate       (re-tune policy
    fine-tune)         weights)           thresholds)
```

---

## 4. Cross-Phase Data Contracts

This table is what lets four people build in parallel. **Freeze these field names before anyone writes code.** Every integration bug you avoid this week is an hour you don't lose at hour 30 of the finale.

| Object | Emitted by | Consumed by | Fields | Cadence |
|---|---|---|---|---|
| `FrameObject F_t` | I | II | `pcm[]`, `t_start`, `t_end`, `codec_vec`, `q_t`, `is_speech`, `speaker_turn`, `lang_t`, `switch_flag` | every hop (100–250 ms) |
| `EvidenceVector E_t` | II | III | `p_spec`, `p_raw`, `p_ssl`, `p_spk`, `p_beh`, `p_rep`, `frame_logits[]`, `expert_conf[]`, passthrough of `q_t`/`codec_vec`/`lang_t` | every hop |
| `VoiceBelief V_t` | III | IV, V | `P_spoof`, `confidence`, `band`, `spans[]`, `q_call`, `trajectory[]` | every hop |
| `ContextVector C_t` | external + IV | IV | `cnap_state`, `number_rep`, `txn_tier`, `beneficiary_new`, `velocity`, `se_cues[]`, `device_sig` | on change + every hop |
| `Decision D_t` | IV | V, API caller | `risk`, `action`, `state`, `reason_codes[]`, `top_features[]`, `confidence` | every hop + on context event |
| `EvidenceRecord` | V | audit store | full `D_t` + `V_t` + `C_t` + `model_version` + `hash_prev` | append-only, per decision |

**Contract rule:** a phase may only read fields declared in its input object. If Phase IV wants raw audio, that is a design error — it wants a *feature*, and the feature belongs in Phase I or II. This single rule prevents the architecture from silently collapsing into a monolith under time pressure.

---

## 5. Phase I — INTAKE ("Listen")

**Mandate:** produce clean, labelled, honestly quality-scored frames from a hostile network stream, and never stall.

### 5.1 Ideation

The naive version of this system starts at "load a .wav file." That version can never be real-time, can never be codec-aware, and can never be deployed. Phase I exists because **the detector never sees what the attacker generated** — it sees the signal after a codec, a network, and a room have all had their way with it. Every design decision in Phase I follows from treating degradation as a first-class input rather than noise to be removed.

The second, subtler idea: Phase I is where Symphony decides *how much to trust itself later*. The quality vector `q_t` computed here propagates all the way to Phase III's expert weighting and Phase IV's confidence output. Getting `q_t` right is worth more than a marginal gain in classifier accuracy, because a confident wrong answer on bad audio is the failure mode that destroys trust in a security product.

### 5.2 Stage detail

| Stage | Function | MVP (internal round) | Target |
|---|---|---|---|
| I.1 Stream gateway | jitter buffer, PLC, PCM normalisation, resample | mic → WebSocket → PCM | SIP/RTP tap via Asterisk testbed |
| I.2 Channel profiler | codec identification, bandwidth, loss % | detect 8k vs 16k, report bandwidth | full codec classifier + loss/jitter telemetry |
| I.3 Quality estimator | SNR, clipping, reverb, silence ratio → `q_t` | SNR + clipping only | full multi-factor `q_t`, calibrated |
| I.4 VAD + pre-roll | gate inference, preserve onsets | energy VAD + 100 ms pre-roll | neural VAD, tuned for Indian telephony noise |
| I.5 Diarisation lite | speaker turn segmentation | assume single caller channel | 2-speaker turn tracking, overlap flagging |
| I.6 Language / code-switch tagger ⚑ | **frame-level** language ID + switch boundary flag | language ID per 1 s window | frame-level, boundaries at 20 ms resolution |

### 5.3 Why I.6 is not optional

Indian speech technology has a documented, architectural failure: most systems commit to a single language for an entire segment before processing. On intra-sentential Hindi-English switching — which is how a very large share of Indian banking calls actually sound — that means running English phonemes through a Hindi model or vice versa. Reported word-error-rate penalties on code-switched speech run in the 30–50% relative range for standard ASR.

The anti-spoofing analogue is worse than an accuracy penalty: a detector whose score is unstable at switch boundaries produces **false positives on genuine bilingual speakers**. That is a bank's nightmare — a system that flags its own real customers for speaking normally. I.6 exists so Phase III can tell the difference between "the acoustics changed because the speaker switched language" and "the acoustics changed because the voice is synthetic."

### 5.4 Failure modes to disclose honestly

- Very short utterances (<1 s of speech) — insufficient evidence, Phase I should mark `q_call` low rather than let downstream phases pretend otherwise
- Heavy overlapping speech — diarisation lite will degrade
- Codec identification on transcoded paths (multiple codecs in sequence) is unreliable; report as `codec: uncertain` rather than guessing

---

## 6. Phase II — ANALYSIS ("Score")

**Mandate:** run genuinely independent forensic experts in parallel, each reporting its own opinion and its own confidence, with no expert able to contaminate another.

### 6.1 Ideation

The reason for multiple experts is **not** ensembling for a marginal accuracy bump. It is that different experts fail on different things, and a security system's value comes from the fact that an attacker who defeats one has not defeated the others.

Concretely:
- **E1 (spectro-temporal)** sees frequency-domain artefacts. It degrades at 8 kHz where the top half of the spectrum simply does not exist.
- **E2 (raw waveform)** has no handcrafted feature assumptions and therefore survives narrowband conditions better — which is why its weight *rises* as quality drops.
- **E3 (SSL foundation)** brings multilingual pretraining, which is the single mechanism most directly serving Indian-language robustness.
- **E4 (speaker)** answers a different question entirely: not "is this synthetic" but "is this the enrolled person." A perfect clone of the wrong person still fails E4.
- **E5 (prosody/behaviour)** operates on timescales the acoustic experts ignore — pause regularity, turn latency, unnatural conversational smoothness.
- **E6 (replay/liveness)** catches the attack class that is neither TTS nor VC: a recording played into the call.

**Independence is the product.** If all six experts were trained on the same features with the same objective, you would have one expert with six names. Say this out loud when a judge asks why not just use the best single model.

### 6.2 Two cheap upgrades that punch above their cost ⚑ MOAT A8

**Probing-guided layer selection.** A frozen SSL backbone has many hidden layers, and the most discriminative layer for spoof detection is generally *not* the last one. Recent work uses lightweight gradient-boosted probes over frozen layer outputs to identify which layers carry spoof-relevant information, then fuses only those with a compact classifier — reporting meaningful cross-domain generalisation gains.

Why this is ideal for this team specifically: it requires **no backbone fine-tuning** (cheap, fast, low-VRAM), and the probe is an XGBoost model — the exact library already in the stack for Phase IV. One dependency, two uses. That is a genuinely good engineering story to tell.

**One-class objective.** Standard binary training teaches the model what *known* fakes look like, which is precisely the thing that does not transfer to unseen generators. One-class approaches (OC-Softmax and relatives) instead compact the *bonafide* distribution and treat everything outside it as suspect. Since Symphony's headline evaluation is unseen-generator generalisation, the training objective should match the metric being reported. Reporting a binary-trained model against an unseen-generator benchmark and being surprised by the result is a self-inflicted wound.

### 6.3 Frame-level logits are mandatory, not optional ⚑ MOAT A3

Every acoustic expert must emit **per-frame logits in addition to a window-level score.** This costs almost nothing at training time (frame-level supervision from segment labels) and unlocks Phase III's segment localiser. See §11/A3 for why this matters as a moat.

### 6.4 Expert-level failure disclosure

| Expert | Known weakness | Mitigation |
|---|---|---|
| E1 spectral | narrowband loss at 8 kHz | weight down via `q_t`; never sole detector |
| E2 raw | sensitive to gain/level shifts | augmentation with random gain during training |
| E3 SSL | pretraining-language bias | Indic adaptation + language-disjoint eval |
| E4 speaker | requires enrollment; useless for unknown callers | degrade gracefully to "no enrollment — E4 abstains" |
| E5 prosody | biological traits *can* be modelled by good generators — never claim these prove humanness | frame as "naturalness consistency," weak feature |
| E6 replay | overlaps with codec artefacts | conditioned on `codec_vec` from Phase I |

---

## 7. Phase III — FUSION ("Harmony")

**Mandate:** turn six independent, noisy, condition-dependent opinions into one calibrated belief with an honest uncertainty attached — and make that belief evolve credibly over the life of the call.

### 7.1 Ideation

Phase III is where Symphony stops being a classifier and becomes a *security system*. Three ideas carry it.

**Idea 1 — the weights are a function, not a constant.** A fixed ensemble average implicitly assumes all experts are equally reliable in all conditions. They are not, and the system already knows the conditions because Phase I measured them. Weighting experts by `q_t` and `codec_vec` is the difference between an ensemble and a *conditioned* ensemble.

Initial engineering priors, to be calibrated against validation data — never presented as tuned results until they are:

| Condition | Spectral | Raw | SSL |
|---|---:|---:|---:|
| 16 kHz clean | 0.35 | 0.30 | 0.35 |
| 8 kHz G.711 | 0.25 | 0.45 | 0.30 |
| Heavy noise | 0.20 | 0.50 | 0.30 |
| Severe compression | 0.15 | 0.55 | 0.30 |

**Idea 2 — belief accumulates, it does not reset.** Re-predicting from scratch every 250 ms throws away everything learned in the previous 250 ms. Bayesian log-odds accumulation (`log O_t = log O_{t-1} + log LR_t`) is both the statistically correct treatment and — not coincidentally — what makes the live demo compelling. A number that visibly climbs as a fraud call progresses tells a story. A number that jitters around 0.6 tells nothing.

Add **evidence decay** so that a long call doesn't become unfalsifiably confident from accumulated weak evidence: down-weight log-likelihood-ratio contributions from low-`q_t` frames, and cap per-hop contribution magnitude.

**Idea 3 — confidence is orthogonal to probability.** `P_spoof = 0.30` with high confidence means "probably genuine." `P_spoof = 0.30` with low confidence on poor audio means "I don't know." These must never render the same. The specific failure this prevents: **high model uncertainty being silently read as low attack probability.** That sentence belongs verbatim in the deck.

### 7.2 The segment localiser ⚑ MOAT A3

```
frame_logits[]  ──►  smoothing  ──►  threshold  ──►  contiguous span merge
                                                             │
                                                             ▼
                                          spans = [{t0: 41.2, t1: 44.6, p: 0.91}]
                                                             │
                                                             ▼
                            "Seconds 41–45 of this call are synthetic.
                             The rest is a live human."
```

This converts a binary verdict into a forensic finding, and it is the highest-impact-per-hour item in the whole document. See §11/A3.

### 7.3 The code-switch stability guard ⚑ MOAT A2

```
if switch_flag(t) and ΔP_spoof(t) > δ and not corroborated_by(E4, E5):
        damp the update — attribute the acoustic shift to the language switch
        log the event as `switch_damped` for later analysis
```

Crucially, **log every damping event.** If the guard is suppressing real detections you need to be able to prove it isn't — and the log is what lets you measure the switch-point false-positive rate that becomes a headline metric.

### 7.4 Output banding

```
Risk:           73
Confidence:     41
Audio quality:  POOR
Band:           UNCERTAIN
Spans:          none localised
Action hint:    STEP-UP VERIFICATION
```

---

## 8. Phase IV — DECISION ("Conductor")

**Mandate:** decide whether the *action being requested* should be trusted, given the voice evidence and everything else known about this call.

### 8.1 Ideation

This is the phase that separates Symphony from a deepfake detector, and it rests on one sentence that should probably be the single most-repeated line in the pitch:

> **The system is protecting an action, not an audio file.**

A 70% voice-risk score during a balance inquiry and a 70% score during a ₹5 crore transfer to a new beneficiary are the same number and completely different events. Any system that treats them identically is not a fraud system.

The second idea: **context can move the score without new audio.** If the caller adds a new beneficiary mid-call, Phase IV re-decides immediately. Risk is a property of the session, not of the waveform.

### 8.2 Context feature families

| Family | Features | Source |
|---|---|---|
| **Identity** | CNAP verified name state ⚑A5, claimed-vs-verified mismatch, enrollment presence | telco / CRM |
| **Number** | reputation, age, port history, prefix risk, known-fraud list | telco / internal |
| **Transaction** | tier 0–4, amount, beneficiary novelty, velocity, deviation from pattern | core banking |
| **Behavioural** | urgency language, callback refusal, secrecy request, verification-bypass language, unusual hour | Phase II E5 + optional NLP (roadmap) |
| **Technical** | device fingerprint, network origin, VoIP-vs-mobile indicator | gateway |

### 8.3 Transaction-sensitivity tiers

```
Tier 0  informational                    → tolerate high risk, log only
Tier 1  account information              → warn
Tier 2  credential / security operation  → step-up at moderate risk
Tier 3  financial transaction            → step-up at low-moderate risk
Tier 4  privileged authorisation         → hold at any elevated risk
```

The effective threshold **falls as the tier rises.** Do not use a single global threshold and then explain the tiers verbally — implement it, because a judge will ask to see it.

### 8.4 Policy and state machine

```
R < 0.30  ALLOW          UNKNOWN ──► MONITORING ──┬─[weak]────► TRUSTED
R < 0.60  WARN                                    ├─[ambiguous]► VERIFY
R < 0.80  STEP-UP                                 └─[strong]───► HIGH_RISK
R ≥ 0.80  HOLD & ESCALATE                                          │
                                                        BLOCK/HOLD ─► REVIEWED
```

Thresholds are placeholders until chosen against false-positive cost, false-negative cost and transaction value. **Say "placeholder" if they still are.** An honest placeholder beats a fabricated tuned number every single time, and a judge who catches one fabricated number re-reads your entire deck with suspicion.

### 8.5 Active liveness — fallback only

The passive detector runs first, always. Only an *uncertain* band triggers a challenge, and the challenge must be **semantic** (answer a question, repeat a randomly composed phrase) rather than a fixed phrase — a fixed phrase can be pre-synthesised by an attacker who knows the system. This is the correct ordering because active challenges cost user friction, and friction spent on genuine customers is the real cost of a security product.

---

## 9. Phase V — ASSURANCE ("Coda")

**Mandate:** make every decision explainable, preserve it as evidence, and convert operational experience back into model improvement. This phase is what makes it a *cycle*.

### 9.1 Ideation

Most hackathon systems end at Phase IV. Phase V is where three separate kinds of value live, and each maps to a different stakeholder:

- **The agent** needs to know *why* right now, in plain language, in under two seconds.
- **The institution** needs a defensible record months later, when a customer disputes a loss.
- **The system itself** needs labelled experience, or it decays as generators improve.

### 9.2 V.1 — Explanation

```
WHY WAS THIS CALL FLAGGED?                    RISK 94  ·  CONFIDENCE 91

  synthetic speech probability      ████████████████░░░░   +34
  speaker embedding mismatch        ███████████░░░░░░░░░   +23
  high transaction sensitivity      █████████░░░░░░░░░░░   +18
  new beneficiary                   ██████░░░░░░░░░░░░░░   +12
  verification-bypass language      ████░░░░░░░░░░░░░░░░    +7

  RISK TRAJECTORY   ▁▁▂▃▃▄▆▇███       flagged spans: 41.2s – 44.6s
  AUDIO QUALITY     0.82  (good)      codec: G.711 µ-law, 8 kHz
```

Saliency and attention overlays are permitted **only when labelled as model attribution** — never as proof that "this frequency is fake." Overclaiming here is the fastest way to lose a technically literate judge.

### 9.3 V.2 — The compliance evidence record ⚑ MOAT A6

Append-only, hash-chained, signed, one record per decision. Contains: call ID, model version, codec, audio quality, all expert scores, context features, fused risk, confidence, action taken, timestamp, and the hash of the previous record.

**This is not a logging feature.** See §11/A6 — under India's current regulatory posture it is arguably the most commercially valuable single component in the system.

### 9.4 V.3 — Privacy lifecycle

- Raw audio buffers auto-expire within seconds; only feature vectors and risk events persist
- Speaker **embeddings** stored, never enrollment recordings, wherever policy allows
- Edge feature extraction option so raw audio need not leave the institution
- Explicit consent and retention policy defined *before* any self-recorded corpus is collected

This is not decoration. Bank and government procurement asks about it in the first meeting, and the DPDP framework makes it a live obligation rather than a nice-to-have. ⚠ Verify current DPDP Rules status with counsel before making compliance claims on a slide.

### 9.5 V.4 / V.5 — The learning loop

```
analyst marks call        ──►  labelled sample
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        ▼                           ▼                           ▼
  retrain / adapt            recalibrate                 re-tune policy
  Phase II experts           Phase III weights           Phase IV thresholds
  (weekly / on drift)        (nightly)                   (on FP-rate breach)
```

Add **drift detection**: monitor the distribution of `P_spoof` on known-genuine traffic. If it shifts, either the channel changed or a new generator arrived. Both are worth an alert.

---

## 10. Phase → Moat → Slide Traceability

Every phase must earn its place on a slide, or it is engineering the jury never sees.

| Phase | Primary moats served | Deck slide | Demo-visible? |
|---|---|---|---|
| I | A2 (code-switch), codec-awareness | 4 architecture | quality/codec badge |
| II | A1 (Indic), A4 (NAC), A8 (probing/one-class) | **5 innovation** | expert score panel |
| III | A3 (localisation), A2, uncertainty banding | **5 innovation**, 8 prototype | **the climbing score — the demo's centrepiece** |
| IV | A5 (CNAP), transaction tiers | 3 solution, 7 impact | action card, tier badge |
| V | A6 (compliance evidence), A7 (protocol) | 7 impact, 10 references | explanation panel |

---

## 11. Augmented Moats — Researched Additions

These extend §7 of the blueprint. Ranked by **jury impact ÷ build cost**. Each carries an honest caveat, because a moat that collapses under one question is worse than no moat.

---

### ⚑ A1 — The published-failure benchmark *(highest impact, near-zero cost)*

**The finding.** Recent published work benchmarking AASIST and RawNet2 on IndicSynth **without domain adaptation reports EERs exceeding 50% across most Indic languages — against sub-1% EER on ASVspoof 2019.**

Read that again. An equal error rate above 50% is *worse than a coin flip*. The published state of the art in audio anti-spoofing does not merely degrade on Indian languages; on this benchmark it inverts.

**Why this changes the pitch.** Your Indian-language slide currently says "existing detectors probably don't generalise to Indian speech." It can now say: *"Here is the published number. Sub-1% on English benchmarks. Over 50% on Indic. That is the gap, and here is ours."*

This converts your headline moat from an assertion a judge must take on faith into a **citable fact with a number attached** — which is exactly the kind of evidence the blueprint already identifies as what wins rounds. It is the single highest-leverage change in this entire document, and it costs one citation.

**Supporting resources now available:**

| Resource | Scale | Use |
|---|---|---|
| **IndicSynth** (ACL 2025, Outstanding Paper, IIIT-Delhi) | ~4,000 h synthetic, 989 target speakers, 12 Indian languages, mimicry + diversity subsets | Primary Indic spoof corpus |
| **MLAAD** (Fraunhofer) | 76k+ utterances, 23 languages, 54 generation systems | Cross-lingual generalisation test |
| **Indic-CodecFake** | Neural-audio-codec spoofs over IndicSUPERB | Emerging generator class — see A4 |
| **IndicVoices** (AI4Bharat) | 22 languages, 22,563 speakers, ~12,000 h | Bonafide speaker diversity |

⚠ **Caveats you must state, not hide:**
1. **IndicSynth is released under CC BY-NC 4.0 — non-commercial academic research only.** Fine for SIH and for publication. Not fine for a commercial product claim. Your self-generated corpus remains necessary for any deployment story, and you should say so.
2. Indian research groups (IIIT-Delhi, IIT-Jodhpur and others) are already publishing actively in Indic audio deepfake detection. **Do not claim "nobody has worked on Indian-language detection."** That claim is false and a well-read judge will know it.
3. The honest and *stronger* claim: *"The datasets and the failure result now exist in the literature. What does not exist is a deployed, real-time, telephony-grade, contextually-fused system built on top of that finding. That is what we built."*

---

### ⚑ A3 — Partial-spoof localisation *(highest impact per engineering hour)*

**The gap.** The PartialSpoof line of research establishes that countermeasures trained on *fully* spoofed utterances **degrade substantially** when tested on partially spoofed audio — utterances where short synthetic segments are embedded inside genuine speech, at resolutions from 20 ms to 640 ms. Locating those injected segments is materially harder than utterance-level detection.

**Why this is the attack that matters here.** Consider the actual fraud: a live human handles the small talk in their own voice, then splices in a cloned phrase — *"transfer twenty-five lakh to the account I'm sending now"* — in the CEO's voice. Every whole-utterance detector on the market is evaluated against fully-synthetic calls. This attack sails through a system that averages a score over a 30-second window, because 28 of those seconds are genuinely human.

**This is a sixth attack class** and it belongs in the blueprint's §2.5 threat table:

| Attack | Description | Detection layer |
|---|---|---|
| **Partial / spliced spoof** | Short synthetic segments embedded in genuine speech | **Frame-level logits (II) → segment localiser (III.4)** |

**What it buys the demo.** Instead of "this call is 87% likely fake," Symphony renders a timeline with a red band and says: *"seconds 41 through 45 are synthetic; the rest of this call is a live human."* That is a forensic finding, not a classifier output, and no other team in the room will show one.

**Cost:** frame-level supervision on experts you are already training, plus smoothing and span-merge logic in Phase III. Low. **Payoff:** disproportionate.

⚠ Caveat: localisation precision degrades sharply below roughly 200 ms of synthetic content. State the resolution you actually achieve; don't imply 20 ms unless you measured 20 ms.

---

### ⚑ A6 — The compliance-evidence layer *(highest commercial value)*

**Why now specifically.** India's regulatory environment moved decisively in the first half of 2026, and the movement runs directly in favour of this product.

| Development | Effect |
|---|---|
| **MeitY IT Amendment Rules 2026** (G.S.R. 120(E), notified 10 Feb 2026, in force 20 Feb 2026) | First legal definition of "synthetically generated information"; labelling, provenance-metadata and traceability duties; sharply compressed takedown windows. Synthetic audio carries a spoken-disclosure requirement |
| **RBI April 2026 package** | Additional Factor of Authentication mandated across digital payment channels; Digital Banking Channels directions requiring real-time alerts and enhanced monitoring |
| **RBI draft Third Amendment Directions, 2026** (proposed effect from 1 July 2026) | Revised customer-liability framework for unauthorised electronic transactions, with defined bank-negligence criteria |

**The moat, stated precisely.** Two things follow from the above.

First, **the buyer now has a quantified financial reason to buy.** When liability for fraud losses shifts toward the institution, detection stops being a security cost centre and becomes loss-avoidance with a computable return. That is the difference between a nice demo and a purchase order.

Second, and more specific to Symphony: **an institution that took a voice call and authorised a transaction will, in a dispute, need to show what precautions it took.** A signed, hash-chained, per-call evidence record containing the model version, the audio quality, the risk trajectory, the evidence vector and the action taken is exactly that artifact. No incumbent markets this as an India-specific compliance product.

Reframe Phase V.2 accordingly: **not "we log things" but "we generate the evidence record your regulator and your dispute-resolution process will ask for."**

⚠ **Caveats — be disciplined here.** Regulation is where overclaiming is most dangerous, because a judge from a bank or a law background will know more than you do.
1. **This is not legal advice and the document must say so.** The team should read the actual gazette text, not summaries — including this one.
2. Several of these instruments were in draft or consultation as of mid-2026. **Verify current status before any slide states a rule is in force.**
3. The IT Rules 2026 obligations attach primarily to *intermediaries*, which is not the same category as a bank deploying an internal fraud control. Do not blur the two.
4. Say "designed to support" a reasonable-precautions showing, never "guarantees compliance."

---

### ⚑ A7 — The generator-confound control *(cheapest credibility signal available)*

**The trap.** You fine-tune on Hindi. EER improves. You put it on slide 5. A sharp judge asks: *"How do you know that's a language effect and not a generator effect?"*

If your Hindi data came from different TTS systems than your English data, your "language" result may be measuring **generator-specific artefacts, not linguistic properties.** This exact confound is flagged in the cross-lingual audio deepfake literature as a source of incorrect conclusions about language transferability.

**The control.** Hold the generator set constant across languages. Same generators produce your Hindi, Marathi and Indian-English spoofs. Then a difference across languages is a language difference, because it is the only thing that varied.

**Why this is worth slide space.** It costs nothing but discipline in data generation, and it lets you pre-empt the hardest question about your headline result *before it is asked.* Stating a confound you controlled for is the strongest possible signal that you understand your own experiment — and per the blueprint's own logic, juries reward rigor-that-anticipates-attack over unverifiable polish.

---

### ⚑ A5 — CNAP-fused caller identity *(newly available, India-only)*

**The development.** TRAI approved Calling Name Presentation in October 2025; national rollout proceeded through late 2025 into 2026, targeting broad availability around March 2026. CNAP displays a caller name drawn from the **operator's KYC-verified subscriber database** — not crowdsourced, unlike existing caller-ID apps — enabled by default with an opt-out.

**Why it is a moat.** This is a brand-new, high-quality, **India-only** identity signal that no foreign incumbent's context engine is wired into. Pindrop, ValidSoft, Nuance and ID R&D all built their context layers around North American and European telephony metadata. CNAP is a signal available to you and structurally unavailable to them.

**How Phase IV consumes it** — as a *prior*, never a decision:

| CNAP state | Signal |
|---|---|
| Present, matches claimed identity | mild trust prior |
| Present, **mismatches** claimed identity | **strong risk prior** — cheap, high-precision |
| Absent (opt-out or unregistered) | neutral; must not be penalised as suspicious |

⚠ Caveats: CNAP is not an anti-spoofing mechanism and should never be described as one; opt-out is legitimate and common; KYC database freshness is a known open concern; rollout coverage across networks and handsets ⚠ requires verification before the slide claims universality.

---

### ⚑ A2 — Code-switch-invariant detection *(distinctive, defensible, nobody measures it)*

Fully specified in §5.3 and §7.3. The moat in one line:

> **Symphony reports a metric no published detector reports: score stability across intra-sentential code-switch boundaries.**

Two headline numbers to target:
- **Switch-point false-positive rate** — FPR measured specifically on genuine Hinglish utterances containing switch boundaries, versus FPR on monolingual genuine speech
- **ΔEER across switch density** — EER on low-switch-density vs high-switch-density genuine speech

If your detector's false-positive rate spikes on genuine bilingual speakers, you have found a real bug that every English-trained competitor also has and none of them are measuring. Finding it, naming it, and fixing it is a better story than a marginally lower headline EER.

---

### ⚑ A4 — Neural-audio-codec generators as a named held-out family

Most anti-spoofing training data is dominated by **vocoder-based** TTS artefacts. Neural audio codec synthesis (the VALL-E family and successors) produces a structurally different artefact profile, and recent work has extended this specifically to Indic languages via codec-synthesised corpora built over IndicSUPERB.

**Symphony's response:** designate NAC as a **named held-out generator family** in the generator-disjoint split. Train on vocoder families, evaluate on NAC. This upgrades the unseen-generator claim from generic ("we held out a generator") to specific and current ("we held out the generator family that is actually displacing the one everyone trains on").

---

### ⚑ A8 — Probing-guided layers + one-class objective

Specified in §6.2. The moat is **engineering economy**: two techniques that target generalisation rather than in-domain accuracy, both cheap on a frozen backbone, one of which reuses a library already in the stack. When a judge asks how you got generalisation gains without a large compute budget, this is the answer, and it is a good one.

---

### Moat priority ranking

| Rank | Moat | Impact | Cost | Verdict |
|---|---|:--:|:--:|---|
| 1 | **A1** published Indic failure benchmark | ★★★★★ | ▪ | Do today. Rewrites slide 5 |
| 2 | **A3** partial-spoof localisation | ★★★★★ | ▪▪ | Do. Best demo payoff per hour |
| 3 | **A7** generator-confound control | ★★★★ | ▪ | Do. Pure discipline, no code |
| 4 | **A6** compliance evidence record | ★★★★ | ▪▪ | Do. Highest commercial value |
| 5 | **A2** code-switch invariance | ★★★★ | ▪▪▪ | Do if Tier 1 is live |
| 6 | **A8** probing + one-class | ★★★ | ▪▪ | Do during model work |
| 7 | **A5** CNAP fusion | ★★★ | ▪▪ | Simulate for demo; real integration is roadmap |
| 8 | **A4** NAC held-out family | ★★★ | ▪▪▪ | Fold into eval matrix if time permits |

---

## 12. Updated Evaluation Matrix

The blueprint's §9.3 table, extended with the augmented moats. **Populate it with real numbers as baselines land — an empty table on a slide is worse than no table.**

| System | Clean EER | 8 kHz EER | AMR EER | Noise EER | **Indic EER** | **Unseen-gen EER** | **NAC EER** | **PartialSpoof EER** | **Switch-point FPR** | p95 latency |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| SVM + MFCC (classical) | | | | | | | | | | |
| CNN baseline | | | | | | | | | | |
| AASIST (published) | | | | | *>50%* ⁽ᵃ⁾ | | | | | |
| RawNet2 (published) | | | | | *>50%* ⁽ᵃ⁾ | | | | | |
| SSL baseline (frozen) | | | | | | | | | | |
| + probed layers (A8) | | | | | | | | | | |
| + one-class objective (A8) | | | | | | | | | | |
| + codec augmentation | | | | | | | | | | |
| Dual-stream fusion | | | | | | | | | | |
| **Symphony (full)** | | | | | | | | | | |

⁽ᵃ⁾ Reported in published benchmarking of these architectures on IndicSynth without domain adaptation. ⚠ Read the source paper and cite the exact figure and condition — do not carry a range onto a slide.

**Splits, extended from blueprint §8:**

- A — speaker-disjoint
- B — generator-disjoint *(now including NAC as a named held-out family, A4)*
- C — channel-disjoint (G.711 / AMR / loss / noise / replay)
- D — language-disjoint *(with generator held constant across languages, A7)*
- E — compound attacks (synthetic + codec + noise + replay)
- **F — partial-spoof split** *(new, A3)* — utterance-level and segment-level metrics reported separately
- **G — code-switch density split** *(new, A2)* — genuine speech stratified by switch density

---

## 13. Build Sequencing — MVP vs Target, per phase

**Rule that governs everything below:** the blueprint is right that a beautiful deck describing a system that doesn't run is the most common way a strong team gets cut. Every phase therefore has a **thin but real** MVP. Thin and running beats thick and theoretical.

| Phase | Thin-but-real MVP | Target |
|---|---|---|
| **I** | mic → WebSocket → PCM, energy VAD, SNR-only `q_t`, 1 s language ID | SIP/RTP via Asterisk, full codec profiler, neural VAD, frame-level switch tagging |
| **II** | E3 (frozen SSL + head) + E1 (AASIST-style), frame logits on both | all six experts, probed layers, one-class objective |
| **III** | quality-weighted average + log-odds accumulator + banding | full conditioned weighting, segment localiser, switch guard, calibration |
| **IV** | XGBoost over 6–8 context features, 4-band thresholds, tier modulation | full context families, CNAP, state machine, active liveness |
| **V** | explanation bar chart + JSON evidence record | signed hash-chained store, privacy lifecycle, feedback loop, drift detection |

**Critical-path order.** III before IV. The climbing risk score is the demo, and it lives in Phase III. A polished Phase IV policy engine attached to a flat, jittery Phase III score demos worse than a rough Phase IV attached to a belief curve that visibly rises. Build the thing the audience actually watches.

---

## 14. Honest Limitations — the slide that buys credibility

Per phase, stated plainly, framed as next iteration:

| Phase | Limitation |
|---|---|
| I | Codec ID unreliable on transcoded paths; diarisation degrades on overlapping speech |
| II | E4 abstains without enrollment; E5 prosody features are weak and can be modelled by good generators |
| III | Localisation resolution degrades below ~200 ms of synthetic content; long calls need evidence decay to avoid false confidence |
| IV | Thresholds are cost-model placeholders until tuned against real FP/FN costs; CNAP integration is simulated, not live |
| V | Compliance-evidence design is informed by public regulatory summaries, not legal review |

**System-wide, unchanged from the blueprint and still true:** very short utterances and adversarially post-processed clones remain the weakest cases. Say so. It costs nothing and it is the cheapest credibility signal in the deck.

---

## 15. The Honesty Statement

If a judge asks *"what is actually new here?"*, this is the answer — and it should be delivered without defensiveness, because it is a strong answer:

> None of the individual components is unprecedented. AASIST, SSL-based detection, speaker-aware anti-spoofing, commercial voice biometrics and transaction-level voice security all exist. What does not exist publicly is **a real-time, telephony-grade system built specifically against the published finding that leading anti-spoofing architectures exceed 50% EER on Indian languages** — combined with segment-level localisation of partial spoofs, code-switch-stable scoring, a generator-controlled evaluation protocol, and a compliance-grade evidence record designed for the Indian regulatory environment as it stands in 2026. The novelty is the **combination, the evaluation protocol, and the deployment context** — and it is reproducible, which is more than any incumbent offers.

---

## 16. Verification Queue — before any of this reaches a slide

- [ ] Read the primary source reporting >50% Indic EER for AASIST/RawNet2; record exact figures, conditions and citation (⚑A1 — **highest priority, this is the headline number**)
- [ ] Confirm IndicSynth licence terms (CC BY-NC 4.0) and access process; confirm SIH use is compatible
- [ ] Read the PartialSpoof paper; record achievable segment resolution and utterance-level EER for the comparison table
- [ ] Read MeitY G.S.R. 120(E) gazette text directly; confirm in-force status and scope of intermediary obligations
- [ ] Confirm current status of RBI Third Amendment Directions, 2026 (draft vs notified) before any liability claim
- [ ] Confirm CNAP rollout coverage as of the pitch date
- [ ] Verify the CERT-In advisory referenced in blueprint §13
- [ ] Confirm Tier 1 end-to-end run — **still the single gating item ahead of all slide work**
- [ ] Download the official SIH PPT template; map §10 traceability onto its actual slide count
- [ ] Confirm the internal-round time cap with the college

---

## 17. One-Page Summary

**Symphony** is a five-phase workcycle, not a pipeline. All five phases run concurrently on a live call.

**I INTAKE** conditions the signal and measures its own trustworthiness, tagging language at frame level.
**II ANALYSIS** runs six independent forensic experts in parallel, each emitting frame-level logits.
**III FUSION** weights experts by channel condition, accumulates belief in log-odds across time, localises synthetic spans, and reports uncertainty separately from probability.
**IV DECISION** fuses voice belief with caller, transaction and behavioural context, modulates by transaction tier, and acts.
**V ASSURANCE** explains, preserves signed evidence, and feeds labelled experience back into II, III and IV — closing the cycle.

**The moat is no longer a claim.** Published benchmarking puts leading anti-spoofing architectures above 50% EER on Indian languages against sub-1% on English. That is the gap. Symphony is built to close it, to localise partial spoofs inside otherwise-genuine calls, to stay stable across Hinglish code-switching, to prove its language result is not a generator artefact, and to leave behind an evidence record the Indian regulatory environment now effectively demands.

**Today's only priority remains Tier 1 running end-to-end.** Everything in this document is worthless attached to a system that doesn't run.

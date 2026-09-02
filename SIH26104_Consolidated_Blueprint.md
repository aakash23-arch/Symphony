# SIH26104 — Real-Time Voice Cloning Detection
## Consolidated Research & Build Document

**Problem Statement:** AI-Powered Real-Time Detection and Prevention of Voice Cloning Impersonation Attacks
**Target Environment:** Indian banking, enterprise, government, and telecom voice channels

---

### Document Purpose

This document merges three separate research passes into one reference: (1) the finalized feature-set and slide-structure lock, (2) the production-grade technical deep-dive (architecture, DSP, models, competitive landscape, roadmap), and (3) the final locked model stack and 10-slide internal-round deck. Where the three threads disagreed or evolved, the **most recent/most specific version is treated as canonical** and earlier versions are folded in as supporting detail rather than duplicated.

---

## 1. The Core Thesis

> **"A real-time voice authenticity engine that catches cloned-voice fraud calls as they happen — tuned and proven for Indian languages and accents, where every existing public benchmark falls short."**

This sentence is the spine of the whole project. It does three jobs simultaneously:
1. Names the real problem (voice-channel impersonation fraud, not "deepfakes" in the abstract)
2. Names the specific technical claim (real-time + Indian-language robustness)
3. Implicitly explains why generic competitors lose to this team

A second framing, sharper and product-oriented, sits alongside it:

> **"A privacy-preserving, codec-aware, multilingual voice-security layer that continuously estimates whether a caller is real, whether they are the claimed speaker, and whether the action they are requesting should be trusted."**

The product is not "deepfake detection." It is **fraud-decisioning built on top of voice evidence.** Every architectural and slide decision below should trace back to one of these two sentences.

---

## 2. Problem Decomposition

### 2.1 What the attack actually is

Voice cloning fraud is better modeled as a full **impersonation chain**, not a single classification task:

```
Target identity → public speech samples collected → cloned via TTS/voice-conversion
   → attacker builds a social-engineering script → call goes over VoIP/PSTN
   → codec + packetization + jitter + noise degrade the signal
   → victim hears synthetic speaker → high-value action requested
   (fund transfer, beneficiary creation, privileged approval, credential disclosure)
   → fraud
```

The detector only ever observes the **final degraded signal** at the bottom of this chain — never the clean synthetic audio the attacker actually generated.

### 2.2 Generator landscape (why "recognize Model X" is the wrong task)

Representative modern generators: **HiFi-GAN** (adversarial vocoder for high-fidelity, efficient synthesis), **StyleTTS2** (style diffusion + adversarial training + SLM-derived discrimination, strong zero-shot speaker adaptation), **VALL-E** (neural codec language model — personalizes speech from a short prompt, preserving speaker identity, emotion, and acoustic environment).

The strategic implication: the detector's task must be framed as—

```
"Recognize the CLASS of synthetic/manipulated speech,
 including generators never seen in training."
```

— not "recognize the fingerprint of one known model." This generalization framing should be stated explicitly on the innovation slide.

### 2.3 Why telephony changes the problem fundamentally

Forensic artifacts present in raw generated audio can be destroyed or distorted by the transmission channel before the detector ever sees them.

- G.711 (PCMA/PCMU): 8-bit samples, 8 kHz sampling — narrowband
- AMR: 8 kHz / 20 ms frames; AMR-WB: 16 kHz

Signal path: `x_fake(t) → [codec] → x_c(t) → [network] → x_n(t) → [noise] → x'(t)`

The model must estimate **P(synthetic | x′)** — the degraded, in-the-wild signal — not P(synthetic | x_fake), the clean lab signal. This single distinction explains why lab-benchmark EER numbers routinely fail to hold up on real phone audio, and is the reason codec-aware training is treated as a first-class architectural requirement below, not an afterthought.

At 8 kHz, Nyquist frequency = 4 kHz — G.711 narrowband speech fundamentally restricts the usable spectrum and eliminates or severely distorts high-frequency cues that a 16 kHz-trained model may be silently relying on.

### 2.4 Four core technical bottlenecks

| # | Bottleneck | Core issue | Design response |
|---|---|---|---|
| A | Latency vs. statistical confidence | A 200ms segment carries far less evidence than 2–3s of speech | Don't force a hard verdict every 200ms — separate *instantaneous posterior* from *accumulated call-level posterior* via temporal aggregation |
| B | Narrowband information loss | A 16kHz model can't just be resampled to 8kHz and assumed equally discriminative | Give the model an explicit telephony-specific operating mode, not one universal 16kHz mode |
| C | Indian linguistic diversity | "Support Hindi" is not the same as "support Indian speech" — IndicVoices alone spans 22 languages, 22,563 speakers, ~12,000 hours across 208 districts | Architecturally separate *language identity* from *speech authenticity*; target P(spoof\|X, L_i) ≈ P(spoof\|X, L_j) across languages L_i, L_j |
| D | Unknown attacks | ASVspoof's own design deliberately holds out unseen attack algorithms at eval time; ASVspoof5 adds ~2,000 speakers, 32 attack algorithms, and adversarially optimized attacks | Accuracy against *known* generators is not the headline metric — generalization to unseen generators/channels is |

### 2.5 Threat model — five attack classes

| Attack | Description | Primary detection layer |
|---|---|---|
| TTS | Text converted into target voice | Synthetic-speech classifier |
| Voice conversion | Attacker's own voice transformed toward target identity | Synthetic + speaker verification |
| Replay | Genuine or synthetic recording played into the call | Replay / liveness detection |
| Post-processed deepfake | Generated audio altered after synthesis to evade detection | Robustness-hardened anti-spoof model |
| **Composite attack** | Synthetic voice **+** caller-ID spoofing **+** social engineering | **Full contextual risk engine** |

The fifth category is the one that actually matters for this problem statement: **the system is protecting an action, not an audio file.** This single sentence is the strongest justification for why a pure audio classifier is an insufficient product.

---

## 3. Competitive Landscape

This space is more crowded than the PS text suggests — the moat is not "we can detect deepfakes."

| Player | Positioning | Key point of note |
|---|---|---|
| **Pindrop** | Pulse (deepfake detection, ~2s) + Protect (near-real-time fraud alerts) | Combines metadata, number reputation, behavior, continuous scoring — already covers TTS, voice conversion, and replay |
| **Nuance / Microsoft Gatekeeper** | Voice biometrics + device/network/location + conversational signals + configurable AI risk engine + fraudster watchlists | Multi-signal risk fusion is *already* their core product, not a novel idea |
| **ID R&D (IDLive Voice)** | Liveness/anti-spoofing + voice biometrics, SDK/Docker deployable, multi-stage frame-level real-time detection | Edge/SDK deployment and passive anti-spoofing are also not unique |
| **ValidSoft (Voice Verity / VIP)** | Real-time 8kHz-telephony deepfake + replay detection, language-agnostic, no enrollment required; VIP (May 2026) launched around "real human / right human / right outcome" — deepfake detection + biometrics + fraud intelligence + transaction/intent binding | **Direct warning:** this is almost exactly the "detect → verify speaker → bind to transaction" concept this project is building. Recommends ~2s of speech despite being marketed as real-time — illustrates that *inferential* latency and *evidence* latency are different things |
| **Hiya / Loccus** | AI Voice Detection, ~1.5s of audio for real-time scam detection; public collaboration with ElevenLabs on deepfake-detection research | Consumer/carrier-scale deployment |
| **ElevenLabs** | AI Speech Classifier (provider-specific, doesn't cover their own v3 model or other providers) + separate watermark-based Audio Detector | Useful cautionary example: **watermark detection and forensic detection are different technologies** — a security system cannot assume the attacker used a watermarked generator |

**Capability comparison (qualitative):**

| Capability | Pindrop | Nuance | ID R&D | ValidSoft | Hiya/Loccus | **This project's target** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| Deepfake detection | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Replay detection | ✓ | ✓ | ✓ | ✓ | — | ✓ |
| Speaker verification | ✓ | ✓ | ✓ | ✓ | — | ✓ |
| Contextual risk | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Real-time/streaming | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 8kHz telephony focus | ✓ | ✓ | ✓ | ✓ | likely | ✓ |
| **Indian-language optimization** | not established | not established | not established | language-agnostic | not established | **Primary moat** |
| **Forensic transparency (public)** | limited | limited | limited | limited | limited | **Primary moat** |
| **Open, reproducible benchmark protocol** | proprietary | proprietary | proprietary | proprietary | proprietary | **Primary moat** |

**The right conclusion:** this project is *not* competing on the existence of deepfake detection. It is competing on **deployment context (Indian telephony), reproducibility, robustness testing under codec degradation, and a highly specific Indian-language threat model** that none of the incumbents have publicly established.

---

## 4. Final Locked Feature Set

### Tier 1 — Core System (must run live, non-negotiable)

1. Real-time audio ingestion & streaming inference — chunked/windowed processing, not batch
2. WavLM-based authenticity classifier (fine-tuned on ASVspoof/WaveFake) — primary detector
3. Contextual risk-scoring layer (XGBoost/LightGBM: acoustic score + call metadata — known/unknown number, request type, urgency signals) — explainable composite risk score, not a binary label
4. Configurable action thresholds (allow / verify / escalate / block)
5. API/SDK exposure for banking, telecom, and enterprise comms integration
6. Explainability layer — feature-importance-driven "why this was flagged"

### Tier 2 — Differentiators (spend slide time here — this wins the round)

1. **Indian multilingual & accent robustness** — self-generated cloned/genuine dataset in Hindi, Marathi, Indian-accented English (via open TTS: Coqui/XTTS/OpenVoice), with a documented before/after EER showing the gap closing. **This is the single strongest slide** — no other team in the room is likely to show a language-specific generalization result.
2. **Rigorous, benchmarked evaluation** — your model vs. published AASIST/RawNet2 numbers vs. your own classical SVM+MFCC baseline. One clean table, not scattered claims.
3. **Continuous session-level risk accumulation** — EMA / Bayesian belief update over the chunk-score stream, turning a static per-chunk number into a live, rising-in-real-time demo score.
4. **Unseen-generator generalization test** — train on generators A/B/C, evaluate on held-out generator D.
5. **Uncertainty-aware output** — genuine / uncertain / high-confidence-synthetic banding (calibrated confidence) instead of a forced binary decision.
6. **Explicit, honest failure-mode disclosure** — a slide stating what the system does *not* reliably catch yet (very short utterances, adversarially post-processed clones). Costs nothing to build and is the cheapest credibility signal in the deck — judges are trained to distrust teams claiming perfection.

### Tier 3 — Cut, Don't Build, Don't Mention

- No unrelated "extra" features (multilingual chatbot, blockchain logging, generic analytics dashboard) added purely to look more complete. Feature bloat reads as unfocused to an experienced jury.
- SVM appears **only** as one row in the baseline comparison table — never presented as a competing product idea.
- **Roadmap-only, one clearly labeled slide, never claimed as built:** conversation-intent/NLP fraud engine, speaker-consistency embedding tracking over time, cross-institution network-level fraud intelligence, full multi-condition attack-matrix stress testing, privacy-preserving federated retraining.

---

## 5. Model & Technical Stack Summary

| Component | Model / Method | Role |
|---|---|---|
| **Primary detector** | WavLM (or wav2vec2-XLSR), fine-tuned with a lightweight classification head | Core authenticity score; multilingual pretraining directly serves Indian-language robustness |
| **Published SOTA baseline** | AASIST or RawNet2 (cited / reference-implemented) | Evaluation-table comparison point, not the primary model |
| **Classical baseline** | MFCC/CQCC features + soft-margin SVM | The "before" in the before/after rigor story — cheap, standard, credible |
| **Contextual fusion** | XGBoost / LightGBM | Combines acoustic score + call metadata into one explainable risk score with feature importance |
| **Session logic** | Simple EMA or Bayesian log-odds update over chunk-level scores | Turns per-chunk predictions into a live, rising/falling session-risk narrative |
| **Uncertainty banding** | Calibration on top of the classifier's own softmax/probability output | Genuine / uncertain / high-confidence-synthetic labeling — no new model required |

**Training data:** ASVspoof + WaveFake (public) for the base model; a self-generated Hindi/Marathi/Indian-accented-English cloned/genuine set for adaptation and the headline result.

---

## 6. System Architecture

### 6.1 Full production architecture (target end-state, not the hackathon MVP)

```
                         ┌──────────────────────┐
                         │   SIP / RTP / WEBRTC │
                         └──────────┬───────────┘
                                    ▼
                         ┌──────────────────────┐
                         │ STREAM GATEWAY        │
                         │ jitter / packet loss  │
                         └──────────┬───────────┘
                                    ▼
                         ┌──────────────────────┐
                         │ AUDIO QUALITY LAYER   │
                         │ VAD / SNR / codec ID  │
                         └──────────┬───────────┘
                      ┌─────────────┼─────────────┐
                      ▼             ▼             ▼
                 RAW AUDIO       CQT/LFCC      SSL AUDIO
                      ▼             ▼             ▼
                 RawNet-style   AASIST-style   WavLM/HuBERT
                      └─────────────┼─────────────┘
                                    ▼
                          ┌────────────────────┐
                          │ SPOOF FUSION        │
                          └─────────┬──────────┘
                    ┌───────────────┼────────────────┐
                    ▼               ▼                ▼
              Speaker ASV     Prosody/Behavior   Replay/Liveness
                    └───────────────┼────────────────┘
                                    ▼
                         ┌──────────────────────┐
                         │ CONTEXT INTELLIGENCE  │
                         │ caller / transaction  │
                         │ history / policy      │
                         └──────────┬───────────┘
                                    ▼
                         ┌──────────────────────┐
                         │ BAYESIAN RISK ENGINE  │
                         │ posterior + confidence│
                         └──────────┬───────────┘
                                    ▼
                         ┌──────────────────────┐
                         │ POLICY ENGINE         │
                         └──────────┬───────────┘
              ┌─────────────────────┼─────────────────────┐
              ▼                     ▼                     ▼
           ALLOW                 VERIFY                 HOLD
                                    └──────────┬──────────┘
                                               ▼
                                      MFA / CALLBACK / ESCALATION
                                               ▼
                                     SOC / AUDIT / XAI
```

### 6.2 Ingestion layer

- **SIP/RTP:** PSTN → SIP trunk → RTP stream → SPAN/mirror/media tap → stream gateway
- **WebRTC:** WebRTC → SRTP → media gateway → PCM frames
- **Enterprise SDK:** Browser/mobile → AudioWorklet / native audio API → 20–30ms packets → gRPC/WebSocket

Asterisk and FreeSWITCH are appropriate for building a **controlled SIP/RTP prototype testbed**, rather than relying solely on raw microphone recordings — this materially strengthens the "we tested under real telephony conditions" claim.

### 6.3 Streaming & chunking — two temporal scales

**Fast path:** 20ms packet/frame → 100–250ms inference hop → first provisional decision at ~300–500ms
**Slow path:** 1–3s rolling context → longitudinal state across the entire call

Formally: `p_t = P(S_t = spoof | x_{t-k:t})` (evidence-conditioned) rather than `p_t = P(S_t = spoof | x_t)` (single-frame — too noisy for a security decision).

### 6.4 Voice Activity Detection

VAD runs *before* the expensive deep-learning inference to save compute: `RTP PCM → energy/VAD → speech frame? → [no: update silence state] / [yes: model pipeline]`. Keep a small pre-roll buffer so the onset of phonemes isn't clipped.

### 6.5 DSP feature pipeline — four forensic views

| View | Method | Why it matters |
|---|---|---|
| **A. Magnitude spectrum** | STFT → linear / log / Mel spectrogram / CQT | A published study found CQT/log-spectral representations can *outperform* Mel representations for deepfake detection (up to ~37% average EER improvement in one setup) — don't default to Mel just because it's standard for ASR |
| **B. CQCC** | Constant-Q transform + cepstral transform | Logarithmic frequency resolution exposes artifacts that MFCC's linear-Mel smoothing can hide |
| **C. LFCC** | Linearly-spaced filterbank + cepstral coefficients | Preserves information Mel compression can suppress — kept as a separate forensic view |
| **D. Phase-derived features** | Unwrapped phase, group delay `τ_g(ω) = -dφ(ω)/dω` | Complementary, not standalone — channel processing can *also* introduce phase distortion, so this branch should never be the sole detector |

**Spectral flatness** (ratio of geometric to arithmetic mean of the power spectrum) is useful for flagging unnatural spectral distributions and vocoder/replay artifacts, but should be treated as a **weak** feature, not a decision variable.

**High-frequency artifacts:** research shows HF features can contribute meaningfully to detection, but attackers can also manipulate them. Avoid overclaiming — never state "AI voices are physically impossible above frequency X." The defensible framing is: *"the detector evaluates learned spectral inconsistencies and generator/channel-dependent frequency patterns."*

### 6.6 Deep-learning architecture — dual-stream + SSL + speaker + behavior

**Expert 1 — Spectro-temporal (AASIST-style):** CQT/LFCC/log-spectrum → CNN encoder → spectral-temporal graph nodes → graph attention → spoof embedding. AASIST's lightweight variant (AASIST-L) runs at ~85k parameters, making it attractive for edge inference.

**Expert 2 — Raw waveform (RawNet-style):** operates directly on `x[n]` with no handcrafted features, giving a representation space independent of the spectral branch.

**Branch 3 — SSL (WavLM/HuBERT/Wav2Vec2):** freeze most of the backbone initially (full fine-tuning is expensive and hurts latency) → selected hidden layer → small projection head → spoof probability.

**Branch 4 — Speaker verification:** current speech → speaker embedding `e_c` → compare against enrollment embedding `e_r` via cosine similarity `s_spk = (e_c·e_r)/(‖e_c‖‖e_r‖)`, ideally with probabilistic calibration rather than a hard threshold. Research on **speaker-aware anti-spoofing** shows conditioning the countermeasure on the enrolled target speaker improves EER/t-DCF over speaker-independent baselines — i.e., "is this synthetic?" and "is it trying to sound like *this specific* enrolled speaker?" are separate, complementary questions.

**Branch 5 — Prosody / behavior:** F0 trajectory, energy contours, speech rate, pause duration, jitter/shimmer, response latency, interruption patterns, unusually regular pauses, over-clean turn transitions. Avoid terms like "micro-tremor" as if they're reliable proof of humanness — some biological voice characteristics can be modeled or copied. Prefer the framing **"naturalness consistency features"** and **"temporal behavioural deviations."**

**Multi-task shared-encoder model:**
```
                   shared encoder
        ┌────────────────┼─────────────────┐
        ▼                ▼                 ▼
   spoof head       speaker head       quality head
        ▼                ▼                 ▼
   P(spoof)          P(match)          SNR/channel

Loss = λ_s·L_spoof + λ_v·L_speaker + λ_q·L_quality
```
The quality head matters because **confidence should fall when the audio itself is unreliable.** e.g. `P(spoof)=0.30, confidence=low, SNR=poor, packet_loss=18%` should never output `SAFE` — it should output `INCONCLUSIVE — secondary verification required`.

**Ensemble weighting — quality-conditioned, not static:**
`z_t = w1(q_t)·p_spec + w2(q_t)·p_raw + w3(q_t)·p_ssl`, where weights depend on channel quality:

| Condition | Spectral | Raw | SSL |
|---|---:|---:|---:|
| 16kHz clean | 0.35 | 0.30 | 0.35 |
| 8kHz G.711 | 0.25 | 0.45 | 0.30 |
| Heavy noise | 0.20 | 0.50 | 0.30 |
| Severe compression | 0.15 | 0.55 | 0.30 |

(Initial engineering priors — train/calibrate against validation data.)

### 6.7 Dynamic risk scoring — session accumulation

Let `H_t = P(S=1 | X_{1:t}, C)`. Bayesian update in log-odds form:
`log O_t = log O_{t-1} + log LR_t`, then `P_t = O_t / (1 + O_t)`.

This is conceptually superior to independently re-predicting from scratch every 250ms, and is exactly what turns the demo into "a score that visibly rises as the fraud call proceeds" rather than a flat number.

**Why not make a Kalman filter the primary model:** `P(spoof)` is bounded on [0,1], non-Gaussian, and can jump sharply when new contextual evidence arrives — a Kalman filter's linear-Gaussian assumption doesn't fit. Use **Bayesian/log-odds sequential fusion** as the core decision mechanism; a Kalman/EKF-style smoother can exist as an *experimental* branch for slowly-varying latent state, not the primary security signal.

### 6.8 Contextual risk fusion & transaction sensitivity

`R_t = f(P_spoof, P_speaker-mismatch, R_caller, R_transaction, R_behavior, Q_audio)`, e.g.
`logit(R_t) = b + w_s·logit(P_s) + w_v·logit(P_v) + w_c·C_t + w_b·B_t + w_q·Q_t`

**Transaction sensitivity tiers** — a 70% voice-risk score during a trivial balance inquiry and a 70% score during a ₹5 crore transfer must **not** trigger the same action:

```
Tier 0 — informational
Tier 1 — account information
Tier 2 — credential/security operation
Tier 3 — financial transaction
Tier 4 — privileged authorization
```

Simple fusion baseline: `R_effective = 1 - (1 - R_voice)(1 - R_context)`, refined later by a trained/calibrated fusion model.

### 6.9 Action policy & risk state machine

```
if R < 0.30:  ALLOW
elif R < 0.60: WARN
elif R < 0.80: REQUIRE_SECOND_FACTOR
else:          HOLD_AND_ESCALATE
```
Thresholds should ultimately be chosen against false-positive cost, false-negative cost, and transaction value — not picked arbitrarily.

```
UNKNOWN → MONITORING → [low evidence]────► TRUSTED
                       [ambiguous]───────► VERIFY
                       [strong evidence]─► HIGH_RISK → BLOCK/HOLD → REVIEWED
```
An explicit state machine is easier for a judge (or an auditor) to reason about than a single floating-point number.

### 6.10 Explainability layer

Every high-risk decision carries a structured evidence vector, e.g.:
```json
{
  "risk": 0.94,
  "decision": "HOLD",
  "evidence": [
    "synthetic_speech_probability",
    "speaker_embedding_mismatch",
    "high_transaction_sensitivity",
    "new_beneficiary",
    "verification_bypass_language"
  ],
  "confidence": 0.91,
  "audio_quality": 0.82
}
```
Displayed as a bar breakdown ("why was this call flagged?") plus saliency/attention overlays over time/frequency for the acoustic model — explicitly labeled as **model attribution**, never as proof that "this frequency is fake."

### 6.11 Uncertainty-aware output

Output a band, not a bare percentage and not a forced binary:
```
Risk:          73
Confidence:    41
Audio quality: POOR
Evidence:      INCONCLUSIVE
Action:        STEP-UP VERIFICATION
```
This prevents a specific security failure mode: **high model uncertainty being silently mistaken for low attack probability.**

---

## 7. Key Differentiators / Moats

These map directly onto the Tier 2 feature list, expanded with the underlying engineering rationale:

1. **Indian telephony robustness** — synthetic channel generator (G.711 A-law/µ-law, AMR 8k, packet loss, jitter, noise, reverb, mic distortion, re-recording) applied during training so the model learns `P(spoof | x′)` instead of `P(spoof | x)`.
2. **Language and accent invariance** — IndicVoices used as a *bonafide speaker-diversity* resource (not a fake/real label set); AI4Bharat's IndicTTS/Indic-Parler resources used to generate controlled Indic spoof counterparts, producing a full language × channel × attack evaluation matrix.
3. **Dual-stream hybrid model** — raw waveform + spectrogram branches have genuinely different inductive biases; their fusion is more defensible than an arbitrary three-model ensemble.
4. **Codec-conditioned inference** — pass codec/SNR/packet-loss/jitter metadata directly into the fusion MLP (`h = MLP([h_audio; h_codec; q])`) rather than pretending all audio has equal quality.
5. **Uncertainty-aware decisions** — see §6.11.
6. **Unseen-generator evaluation** — train on generators {A,B}, test on held-out {C,D} plus adversarially modified attacks; mirrors ASVspoof's own evaluation philosophy and ASVspoof5's addition of adversarial attacks.
7. **Forensic XAI** — per-incident record of call ID, model version, codec, audio quality, spoof probability, speaker similarity, temporal evidence, risk evolution, final action; risk-trajectory visualization shows *how confidence accumulated*, not just the final number.
8. **Active liveness as a fallback, not the default** — passive detector runs first; only an *uncertain* verdict triggers a semantic (not fixed-phrase) challenge, since attackers can pre-synthesize a known fixed phrase.
9. **Privacy-first inference** — edge feature extraction, short-lived raw-audio buffers (auto-delete in seconds), only feature vectors/risk events persisted centrally — attractive specifically for bank/government deployment contexts.

---

## 8. Dataset Strategy

| Tier | Source | Purpose |
|---|---|---|
| 1 | ASVspoof 2019/2021 (LA, PA, DF partitions; official EER/min-t-DCF scripts) | Core anti-spoof benchmark |
| 2 | ASVspoof 5 (~2,000 speakers, diverse conditions, 32 attack algorithms, adversarial attacks) | Modern open-domain deepfake coverage |
| 3 | In-the-Wild (~37.9h real / ~17.2h deepfake, celebrity/public-figure speech) | **Held-out external generalization test only** — never a training source |
| 4 | IndicVoices (22 languages, 22,563 speakers, 208 districts, ~12,000h) + IndicTTS/Indic-Parler | Indian genuine-speech diversity + controlled synthetic Indic generation |
| 5 | Self-generated corpus: volunteers reading transaction requests, auth phrases, spontaneous dialogue, numbers, names, mixed Hindi-English, noisy environments — each paired with a synthetic counterpart of the *same speaker, same utterance* | Controlled forensic same-speaker/same-utterance pairs; **obtain explicit consent and define retention policy up front** |

**Split strategy (never rely on a single random 80/20 split):**

- **Split A — speaker-disjoint:** `Speaker_train ∩ Speaker_test = ∅`
- **Split B — generator-disjoint:** `Generator_train ∩ Generator_test = ∅`
- **Split C — channel-disjoint:** train mostly clean, test on G.711 / AMR / packet-loss / noise / replay
- **Split D — language-disjoint:** train on a subset of languages, evaluate cross-lingual transfer
- **Split E — compound attacks:** synthetic + codec + noise + replay stacked together

---

## 9. Latency & Evaluation Framework

### 9.1 Latency budget (engineering targets, not guarantees)

| Component | Target |
|---|---:|
| RTP/frame arrival | 20–40 ms |
| Jitter buffering | 20–40 ms |
| VAD/preprocess | 5–15 ms |
| Feature computation | 10–30 ms |
| Model inference | 20–80 ms |
| Fusion/risk | <10 ms |
| Network/API overhead | 20–50 ms |
| **First provisional decision** | **~150–300 ms** |
| High-confidence rolling decision | ~500 ms – 2 s |

**Critical distinction to state explicitly on the feasibility slide:** *inferential latency* (how fast the model runs) vs. *evidence latency* (how much speech is statistically needed for a reliable decision). Sub-100ms inference is achievable while still needing 1–2 seconds of accumulated speech for a trustworthy call-level verdict — this is exactly the gap ValidSoft and Pindrop navigate publicly (both market "real-time" while recommending ~2s of audio). The defensible claim is **"sub-500ms provisional risk update,"** not "100% reliable decision in 300ms."

### 9.2 Core metrics

- **RTF (Real-Time Factor):** `RTF = T_compute / T_audio`; target `RTF < 0.1`. Report **p50/p95/p99**, never just the average.
- **EER:** the operating point where FAR = FRR. Lower is better — but should not be the only reported metric.
- **min t-DCF:** relevant wherever speaker verification is integrated, since it reflects the cost of spoofing attacks interacting with ASV; ASVspoof provides official baseline scripts for both.

### 9.3 Target benchmark table (the strongest single slide in the deck, once populated)

| System | Clean EER | 8kHz EER | AMR EER | Noise EER | Unseen-generator EER | p95 latency |
|---|---:|---:|---:|---:|---:|---:|
| CNN baseline | | | | | | |
| AASIST | | | | | | |
| RawNet | | | | | | |
| SSL baseline | | | | | | |
| Dual-stream | | | | | | |
| Dual-stream + codec training | | | | | | |
| **Full system** | | | | | | |

### 9.4 The central research hypothesis

`H1: multi-view codec-aware fusion > single-view detector`, evaluated jointly under **unseen generators + 8kHz telephony + noise + adversarial processing**.

Ablation path: `AASIST → + RawWave → + SSL → + codec augmentation → + speaker conditioning → + temporal Bayesian fusion → + contextual risk`, tracking EER / min-t-DCF / FPR / unseen-generator robustness / latency at each increment. This is materially stronger than "we used AASIST."

---

## 10. Implementation Roadmap

### 10.1 Phases

- **Phase 0 — Threat-model & benchmark design:** build the master evaluation matrix (language × channel × noise × attack × generator seen/unseen × duration × latency × metric) *before* training anything.
- **Phase 1 — Baselines:** (A) log-Mel + small CNN, (B) AASIST, (C) RawNet-style encoder — established first so later gains are attributable.
- **Phase 2 — Codec robustness:** channel-augmentation layer (`random_codec → random_resample → random_noise → random_reverb → random_packet_loss → random_gain`) so training distribution resembles deployment.
- **Phase 3 — Dual-stream model:** spectral + raw encoders → concatenation → fusion MLP → spoof logit. (Treat any specific code as a structural pattern, not a fixed implementation.)
- **Phase 4 — Speaker verification:** speaker encoder → embedding → compare to enrollment → calibrated likelihood. Store **embeddings**, not raw enrollment recordings, wherever policy allows.
- **Phase 5 — Streaming inference:** persistent per-call state; each frame: preprocess → VAD gate → feature extraction → model scores → audio-quality estimate → Bayesian posterior update → fetch context → fuse risk → policy decision → publish.

### 10.2 Suggested microservice layout

```
voice-security/
├── gateway/        (sip/, rtp/, webrtc/)
├── audio/          (vad/, preprocessing/, codec/)
├── ml/             (aasist/, rawnet/, ssl/, speaker/, fusion/)
├── risk/           (bayesian/, policy/, calibration/)
├── context/        (caller/, transaction/, behaviour/)
├── explainability/
├── alerting/
├── dashboard/
└── audit/
```

Prototype data path: `RTP/WebRTC → FastAPI gateway → Redis Streams → Python inference worker → gRPC risk engine → WebSocket dashboard`. Redis Streams is the right call for an SIH-scale prototype — Kafka is overkill unless genuine high-throughput distributed processing is required.

### 10.3 Recommended stack

| Layer | Tool |
|---|---|
| Model training | PyTorch |
| Audio I/O | torchaudio / librosa |
| DSP | NumPy / SciPy |
| ASR (if needed) | Whisper-family or Indic ASR |
| Speaker embeddings | ECAPA / RawNet family |
| Anti-spoof | AASIST + raw-waveform branch |
| Inference serving | ONNX Runtime |
| API | FastAPI |
| Internal RPC | gRPC |
| Streaming transport | WebRTC / RTP |
| PBX testbed | Asterisk / FreeSWITCH |
| Queue | Redis Streams |
| Database | PostgreSQL |
| Dashboard | React / Next.js |
| Visual analytics | Plotly |
| Deployment | Docker |
| GPU serving | CUDA / TensorRT where useful |
| Edge | ONNX Runtime / WebAssembly where feasible |

### 10.4 36-hour grand-finale timeline (hour-by-hour)

| Block | Hours | Focus |
|---|---|---|
| 1 | 0–6 | Environment & data setup |
| 2 | 6–16 | Core classifier fine-tuning + baseline training |
| 3 | 16–22 | Risk fusion + session accumulation integration |
| 4 | 22–28 | Explainability + API wiring |
| 5 | 28–33 | UI polish and rehearsal |
| 6 | 33–36 | Buffer |

Assign a named owner per block from the actual team workstream table (ML core / real-time systems / data engineering / product+demo).

### 10.5 Immediate priority, right now

**Confirm the Tier 1 system actually runs end-to-end today, even at rough accuracy.** A beautiful deck describing a system that doesn't run live is the single most common way a strong-sounding SIH team gets cut at the internal round. If Tier 1 isn't live, that is this week's only priority — not slide polish.

---

## 11. Product Surfaces

### 11.1 Positioning

Ship this as an **adaptive voice-security layer** ("VoiceShield"-style product framing) — not as "a deepfake detection app."

### 11.2 Call-agent interface (mockup)

```
┌────────────────────────────────────┐
│ CALL SECURITY                       │
├────────────────────────────────────┤
│ Caller: CFO                         │
│ Speaker Match:        68%           │
│ Voice Integrity:      HIGH RISK     │
│ Transaction Risk:     CRITICAL      │
│                                      │
│ Overall Risk          93 / 100      │
│                                      │
│ [ HOLD TRANSACTION ]                │
│ [ START VERIFICATION ]              │
└────────────────────────────────────┘
```

### 11.3 SOC dashboard

Suspicious calls, attack categories, risk timeline, speaker identity, caller metadata, codec, model confidence, false-positive review, known-fraudster clustering.

### 11.4 API surface

```http
POST /v1/voice/session
POST /v1/voice/chunk
GET  /v1/risk/{session_id}
POST /v1/action/verify
POST /v1/action/block
GET  /v1/audit/{session_id}
```

Example response:
```json
{
  "session_id": "call_7f91",
  "risk_score": 0.93,
  "risk_level": "CRITICAL",
  "spoof_probability": 0.87,
  "speaker_match_probability": 0.41,
  "audio_quality": 0.82,
  "confidence": 0.91,
  "recommended_action": "HOLD_AND_VERIFY"
}
```

---

## 12. End-to-End Demo Scenario (the scripted live demo)

**Step 1 — Genuine call:** CEO calls employee → speaker verified → voice integrity normal → low transaction risk → **ALLOW**.

**Step 2 — Clone attack:** Attacker clones the CEO's voice → sent over a G.711 channel with added noise → employee receives the call. Attacker says: *"Transfer ₹25 lakh immediately. Do not call me back; I am in a meeting."*

System display:
```
VOICE INTEGRITY       81% suspicious
SPEAKER MATCH         54%
SOCIAL ENGINEERING    HIGH
TRANSACTION RISK      CRITICAL
CALLER REPUTATION     UNKNOWN

FINAL RISK             96%
```

Resulting action: **TRANSACTION HOLD + INDEPENDENT CALLBACK + MFA.**

This scenario is deliberately designed so the "do not call me back" line in the script itself becomes a labeled social-engineering evidence signal on the explainability panel — a small but memorable detail for a live demo.

---

## 13. Internal-Round Pitch Deck (10-Slide Locked Structure)

**⚠ Verify before finalizing:** SIH's registration portal states the PPT template is mandatory. Someone on the team must download the actual official `.pptx` from the SPOC/institute portal and confirm slide count and section titles — treat everything below as *content to pour into whatever the official shell turns out to be*, not a replacement for it. Also confirm the actual internal-round time cap with the college before rehearsing to a number.

**Scoring weights (per current third-party guidance — cross-check against the official rubric):** Innovation 25% · Problem Understanding 20% · Technical Feasibility 20% · Impact/Scalability 20% · Presentation Quality 15%. Slides 2 and 5 alone are 45% of the score — they should get the most polish time, not the least.

| # | Slide | Content |
|---|---|---|
| 1 | Title | Team name, "SIH26104 — AI-Powered Real-Time Detection and Prevention of Voice Cloning Impersonation Attacks," institute, all team members with department, mentor name |
| 2 | Problem Understanding (20%) | Causal chain: cheap high-fidelity cloning now exists → voice is still treated as an implicit trust signal in high-stakes calls → attackers exploit exactly that gap → no automated real-time layer currently challenges that assumption. Cite the CERT-In advisory on deepfake-driven financial fraud / executive-voice impersonation (**verify the exact document before listing it**). Name current-solution gaps: caller ID is spoofable, callback verification still trusts the same voice channel, human voice-recognition is exactly the heuristic a good clone defeats |
| 3 | Proposed Solution | Headline: *"Don't just detect the fake voice. Detect the fraud."* Sub-line: a real-time, contextually-fused, explainable risk layer, measured for Indian languages, that plugs into existing fraud-decisioning infrastructure. One simple flow diagram: Audio → Authenticity Score → Session Accumulation → Contextual Risk Fusion → Adaptive Action |
| 4 | Technical Architecture | System diagram (from §5/§6): streaming audio → WavLM score → EMA session accumulator → XGBoost fusion with call metadata → thresholded action → API out. Diagram-first, minimal prose |
| 5 | **Innovation & Novelty (25% — highest weight)** | Headline number: Indian-language EER before/after fine-tuning (make it visually dominant); unseen-generator generalization result; uncertainty-aware banding; live session-accumulation demo concept. State the honest novelty claim explicitly: not claiming to have invented voice-authenticity detection — extending it into an underserved linguistic distribution and wrapping it in an explainable, deployable decisioning layer existing detectors don't publicly provide |
| 6 | Feasibility & Viability (20%) | WavLM is fine-tuned, not trained from scratch — achievable in the build window. Free/open resources: ASVspoof/WaveFake, open-source Indian-language TTS tools, open pretrained checkpoints. Scalability: stateless API/SDK design scales horizontally; state the *actual measured* latency number from a spike test, not an estimate |
| 7 | Impact & Benefits (20%) | Quantify: EER improvement %, measured latency, the CERT-In-verified real-world fraud pattern addressed. Name specific beneficiaries (bank customers, enterprise finance teams, telecom subscribers) — matches the PS's own stated deployment targets, which is a subtle point in the team's favor |
| 8 | Prototype/Demo | Screenshots or mockup of the live session-risk dashboard (score climbing during a scripted call) and the explainability panel. Real screenshots beat polished wireframes with a technical judge |
| 9 | Timeline (36-hour grand-finale plan) | Hour-by-hour breakdown from §10.4, with named owners per block |
| 10 | Team & References | One line per member tied to actual workstream ownership (ML core / real-time systems / data engineering / product+demo); mentor name; references: ASVspoof/WavLM/AASIST/RawNet2 papers + the CERT-In advisory (verified) |

### 13.1 Formatting rules that separate shortlisted decks from rejected ones

1. **Diagrams before text, always.** Evaluators scan visually first in a 2–3 minute pass. Slides 3 and 4 should be diagram-dominant.
2. **One hard, checkable number beats an adjective every time.** "Highly accurate" convinces nobody; "EER dropped from X% to Y% after Indian-language fine-tuning" is specific, memorable, and defensible on the spot.
3. **Six bullet points per slide, maximum.** If Tier 2's differentiators don't fit cleanly on Slide 5, compress into icons/short labels and hold detail in spoken narration — don't shrink the font.
4. **State the exact PS number and title verbatim early**, and make every subsequent slide visibly trace back to it. A common rejection pattern is a deck that reads like a generic AI-security pitch instead of a direct answer to SIH26104's stated requirements (real-time detection, API/SDK for banking-telecom-enterprise, explainability).
5. **Never let a slide claim something not actually built.** A judge who catches one overclaim will re-read every other slide with suspicion — this is why §4's Tier 3 discipline exists.
6. **File size and visual consistency are real filters, not cosmetic ones.** Stay under the stated size limit, one color scheme throughout, 14pt+ body text.

### 13.2 Note on the earlier 12-slide draft

An earlier pass through this material produced a 12-slide version (adding a dedicated "why existing approaches fail" slide and splitting evaluation rigor / explainability into separate slides, total under 6 minutes of talking). The 10-slide structure above is the **final locked version** and supersedes it, but the extra framing point from the earlier draft is worth keeping in the narration even if it doesn't get its own slide: *"generic detectors trained on English-only data silently fail on Indian speech — that's the specific gap this project closes."* That sentence belongs inside Slide 2 or the opening of Slide 5.

---

## 14. Strategic Verdict

Three tiers of possible implementation, in ascending order of SIH competitiveness:

| Tier | Shape | Competitiveness |
|---|---|---|
| **Weak** | `upload audio → CNN → Fake/Real` | Low — a wrapper around an already heavily-researched task |
| **Good** | `live stream → AASIST/RawNet → risk score → dashboard` | Good — demonstrable and technically serious, but commercially similar to existing platforms |
| **Target** | Indian multilingual speech + telephony codec simulation + dual-view anti-spoofing + speaker-aware verification + streaming temporal Bayesian fusion + contextual transaction risk + uncertainty calibration + active verification fallback + explainable evidence + privacy/edge deployment | **Potentially excellent** |

**Critical honesty check, repeated deliberately:** none of the individual components above is unprecedented. AASIST, speaker-aware anti-spoofing, commercial voice biometrics, streaming deepfake detection, and transaction-level voice security all already exist in some commercial or academic form. The actual novelty claim is an **engineering combination and evaluation protocol specifically optimized for Indian telephony environments, backed by publicly reproducible evidence of robustness under codec degradation and unseen generators.** This is the sentence to say out loud if a judge asks "what's actually new here?"

---

## 15. Open Items / Next Actions

- [ ] Confirm Tier 1 (ingestion → WavLM classifier → risk layer → thresholds → API) runs end-to-end today, even at rough accuracy — this is the current single priority, ahead of any slide work
- [ ] Download the **official** SIH PPT template from the SPOC/institute portal; map this document's content onto its actual slide count/section titles
- [ ] Confirm the internal round's actual time cap with the college before rehearsing to a possibly-wrong number
- [ ] Verify the exact CERT-In advisory document before citing it on Slide 2/10
- [ ] Run the latency spike test and use the *actual measured* number on Slide 6, not an estimate
- [ ] Populate the benchmark table in §9.3 with real numbers as soon as baselines are trained
- [ ] Record/consent-clear the self-generated Hindi/Marathi/Indian-English speaker corpus (§8, Tier 5) before use

---

## 16. Reference Anchors

Core technical grounding used throughout this document: the ASVspoof 5 challenge/data papers and official materials; AASIST; RawNet3; speaker-aware anti-spoofing research; the *In-the-Wild* generalization study; AI4Bharat's IndicVoices and IndicTTS/Indic-Parler resources; HiFi-GAN, StyleTTS2, and VALL-E as representative generator architectures; RFC 3551 (RTP audio profile) and RFC 4867 (AMR) for telephony codec detail; and current commercial documentation from Pindrop, Nuance/Microsoft Gatekeeper, ID R&D, ValidSoft, Hiya/Loccus, and ElevenLabs for the competitive landscape in §3.

# Model Inventory (L3 — ML / Evidence Generation)

Single source of truth for **which models actually run**, which do not, and what
is and is not claimed about them.

Generated against the verified environment on **2026-08-28**:
Python 3.10.0 · torch 2.1.2+cpu · transformers 4.36.2 · librosa 0.11.0 ·
numpy 1.26.4 · CPU only (no CUDA).

---

## 1. Status of the six experts

| Slot | Role (spec) | Model actually used | Status |
|---|---|---|---|
| **E1** | Spectro-temporal, AASIST-style | *none* | `MODEL_UNAVAILABLE` / `WEIGHTS_NOT_ACQUIRED` |
| **E2** | Raw waveform anti-spoofing | `mo-thecreator/Deepfake-audio-detection` | **OK — real inference** |
| **E3** | Multilingual SSL + probe | backbone loadable, **probe absent** | `MODEL_UNAVAILABLE` / `PROBE_NOT_TRAINED` |
| **E4** | Speaker verification | `microsoft/wavlm-base-plus-sv` | **OK — real inference** |
| **E5** | Prosody / behavioural | *none* | `DEFERRED` (B1) |
| **E6** | Replay / liveness | *none* | `DEFERRED` (B2) |

**Two of six experts perform real model inference.** The startup log states this
on every boot (`2/6 experts live; unavailable or deferred: E1, E3, E5, E6`).

### Pinned artefacts

| Key | Repo | Revision | License |
|---|---|---|---|
| `wavlm_base_plus_sv` | `microsoft/wavlm-base-plus-sv` | `feb593a6c23c1cc3d9510425c29b0a14d2b07b1e` | **UNKNOWN** — repo card declares none; review before non-demo use |
| `wav2vec2_deepfake` | `mo-thecreator/Deepfake-audio-detection` | `e4d9874b493362149cec96ced85f00b00b1a04c0` | apache-2.0 |

Total vendored size ≈ 783 MB. Revisions are pinned, never `main`.

---

## 2. Substitution register

Both live experts are **substitutions**. This is recorded machine-readably in
`ModelDescriptor.is_substitution` and asserted by a test, so it cannot be lost.

### E2 — wav2vec2 deepfake classifier, *not* RawNet2, *not* AASIST

The specification (§6.2, C-21) names a RawNet2-class raw-waveform anti-spoof
model. No RawNet2 checkpoint is available in a loadable form here.

What runs instead is `Wav2Vec2ForSequenceClassification` fine-tuned for deepfake
audio detection, with `id2label = {0: fake, 1: real}`.

It occupies **E2 rather than E1** because it consumes **raw waveform**, which is
exactly what C-21 declares as E2's input — and C-21 additionally says E2 "does
NOT consume spectral features". C-20 fixes E1's input as
`FeatureBundle.spectral` and names a specific architecture. Putting a wav2vec2
classifier at E1 would require claiming it is AASIST-style, which is false: it
has no graph attention, no spectro-temporal branch fusion, and does not consume
a spectrogram.

The fake-class index is resolved from the checkpoint's own `id2label` at load
time, never hardcoded — other checkpoints disagree (`Hemgg` uses
`{0: AIVoice, 1: HumanVoice}`), and an index-0 assumption would silently invert
the score. If neither label is recognisable, E2 refuses to load and reports
`LABEL_MAP_UNRECOGNIZED` rather than guessing.

### E4 — WavLM x-vector, *not* ECAPA-TDNN

The specification (§6.2, C-23) names an ECAPA-TDNN encoder via SpeechBrain.
SpeechBrain is **not installable in this environment**: it requires `torchaudio`,
which is absent, and its torch-2.1.2 compatibility was already flagged
"REQUIRES VERIFICATION" in `EXECUTION_TECH_STACK.md`.

`WavLMForXVector` is a genuine speaker-verification model — the task matches the
slot exactly — but **the embedding dimension differs: 512-d here versus 192-d for
ECAPA.** Each enrolment records its dimension and originating model, so a stale
192-d reference is never silently compared against a 512-d embedding; that case
returns `ABSTAIN` / `ENROLLMENT_DIM_MISMATCH`.

### E1 and E3 — deliberately left unavailable

Filling every slot with whatever happens to load is the exact failure mode the
specification's failure-behaviour clauses exist to prevent.

- **E1**: no AASIST weights *and* no AASIST architecture code exist here.
- **E3**: the WavLM backbone loads, but C-22 requires
  `selected hidden layers → lightweight probe → spoof classifier`, and **the
  probe does not exist**. Verified: `wavlm-base-plus-sv`'s `id2label` holds 1211
  generic `LABEL_n` **speaker** classes, not spoof/genuine classes. Mapping
  hidden states to a spoof probability would mean inventing a classifier head.

  E3 also deliberately does **not** reuse E2's output. That would make E3 a copy
  of E2, and L4 would fuse two perfectly correlated numbers as if they were
  independent evidence — worse than abstaining, because it would inflate apparent
  agreement between experts.

  The layer-selection machinery (`DEFAULT_PROBE_LAYERS = [4, 8, 12]`) is
  implemented and tested so a future probe is a drop-in.

---

## 3. What is NOT claimed

> **No accuracy, EER, or detection-rate claim is made for any expert.**
>
> **No evaluation set exists in this workspace** (readiness R1). No such number
> could be produced here honestly.
>
> **Latency figures are measurements on one CPU machine, not guarantees.**
>
> **The demo fixtures (`demo/audio/*.wav`) are synthetic tones, not speech, and
> carry no authenticity ground truth. Any probability produced on them is
> meaningless and must not be cited as evidence that detection works.**

That last point is concrete: on `clean_speechlike.wav` the detector outputs
`p(fake) = 0.9968`, and on pure `silence.wav` it outputs `p(real) = 1.0000`.
Both are artefacts of feeding a speech model non-speech. The fixtures prove the
code path executes; they prove nothing about detection quality.

No test in the suite asserts an accuracy figure. The one behavioural assertion
(E4) is explicitly relative — see §5.

---

## 4. Measured constraints

All measured by binary search against the real checkpoints, not estimated.

| Constraint | Value | Consequence |
|---|---|---|
| `WavLMForXVector` minimum input | **4880 samples (0.305 s)** | Below this it raises `RuntimeError`; E4 must abstain *before* calling it |
| Deepfake detector minimum input | **400 samples (0.025 s)** | E2 runs per-frame with margin |
| Frame size (`audio_hop_ms=250`) | **4000 samples (0.25 s)** | **Below E4's floor** — hence the rolling buffer |
| Cold model load | ≈ 53 s | Warmup at startup is mandatory, not an optimisation |
| Warm load (cached) | ≈ 0.5 s | |
| E2 inference | ≈ 250–610 ms per clip | Recorded, not asserted |
| E4 inference | ≈ 480 ms per 3 s clip | Recorded, not asserted |

### The frame-cadence conflict

A `FrameObject` carries 250 ms of audio — **less than E4's 305 ms floor**. E4
therefore accumulates a rolling 2 s window across frames
(`models/buffering.py`) and re-scores on a 1 s stride rather than per frame.

The stride is not laziness: a 2 s window advanced by 250 ms is 87.5 % the same
audio, so scoring every frame would spend roughly 1.4 CPU-seconds per
wall-second producing eight near-identical numbers. Between emissions E4 returns
`ABSTAIN` with a reason code that distinguishes *warming up*
(`INSUFFICIENT_AUDIO`) from *deliberately holding* (`E4_STRIDE_SKIP`).

Whether L4 carries the last E4 value forward between emissions is L4's decision.
L3's job is to say honestly that it has nothing new.

### Determinism

Inference is **bit-for-bit deterministic** across independent loads (verified
with `torch.equal`). `deterministic_mode` seeds torch and prefers deterministic
kernels; every adapter calls `.eval()` and runs under `torch.inference_mode()`.

---

## 5. The E4 behavioural test, and its honest limitation

C-23 asks for "same-speaker pair scores higher than different-speaker pair".

The available real-speech corpus (LibriSpeech dummy/demo) contains **exactly one
speaker (id 1272)**, so **a true different-speaker pair is not available**. The
test therefore asserts the weaker but still meaningful claim it *can* support:

    min(same-speaker cosine) > max(speech-vs-non-speech cosine)

Measured: same-speaker pairwise cosine **0.9721 – 0.9901**; speech-vs-noise
**0.4734**; speech-vs-tone **0.5760**. Large headroom, so the assertion is
stable — but it is a **relative separation check, not an EER or accuracy claim.**

Synthetic fixtures cannot substitute here. On the repo's harmonic-stack
fixtures, "same source" scored **0.79** and "different source" **0.90** — the
assertion fails, because a harmonic stack carries no speaker identity. Any E4
behavioural assertion must use real speech.

---

## 6. The cosmetic weight-norm warning

Loading `wavlm-base-plus-sv` under torch 2.1 + transformers 4.36 prints that
`pos_conv_embed.conv.weight_g` / `weight_v` "were not used" and that
`parametrizations.weight.original0` / `original1` were "newly initialized".

That reads exactly like *the positional convolution is randomly initialised*,
which would silently corrupt every embedding. **It is not what happens.**

Verified by loading the checkpoint and comparing tensors directly:

```
original0 == checkpoint weight_g  ->  torch.allclose(...) is True
original1 == checkpoint weight_v  ->  torch.allclose(...) is True
```

torch 2.1 renamed weight-norm's storage; transformers remaps it correctly but
reports the old names as unused. Inference was additionally confirmed
bit-identical across independent loads with different seeds.

The message is suppressed deliberately in `models/runtime.py`, where this note is
repeated. **Do not remove that note** — without it, the next person to see the
warning will "fix" a bug that does not exist.

---

## 7. Offline cold start (readiness R12)

```
python scripts/fetch_models.py               # vendor weights + write manifest
python scripts/fetch_models.py --verify-only # pre-demo integrity gate
```

`fetch_models.py` downloads pinned revisions into `assets/models/<key>/` and
writes `assets/models/manifest.json` with a sha256 for every file. At runtime
`models_offline` sets `HF_HUB_OFFLINE=1` / `TRANSFORMERS_OFFLINE=1` **before**
the lazy transformers import, so a missing artefact fails fast instead of
reaching for the network. Checksums are verified before any load; a mismatch
refuses the model rather than running unverified weights.

**Verified**: with `HF_HOME` pointed at a nonexistent directory and both offline
flags set, both models still load from `assets/models/` and run real inference.

Weights are gitignored; **the manifest is committed** — it is the small,
reproducible record of exactly what was vendored.

---

## 8. Architecture notes

**ML-library isolation.** Only `models/adapters/*` and `models/runtime.py` may
import torch or transformers; an AST test enforces this. Everything else —
experts, registry, evidence, contracts — depends on the protocols in
`models/interfaces.py`. Importing `voiceshield.models` does **not** require an ML
stack, so the availability report stays truthful on a machine with no torch.

**The frozen-contract bridge.** The L3 brief requires every result to carry model
id, version, inference timestamp, latency and error state. `ExpertResult` is
frozen (`extra="forbid"`) with only six fields, and §22 forbids amending it. So
the richer `ModelInferenceResult` lives in the adapter layer and is projected
down via `to_expert_result()`; model identity still reaches the contract through
the existing `EvidenceVector.model_versions[]` field via `version_signature()`,
e.g. `E4:microsoft/wavlm-base-plus-sv@feb593a6...`. Nothing frozen changed.

**Uniform score polarity.** `p` means **P(inauthentic)** for *every* expert.
Cosine similarity is natively the opposite (high = matches the enrolled speaker =
*less* suspicious), so E4 emits `p = 1 − normalised_similarity` and preserves the
raw cosine in `logits[0]` and `extra["cosine"]`. Without this, one expert's field
would be inverted relative to the other five and L4 would have no way to tell.

**Abstention over fabrication.** No code path in L3 produces a number it did not
measure. Every non-`OK` status carries `p = None` and `confidence = None`, and
the assembler discards any probability attached to a non-`OK` result. If all six
experts abstain, a complete EvidenceVector is still published with every
probability `None` — L4 reads that as `UNCERTAIN`, which is the correct answer.

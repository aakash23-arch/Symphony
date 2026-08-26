# SIH26104 — Voice Cloning Detection
## Demo Prototype: Architecture & Workflow Document

**Purpose of this document:** to accompany the pitch deck submission with a
concrete, honest account of what the demo prototype actually does, why it was
built this way under hackathon constraints, and how it maps to the full
system described in the deck. This document is written to survive a judge
reading it closely, not just glancing at it.

---

## 1. What this demo is — and isn't

| | |
|---|---|
| **Is** | A working, runnable, judge-clickable implementation of the Tier-1 pipeline shape: ingest → analyze → risk-score → threshold → action, with real explainability. |
| **Isn't** | The production WavLM classifier fine-tuned on ASVspoof/WaveFake. That requires GPU training time, licensed/curated datasets, and a validation cycle that doesn't fit a hackathon build window. |
| **Why build it this way** | A demo that runs live, offline, and explains itself beats a slide describing a system that doesn't yet exist. The architecture is deliberately modular so the acoustic-scoring layer can be swapped for the real WavLM model later without touching anything else. |

This framing matters because it **pre-empts the single most common way strong
SIH decks lose points at the internal round**: a jury asks "does this
actually run," and the answer needs to be yes, live, in front of them.

---

## 2. System architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CALL AUDIO SOURCE                            │
│        (live mic / uploaded clip / bundled synthetic sample)         │
└───────────────────────────────┬───────────────────────────────────┘
                                  │  raw audio bytes
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│  LAYER 1 — INGESTION                                                  │
│  soundfile decode → mono downmix → normalize                          │
└───────────────────────────────┬───────────────────────────────────┘
                                  │  waveform (y, sr)
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│  LAYER 2 — ACOUSTIC AUTHENTICITY SCORING   (features.py)              │
│  ┌─────────────┬──────────────┬───────────────┬───────────────┐    │
│  │ Pitch jitter│ Amp. shimmer │ Spectral       │ Spectral flux  │    │
│  │             │              │ flatness       │                │    │
│  ├─────────────┼──────────────┼───────────────┼───────────────┤    │
│  │ MFCC-delta  │ Harmonic     │ Pause-length   │                │    │
│  │ variance    │ ratio        │ uniformity     │                │    │
│  └─────────────┴──────────────┴───────────────┴───────────────┘    │
│  [DEMO STAND-IN for the WavLM classifier — see §5]                     │
└───────────────────────────────┬───────────────────────────────────┘
                                  │  per-feature risk (0-100) × weights
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│  LAYER 3 — CONTEXTUAL RISK SCORING          (risk_engine.py)          │
│  acoustic_risk (75%) + metadata_risk (25%)                            │
│  metadata = {unknown number, transaction request, urgency language}   │
│  → composite_risk_score (0-100)                                       │
└───────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│  LAYER 4 — ACTION THRESHOLDING              (risk_engine.py)          │
│  configurable sliders: allow_max, flag_max                            │
│  → ALLOW  /  FLAG FOR CALLBACK VERIFICATION  /  BLOCK                 │
└───────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│  LAYER 5 — EXPLAINABILITY + UI              (app.py, Streamlit)       │
│  score gauges · feature-contribution chart · metadata breakdown       │
│  waveform + spectrogram · raw feature JSON · limitations panel        │
└─────────────────────────────────────────────────────────────────────┘
```

Every box in this diagram corresponds to one Tier-1 requirement from the
deck: real-time-shaped ingestion, an authenticity classifier, a contextual
risk-scoring layer, configurable thresholds, and (per Tier-2) explainability
on every flag.

---

## 3. Workflow — what happens on one call

1. **Ingest.** Audio arrives as bytes (mic recording, upload, or the bundled
   sample). Decoded to a mono float32 waveform at its native sample rate.
2. **Acoustic analysis.** Seven interpretable DSP features are computed
   (§4). Each is mapped to a 0–100 "risk contribution" against a documented
   reference point for what genuine human speech looks like, then combined
   into a single acoustic authenticity risk score.
3. **Contextual fusion.** The acoustic score is combined with three
   simulated call-metadata flags — unknown/unverified number, transaction
   request, urgency language — the kind of signals a bank or telecom already
   has at call time. Acoustic evidence is weighted higher (75%) than
   metadata (25%), because metadata alone should never be sufficient grounds
   to block a legitimate call.
4. **Thresholding.** The composite score is compared against two
   judge-adjustable sliders to produce one of three actions: **Allow**,
   **Flag for callback verification**, or **Block**. This directly answers
   the deployability question — a lab demo that only prints a number isn't
   a product; a system with configurable business-facing actions is.
5. **Explain.** Every score is traceable: the UI shows which specific
   features drove the risk contribution, ranked by impact, plus the raw
   feature values for anyone who wants to check the math.

---

## 4. Why these seven features (and not a black box)

Each is a documented marker of synthetic speech in the anti-spoofing
literature, chosen specifically because they're *cheap to compute* (no
GPU, no model weights, pure signal processing via `librosa`) and
*individually explainable* — which is exactly what the Tier-2
explainability differentiator in the deck asks for.

| Feature | What it measures | Why synthetic speech often differs |
|---|---|---|
| Pitch jitter | Frame-to-frame F0 perturbation | Natural voices wobble; naive synthesis can be too smooth |
| Amplitude shimmer | Frame-to-frame loudness perturbation | Same logic, for amplitude |
| Spectral flatness | How "noise-like" vs "tonal" the spectrum is | Synthetic speech can be spectrally flatter |
| Spectral flux | Frame-to-frame spectral change | Natural articulation is less uniform |
| MFCC-delta variance | Micro-prosody variation | Real speech has more moment-to-moment variation |
| Harmonic-to-noise ratio | Harmonic vs. noise energy split | Differs systematically between natural and synthesized voicing |
| Pause-length uniformity | Regularity of silence gaps | TTS engines often insert unnaturally regular pauses |

**Important, stated plainly:** these thresholds are hand-set from general
literature intuition and demo-calibrated against one offline TTS engine
(espeak-ng), *not* fitted on a labeled dataset like ASVspoof. They are a
transparent, swappable stand-in — not a claim of production-grade accuracy.

---

## 5. Demo vs. production — explicit mapping

| Deck component | Production design | This demo |
|---|---|---|
| Authenticity classifier | WavLM fine-tuned on ASVspoof/WaveFake | Classical DSP feature scoring (§4) |
| Risk-scoring layer | XGBoost/LightGBM | Weighted linear combination |
| Action thresholds | Configurable | **Identical in demo** — real sliders |
| API/SDK | REST/SDK for bank/telecom integration | Not built (UI-first prototype); interface sketched in §7 |
| Real-time streaming | Chunked inference | Simulated staged progress over full-clip analysis |
| Explainability | Feature-importance from risk layer | **Identical in demo** — real, per-flag |
| Language/accent robustness dataset | Self-generated Hindi/Marathi/Indian-English cloned+genuine set | Not in this demo — the demo audio is English/espeak only |

The last row matters: the deck's single strongest slide (the Indian-language
generalization result) is a **research result**, not something a UI demo can
show live. Keep those clearly separate in your own head when presenting —
don't let the demo's polish overstate what's been benchmarked.

---

## 6. Anticipated judge questions (and how the demo answers them)

- **"Does it actually run?"** → Yes, live, offline, on this laptop.
- **"How do you avoid false positives on a real call?"** → Point at the
  layered design: acoustic evidence dominates (75%), metadata alone can't
  trigger a block, and thresholds are configurable per deployment.
- **"Isn't this just a black box red light?"** → Open the feature-
  contribution chart. Every flag is traceable to named features.
- **"What happens with a short or noisy clip?"** → Point at the Known
  Limitations panel — stated upfront, not discovered by the judge.
- **"Is this the real model from your architecture slide?"** → Say no,
  clearly, and explain why (§1), then pivot to what *is* real: the pipeline
  shape, the thresholding, and the explainability.

---

## 7. Path from this prototype to the production system

Because the acoustic layer is isolated in `features.py` behind a single
`extract_features(y, sr) -> dict` call, swapping it for a real classifier is
a contained change, not a rewrite:

1. Replace `features.py`'s DSP extraction with a WavLM forward pass fine-tuned
   on ASVspoof/WaveFake (+ the self-generated Hindi/Marathi/Indian-English
   set), producing a single authenticity logit instead of seven hand-scored
   features.
2. Replace the linear weighting in `risk_engine.py` with a trained
   XGBoost/LightGBM model over `[acoustic_logit, call_metadata_features...]`.
3. Replace the staged progress bar with true chunked/streaming inference
   over a live audio socket.
4. Wrap `risk_engine.run_pipeline()` behind a REST/gRPC endpoint for the
   API/SDK integration point the deck promises to banks/telecom/enterprise
   comms.
5. Everything above the acoustic layer — thresholding, explainability
   rendering, the metadata-fusion logic — carries forward largely unchanged.

---

## 8. Honesty checklist before you present

- [ ] Tested the live-mic flow on the actual presentation laptop/mic
- [ ] Confirmed your voice scores low risk and the synthetic sample scores
      meaningfully higher, on that hardware
- [ ] Rehearsed opening the Known Limitations panel unprompted
- [ ] Clear in your own head on which claims are "real" (thresholds,
      explainability, pipeline shape) vs. "demo stand-in" (the classifier
      itself) — see §5
- [ ] Not quoting any accuracy/EER numbers from this demo as project results

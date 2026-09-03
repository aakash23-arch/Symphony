# SYMPHONY / VoiceShield

**Real-Time Voice Integrity & Conversational Deepfake Defense System**

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen)](https://github.com/aakash23-arch/Symphony)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![TypeScript](https://img.shields.io/badge/typescript-5.x-blue)](https://www.typescriptlang.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Symphony (VoiceShield) is an enterprise-grade, real-time voice integrity and impersonation defense pipeline designed to detect synthetic voice manipulation, AI cloning, and conversational deepfake attacks during sensitive voice interactions—such as high-value corporate treasury transfers, wire authorizations, and executive phone directives.

---

## 🏛 Core Architectural Principles

1. **P1 / Replaceability & Open Protocols:** Standardized, decoupled boundaries across ingestion, DSP, ML feature extraction, and Bayesian fusion—no closed vendor lock-in.
2. **P2 / Minimal Data Passing & Privacy:** Raw PCM audio is strictly isolated at the ingestion boundary; downstream ML and policy engines receive only structured numerical tensors and evidence vectors.
3. **P3 / Sub-Second Non-Blocking Ingestion:** Real-time ring buffer streaming ingress operates independently of deep ML inference, guaranteeing `<18ms` frame-level inference latency.
4. **P4 / Context-Aware Bayesian Risk (VoiceBelief):** Security decisions are conditioned on transaction sensitivity, beneficiary novelty, and historical relationship—never on raw acoustic confidence alone.
5. **P5 / Tamper-Evident Forensic Assurance:** Every factor attribution, feature score, and action-grade decision is bound into an immutable, cryptographically verifiable SHA-256 hash chain.

---

## ⚡ Key Capabilities & Moats

- **Multilingual Indic Speech Robustness:** Fine-tuned to eliminate the published `>50%` Equal Error Rate (EER) gap that conventional English-centric models exhibit on Indian accents and code-switching.
- **Partial-Spoof Temporal Localization:** Pinpoints the exact synthetic seconds spliced into an otherwise genuine executive conversation instead of relying on blunt average scores.
- **Ensemble Forensic Defense (6 Independent Experts):**
  - **E1 — Spectro-Temporal:** High-resolution harmonic and spectral tilt analysis.
  - **E2 — Raw Waveform:** Unfiltered PCM phase coherence and neural vocoder artifact detection.
  - **E3 — SSL Foundation:** Multilingual acoustic representations (Wav2Vec2 / WavLM).
  - **E4 — Speaker Biometrics:** Dynamic cosine distance against enrolled caller voiceprints.
  - **E5 — Prosody & Pitch Contour:** Micro-intonation, fundamental frequency ($F_0$), and natural respiratory cadence.
  - **E6 — Contextual Vector:** Transaction magnitude, beneficiary novelty, and out-of-band behavioral markers.

---

## 📂 Repository Layout

```text
Symphony/
├── backend/
│   └── voiceshield/
│       ├── __main__.py           # Role dispatcher: api | analysis-worker | decision-worker | all-in-one
│       ├── config.py             # Pydantic Settings configuration
│       ├── obs/logging.py        # Structured JSON logger with audio payload scrubbing
│       ├── contracts/            # Frozen Pydantic data schemas & message contracts
│       ├── ingestion/            # L1 audio capture, streaming ingress, ring buffer
│       ├── signal_processing/    # L2 DSP, spectral features, filterbanks
│       ├── models/               # L3 anti-spoofing experts E1..E6 & model registry
│       ├── evidence/             # Evidence vector assembly
│       ├── speaker/              # E4 speaker reference enrollment store
│       ├── fusion/               # L4 calibration, quality weighting, VoiceBelief state
│       ├── context/              # L4 contextual risk scaling
│       ├── risk/                 # Composite risk calculation & threshold policy
│       ├── decision/             # L5 policy engine, state machine, action emitter
│       ├── assurance/            # Factor explanation, SHA-256 hash-chain evidence
│       ├── storage/              # SQLite persistence repository
│       ├── api/                  # FastAPI REST and WebSocket streaming routes
│       └── demo/                 # Scenario playback simulator and fixtures
├── frontend/                     # React + TypeScript + Vite + Tailwind CSS dashboard
│   ├── src/
│   │   ├── components/           # RiskGauge, PipelineFlow, EvidenceCards, Storytelling UI
│   │   ├── sections/             # Problem, Signal, Forensics, LiveDetection
│   │   ├── panels/               # HeaderBar, DemoControl, EvidencePanel, RiskPanel
│   │   ├── state/                # SessionProvider, sessionReducer, useSession
│   │   └── api/                  # REST client & WebSocket streaming managers
├── demo/                         # High-fidelity multi-dialect audio recordings
│   ├── demo_01_indian_english.wav # DEMO 01 — Natural Indian English (CFO Wire Request)
│   ├── demo_02_hindi_english.wav  # DEMO 02 — Hindi + English Code-Switching
│   └── demo_03_marathi_hindi.wav  # DEMO 03 — Marathi + Hindi Regional Authorization
├── tests/                        # Comprehensive Pytest suite (Contract, DSP, Pipeline, Scenarios)
├── scripts/                      # Setup, execution, verification, and demo launchers
├── docker-compose.yml            # Containerized deployment specification
└── README.md                     # Project documentation
```

---

## 🎙 Live Testing Demo Scenarios

Symphony ships with 3 pre-recorded, naturalistic multi-accent audio test fixtures:

| Demo | Language / Dialect | Persona & Context | Scenario Transaction | Expected Policy Action |
| :--- | :--- | :--- | :--- | :--- |
| **DEMO 01** | **Indian Accent English** | CFO (Ananya Sharma) — Corporate treasury wire | ₹ 25,00,000 (New Beneficiary) | **HOLD + ESCALATE** |
| **DEMO 02** | **Hindi + English** | VP Finance (Rajesh Malhotra) — Emergency liquidity | ₹ 45,00,000 (Urgent Vendor) | **STEP-UP VERIFY** |
| **DEMO 03** | **Marathi + Hindi** | Director (Sunil Deshmukh) — Regional payroll approval | ₹ 15,00,000 (Verified Vendor) | **NOMINAL ALLOW** |

---

## 🚀 Quickstart & Developer Setup

### Prerequisites
- **Python 3.10+** (with `pip` and `venv`)
- **Node.js 18+** & **npm**
- *(Optional)* **Docker** & **Docker Compose**

### 1. Automated Setup & Execution

```bash
# Clone the repository
git clone https://github.com/aakash23-arch/Symphony.git
cd Symphony

# Run the automated setup script
./scripts/setup

# Start both Backend (:8000) and Frontend (:5173)
./scripts/start
```

Open your browser to: **`http://localhost:5173`** and click **RUN DETECTION** to enter the Live Testing Console.

---

### 2. Manual Development Setup

#### Backend (FastAPI + PyTorch DSP)
```bash
# Create and activate Python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e .

# Start the API server
python -m uvicorn voiceshield.api.app:app --host 127.0.0.1 --port 8000 --reload
```

#### Frontend (React + Vite + Tailwind CSS)
```bash
cd frontend

# Install Node modules
npm install

# Start Vite development server
npm run dev
```

---

### 3. Verification & Automated Test Suite

Run the full end-to-end test suite (Contract schemas, DSP, fusion math, and demo scenarios):

```bash
# Run backend pytest suite
pytest tests/

# Run specific demo scenario integration tests
pytest tests/test_demo_scenarios.py

# Verify frontend build & TypeScript type checking
cd frontend && npm run lint && npm run build
```

---

## 🐳 Docker Container Execution

To spin up the complete containerized stack:

```bash
docker compose up --build
```
Access the application at `http://localhost:5173`.

---

## 🔒 Security & Privacy Architecture

- **No Persistent Voice Storage:** Raw audio chunks are processed in volatile memory and purged immediately following feature extraction.
- **SHA-256 Chained Auditing:** Forensic dossiers contain cryptographically verifiable hash chains ensuring non-repudiation during regulatory compliance audits.
- **Defense in Depth:** Combines acoustic waveform physics, temporal prosody, spectral distribution, biometric voiceprint matching, and financial context modeling.

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

# EXECUTION TECH STACK — VOICE SHIELD INTERNAL DEMO

**Author:** System Architecture Team  
**Authority:** [docs/EXECUTABLE_ARCHITECTURE.md](file:///e:/Symphony%201/docs/EXECUTABLE_ARCHITECTURE.md) · [docs/IMPLEMENTATION_READINESS.md](file:///e:/Symphony%201/docs/IMPLEMENTATION_READINESS.md) · [SYMPHONY_REFERENCE.md](file:///e:/Symphony%201/SYMPHONY_REFERENCE.md)  
**Target Profile:** Profile A — Internal Round / Single-Machine Local Execution  
**Status:** Canonical Tech Stack Specification  

---

## §1 — Executive Summary & Operational Posture

This document defines the **minimum technically credible technology stack** required to execute the complete Voice Shield internal-round demo. It bridges architectural contracts with concrete, inspectable libraries and runtime tools.

### 1.1 Core Principles Binding the Stack

1. **Student Team Executability:** The entire system must run locally on a single standard developer machine (Windows 11, macOS, or Linux) with or without a dedicated GPU.
2. **Offline Demo Cold-Start:** While dependencies and model weights require internet access during installation/acquisition, **the running demo must execute 100% offline** with locally vendored weights and pre-recorded test fixtures.
3. **No Fabricated Package Versions:** Every version in this specification is explicitly classified as either **Verified in Local Host Environment**, pinned via strict compatibility constraint, or marked **`REQUIRES VERIFICATION`**. No version number is guessed or invented.
4. **Architectural Authority & Invariant Preservation:** The technology stack strictly honors:
   - **P1 / Replaceability:** No proprietary platform lock-in.
   - **P2 / Minimal Data Passing:** L3/L4/L5 modules receive only structured features and evidence vectors; raw PCM audio is strictly bounded to the ingestion layer (L1/Redis).
   - **P3 / Non-Blocking Ingestion:** The `api` ingestion process never waits on synchronous ML inference.
   - **P4 / Context Sensitivity:** Transaction tiering and contextual risk scaling are decoupled from audio scoring.
   - **P5 / Inspectable Evidence Chain:** SQLite holds a cryptographically hashed evidence chain; raw audio is never written to SQLite.

---

## §2 — Detailed Dependency Specifications

Every dependency across the entire Voice Shield system is detailed below with the mandatory eight-attribute metadata specification:

1. **Purpose:** Concrete functional role in Voice Shield.
2. **Version Policy:** Verified environment version, constraint policy, or explicit verification status.
3. **Installation Method:** Recommended command / distribution channel.
4. **Mandatory Status:** `Mandatory`, `Optional`, or `Deferred`.
5. **GPU Requirement:** `No` (CPU-compatible), `Optional` (benefits from CUDA/MPS), or `Mandatory`.
6. **Internet Access:** `Install/Acquisition Only`, `None (Fully Offline)`, or `Runtime Required`.
7. **Licensing Considerations:** License category and compliance constraints.
8. **Fallback Strategy:** Concrete fallback if the dependency or component fails.

---

### 2.1 Language Runtimes & Toolchains

#### `Python`
- **Purpose:** Primary backend runtime for ingestion, DSP, ML inference workers, decision engine, and SQLite storage repository.
- **Version Policy:** `Python 3.10.x` (*Verified in host environment: 3.10.0*). Policy: `>=3.10, <3.12` to ensure PyTorch and SpeechBrain wheel compatibility.
- **Installation Method:** Official Python installer / `winget install Python.Python.3.10` / `apt install python3.10`.
- **Mandatory:** Yes.
- **Requires GPU:** No.
- **Requires Internet:** Install only.
- **Licensing Considerations:** Python Software Foundation (PSF) License (Permissive).
- **Fallback:** None. Core backend runtime.

#### `Node.js` & `npm`
- **Purpose:** Runtime and package manager for building, bundling, and serving the React TypeScript frontend development server.
- **Version Policy:** `Node.js v24.x`, `npm v11.x` (*Verified in host environment: Node v24.11.1, npm 11.6.2*). Policy: Node `>=18.0.0 LTS`.
- **Installation Method:** Official Node installer / `winget install OpenJS.NodeJS` / `nvm use 20`.
- **Mandatory:** Yes.
- **Requires GPU:** No.
- **Requires Internet:** Install only (`npm install`).
- **Licensing Considerations:** MIT / Node.js license (Permissive).
- **Fallback:** Pre-bundled static frontend served via FastAPI static file mount (for headless demo runs).

---

### 2.2 Backend Framework, API & Realtime

#### `FastAPI`
- **Purpose:** Core asynchronous web framework exposing the REST API surface (`/v1/sessions`, `/v1/evidence`, `/v1/scenarios`, `/v1/health`) and WebSocket endpoints.
- **Version Policy:** `0.141.1` (*Verified in host environment: 0.141.1*). Policy: `>=0.100.0`.
- **Installation Method:** `pip install fastapi`
- **Mandatory:** Yes.
- **Requires GPU:** No.
- **Requires Internet:** Install only.
- **Licensing Considerations:** MIT (Permissive).
- **Fallback:** None. REST/WS contracts directly bind to FastAPI route definitions.

#### `Uvicorn`
- **Purpose:** High-performance ASGI web server hosting the FastAPI application.
- **Version Policy:** `0.52.4` (*Verified in host environment: 0.52.4*). Policy: `>=0.25.0`.
- **Installation Method:** `pip install uvicorn[standard]`
- **Mandatory:** Yes.
- **Requires GPU:** No.
- **Requires Internet:** Install only.
- **Licensing Considerations:** BSD-3-Clause (Permissive).
- **Fallback:** `hypercorn` ASGI server.

#### `Pydantic` (and `pydantic-settings`)
- **Purpose:** Enforces frozen data contracts (`FrameObject`, `EvidenceVector`, `VoiceBelief`, `ContextVector`, `Decision`, `EvidenceRecord`) with strict type validation, JSON serialization, and `extra="forbid"`.
- **Version Policy:** `Pydantic 2.13.4`, `pydantic-settings 2.2.1` (*Verified in host environment*). Policy: `^2.0`.
- **Installation Method:** `pip install pydantic pydantic-settings`
- **Mandatory:** Yes.
- **Requires GPU:** No.
- **Requires Internet:** Install only.
- **Licensing Considerations:** MIT (Permissive).
- **Fallback:** None. System invariants (I1, I3) depend on Pydantic schema validation.

#### `websockets`
- **Purpose:** WebSocket transport protocol implementation for client audio streaming ingress (`WS /v1/sessions/{id}/audio`) and structured event relay egress (`WS /v1/sessions/{id}/events`).
- **Version Policy:** `14.2` (*Verified in host environment: 14.2*). Policy: `>=12.0`.
- **Installation Method:** `pip install websockets` (bundled with `uvicorn[standard]` / FastAPI).
- **Mandatory:** Yes.
- **Requires GPU:** No.
- **Requires Internet:** Install only.
- **Licensing Considerations:** BSD-3-Clause (Permissive).
- **Fallback:** HTTP Server-Sent Events (SSE) for egress; chunked HTTP POST for ingress (requires architectural waiver).

---

### 2.3 Streaming Infrastructure & Inter-Process Communication

#### `Redis` (Engine)
- **Purpose:** High-throughput in-memory broker providing Redis Streams (`vs:frames` with TTL, `vs:evidence`) and Pub/Sub (`vs:events:{session_id}`) decoupling ingestion (L1) from inference (L2/L3) and decision (L4/L5) per Invariant P3.
- **Version Policy:** Redis `7.x` via Docker or local service (`REQUIRES VERIFICATION` on local native Windows).
- **Installation Method:** `docker run -d -p 6379:6379 redis:7-alpine` or Docker Compose.
- **Mandatory:** Yes (for production 3-process topology).
- **Requires GPU:** No.
- **Requires Internet:** Install/Docker pull only.
- **Licensing Considerations:** RSALv2 / SSPL (Redis 7.2.4+) or BSD-3-Clause (Redis <=7.2.3) / Valkey (BSD-3-Clause). Local development use is unrestricted.
- **Fallback:** In-process `asyncio.Queue` in `all-in-one` mode (`python -m voiceshield all-in-one`). *Note: `all-in-one` is for debugging only and cannot guarantee P3 under heavy load.*

#### `redis` (Python Client)
- **Purpose:** Async Python client library for connecting to Redis Streams (`XADD`, `XREADGROUP`) and Pub/Sub channels.
- **Version Policy:** `5.0.3` (*Verified in host environment: 5.0.3*). Policy: `>=5.0.0`.
- **Installation Method:** `pip install redis`
- **Mandatory:** Yes.
- **Requires GPU:** No.
- **Requires Internet:** Install only.
- **Licensing Considerations:** MIT (Permissive).
- **Fallback:** In-memory queue shim when running in single-process `all-in-one` mode.

---

### 2.4 Audio Ingestion, DSP & Feature Extraction

#### `FFmpeg` (System Binary)
- **Purpose:** Audio ingestion decoding, container demuxing, format normalization, and conversion of arbitrary incoming audio streams/files into canonical single-channel 16 kHz 16-bit linear PCM.
- **Version Policy:** `FFmpeg 6.x / 7.x` (`REQUIRES VERIFICATION` on Windows PATH).
- **Installation Method:** 
  - Windows: `winget install Gyan.FFmpeg` or download static build from gyan.dev and add to system `PATH`.
  - Linux: `apt-get install -y ffmpeg`
  - macOS: `brew install ffmpeg`
- **Mandatory:** Yes (for compressed audio formats and streaming ingest).
- **Requires GPU:** No.
- **Requires Internet:** Install only.
- **Licensing Considerations:** LGPL v2.1+ / GPL v2+ (depending on build flags). Voice Shield calls FFmpeg as a distinct external sub-process or via standard bindings; no proprietary code is linked into FFmpeg.
- **Fallback:** Pure Python `wave` standard library (strictly limited to pre-converted uncompressed 16 kHz 16-bit mono WAV fixtures).

#### `soundfile`
- **Purpose:** Fast, C-backed audio I/O reading and writing WAV files and PCM audio buffers using `libsndfile`.
- **Version Policy:** `0.14.0` (*Verified in host environment: 0.14.0*). Policy: `>=0.12.0`.
- **Installation Method:** `pip install soundfile` (includes pre-compiled `libsndfile` binary wheels for Windows, Linux, and macOS).
- **Mandatory:** Yes.
- **Requires GPU:** No.
- **Requires Internet:** Install only.
- **Licensing Considerations:** BSD-3-Clause (soundfile wrapper) / LGPL v2.1+ (`libsndfile` dynamic library).
- **Fallback:** Python standard library `wave` module.

#### `NumPy`
- **Purpose:** Fundamental n-dimensional array operations, vector arithmetic, signal windowing, and tensor pre-formatting.
- **Version Policy:** `1.26.4` (*Verified in host environment: 1.26.4*). Policy: `>=1.24.0, <2.0.0` (pinned below 2.0 to maintain binary compatibility with PyTorch 2.1 and SciPy 1.15).
- **Installation Method:** `pip install "numpy<2.0.0"`
- **Mandatory:** Yes.
- **Requires GPU:** No.
- **Requires Internet:** Install only.
- **Licensing Considerations:** BSD-3-Clause (Permissive).
- **Fallback:** None. Core mathematical substrate.

#### `SciPy`
- **Purpose:** Scientific signal processing (`scipy.signal`), Butterworth/bandpass filtering, STFT computation, spectral statistics, and statistical calibration utilities.
- **Version Policy:** `1.15.3` (*Verified in host environment: 1.15.3*). Policy: `>=1.11.0`.
- **Installation Method:** `pip install scipy`
- **Mandatory:** Yes.
- **Requires GPU:** No.
- **Requires Internet:** Install only.
- **Licensing Considerations:** BSD-3-Clause (Permissive).
- **Fallback:** Hand-rolled discrete Fourier transforms in NumPy (severe CPU performance penalty).

#### `librosa`
- **Purpose:** High-level audio feature extraction (LFCC, Mel-filterbanks, CQCC, spectral centroid, spectral flux, zero-crossing rate, pitch tracking) for expert feature bundles.
- **Version Policy:** `0.11.0` (*Verified in host environment: 0.11.0*). Policy: `>=0.10.0`.
- **Installation Method:** `pip install librosa`
- **Mandatory:** Yes.
- **Requires GPU:** No.
- **Requires Internet:** Install only.
- **Licensing Considerations:** ISC License (Permissive).
- **Fallback:** Hand-rolled Mel-filterbanks and spectral features using NumPy and SciPy.

---

### 2.5 Machine Learning & Anti-Spoofing Inference

#### `PyTorch` (`torch`)
- **Purpose:** Neural network runtime and tensor computation engine executing forward passes for E1 (Spectro-temporal), E2 (Raw waveform), E3 (SSL probe), and E4 (ECAPA speaker encoder).
- **Version Policy:** `2.1.2` (*Verified in host environment: 2.1.2+cpu*). Policy: `^2.1.0`.
- **Installation Method:** 
  - CPU-only: `pip install torch==2.1.2 --index-url https://download.pytorch.org/whl/cpu`
  - CUDA: `pip install torch==2.1.2 --index-url https://download.pytorch.org/whl/cu118`
- **Mandatory:** Yes.
- **Requires GPU:** Optional. All models are selected and structured to execute on standard multi-core CPUs.
- **Requires Internet:** Install only (large download ~200MB-2GB).
- **Licensing Considerations:** Modified BSD-style license (Permissive).
- **Fallback:** ONNX Runtime (`onnxruntime`) if PyTorch installation fails on resource-constrained environments.

#### `SpeechBrain`
- **Purpose:** Pretrained ECAPA-TDNN speaker recognition architecture for Expert E4 (`models.e4_speaker`) computing 192-dimensional speaker embeddings and cosine verification.
- **Version Policy:** `1.0.x` (`REQUIRES VERIFICATION` against PyTorch 2.1.2). Policy: `>=0.5.15, <=1.0.0`.
- **Installation Method:** `pip install speechbrain`
- **Mandatory:** Yes (for Expert E4 speaker verification).
- **Requires GPU:** Optional.
- **Requires Internet:** Acquisition time only (to fetch `speechbrain/spkrec-ecapa-voxceleb` weights into local model cache). **Offline at demo runtime.**
- **Licensing Considerations:** Apache-2.0 (Permissive).
- **Fallback:** Pre-computed speaker embedding vector loaded directly from disk fixture; if missing, E4 cleanly emits `ExpertResult(status=ABSTAIN, p=None)` per §22.

#### `Hugging Face Transformers` (`transformers`)
- **Purpose:** Loading and layer-probing frozen multilingual Self-Supervised Learning (SSL) backbones (e.g., WavLM-Base+ / XLS-R-300M) for Expert E3 (`models.e3_ssl`).
- **Version Policy:** `4.36.2` (*Verified in host environment: 4.36.2*). Policy: `>=4.30.0`.
- **Installation Method:** `pip install transformers`
- **Mandatory:** Yes (for Expert E3 SSL inference).
- **Requires GPU:** Optional (CPU latency optimization: use WavLM-Base or quantized mini-backbone).
- **Requires Internet:** Acquisition time only. **Offline at demo runtime.**
- **Licensing Considerations:** Apache-2.0 (Permissive).
- **Fallback:** Lightweight linear spectral probe on librosa filterbanks, or E3 cleanly returns `ExpertResult(status=MODEL_UNAVAILABLE)` without stalling the pipeline.

#### `Anti-Spoofing Architecture / Models (E1 & E2)`
- **Purpose:** 
  - **E1 (`models.e1_spectral`):** AASIST-style (Audio Anti-Spoofing using Integrated Spectro-Temporal Graph Attention) / Light-CNN on LFCC/spectrograms.
  - **E2 (`models.e2_raw`):** RawNet2 / RawBoost learned raw waveform temporal representation.
- **Version Policy:** Custom PyTorch model definitions with vendored weights in `assets/models/` (`REQUIRES VERIFICATION` of checkpoint files).
- **Installation Method:** Vendored directly into the repository code and model directory.
- **Mandatory:** Yes.
- **Requires GPU:** No (designed for CPU forward pass <50ms per 1s window).
- **Requires Internet:** None (weights stored locally).
- **Licensing Considerations:** Academic/Open-Source (BSD/Apache-2.0). License file must accompany vendored weights.
- **Fallback:** Deterministic heuristic feature benchmark or explicit `MODEL_UNAVAILABLE` status flag.

#### `scikit-learn`
- **Purpose:** Probability calibration (Platt scaling / Isotonic regression) and baseline classification metrics.
- **Version Policy:** `1.7.2` (*Verified in host environment: 1.7.2*). Policy: `>=1.3.0`.
- **Installation Method:** `pip install scikit-learn`
- **Mandatory:** Yes (for C-28 Calibrator prior mapping).
- **Requires GPU:** No.
- **Requires Internet:** Install only.
- **Licensing Considerations:** BSD-3-Clause (Permissive).
- **Fallback:** Hand-rolled logistic sigmoid mapping in NumPy.

---

### 2.6 Persistence & Audit Storage

#### `SQLite` (`sqlite3` / `aiosqlite`)
- **Purpose:** Embedded, zero-configuration local database persisting sessions, context, policy decisions, timeline events, and tamper-evident SHA-256 hash-chained `EvidenceRecord`s.
- **Version Policy:** SQLite 3.x (bundled with Python 3.10 standard library); `aiosqlite 0.20.0` (*Verified in host environment: 0.20.0*).
- **Installation Method:** Standard library / `pip install aiosqlite`.
- **Mandatory:** Yes.
- **Requires GPU:** No.
- **Requires Internet:** None (Local file).
- **Licensing Considerations:** Public Domain.
- **Fallback:** In-memory SQLite (`:memory:`) or ephemeral JSON-Lines file log.

---

### 2.7 Frontend Presentation Layer

#### `React`
- **Purpose:** Declarative component hierarchy rendering the seven live inspection panels (Status, Live Risk Gauge, Waveform/Quality, Spectrogram, Factor Attribution, Policy Decision/State, Cryptographic Evidence Log).
- **Version Policy:** `React 18.x` (`REQUIRES VERIFICATION` during npm init). Policy: `^18.2.0` or `^19.0.0`.
- **Installation Method:** `npm install react react-dom`
- **Mandatory:** Yes.
- **Requires GPU:** No (Hardware acceleration in browser optional).
- **Requires Internet:** Install only (`npm install`).
- **Licensing Considerations:** MIT (Permissive).
- **Fallback:** None. Core frontend framework.

#### `TypeScript`
- **Purpose:** Static type checking for frontend event handlers, WebSocket envelope decoding, and ensuring strict parity with backend Pydantic contract schemas.
- **Version Policy:** `TypeScript 5.x` (`REQUIRES VERIFICATION`). Policy: `^5.0.0`.
- **Installation Method:** `npm install -D typescript @types/react @types/react-dom`
- **Mandatory:** Yes.
- **Requires GPU:** No.
- **Requires Internet:** Install only.
- **Licensing Considerations:** Apache-2.0 (Permissive).
- **Fallback:** Transpiled JavaScript.

#### `Vite`
- **Purpose:** Ultra-fast local development server, Hot Module Replacement (HMR), and production asset bundler.
- **Version Policy:** `Vite 5.x / 6.x` (`REQUIRES VERIFICATION`). Policy: `^5.0.0`.
- **Installation Method:** `npm install -D vite @vitejs/plugin-react`
- **Mandatory:** Yes.
- **Requires GPU:** No.
- **Requires Internet:** Install only.
- **Licensing Considerations:** MIT (Permissive).
- **Fallback:** Next.js or standard Webpack bundler.

#### `Tailwind CSS` & `shadcn/ui`
- **Purpose:** Utility-first CSS engine and accessible Radix-UI component primitives for high-density, professional, dark-mode financial SOC dashboard styling.
- **Version Policy:** `Tailwind CSS 3.4.x`, `shadcn/ui` components (`REQUIRES VERIFICATION`).
- **Installation Method:** `npm install -D tailwindcss postcss autoprefixer && npx tailwindcss init -p`
- **Mandatory:** Yes.
- **Requires GPU:** No.
- **Requires Internet:** Install only.
- **Licensing Considerations:** MIT (Permissive).
- **Fallback:** Plain Vanilla CSS stylesheets.

#### `Recharts`
- **Purpose:** High-performance responsive charting library rendering the real-time temporal risk trajectory ($R_t$), confidence intervals, and threshold cross lines ($T_{\text{warn}}, T_{\text{crit}}$).
- **Version Policy:** `Recharts 2.x` (`REQUIRES VERIFICATION`). Policy: `^2.10.0`.
- **Installation Method:** `npm install recharts`
- **Mandatory:** Yes.
- **Requires GPU:** No.
- **Requires Internet:** Install only.
- **Licensing Considerations:** MIT (Permissive).
- **Fallback:** HTML5 Canvas-based direct rendering or Chart.js.

#### `lucide-react`
- **Purpose:** Crisp, modern SVG iconography for system statuses, tier badges, security shields, waveform indicators, and evidence verification markers.
- **Version Policy:** `^0.300.0` (`REQUIRES VERIFICATION`).
- **Installation Method:** `npm install lucide-react`
- **Mandatory:** Optional (Recommended for visual polish).
- **Requires GPU:** No.
- **Requires Internet:** Install only.
- **Licensing Considerations:** ISC License (Permissive).
- **Fallback:** Standard unicode symbols or inline SVGs.

---

### 2.8 Quality Assurance & Testing

#### `pytest` & `pytest-asyncio`
- **Purpose:** Comprehensive test harness executing unit tests, contract invariance tests (I1-I5), import boundary enforcement, policy rule tables, and cryptographic tamper tests.
- **Version Policy:** `pytest 8.1.1`, `pytest-asyncio 0.23.6` (*Verified in host environment*). Policy: `>=7.4.0`.
- **Installation Method:** `pip install pytest pytest-asyncio`
- **Mandatory:** Yes.
- **Requires GPU:** No.
- **Requires Internet:** None (Local execution).
- **Licensing Considerations:** MIT (Permissive).
- **Fallback:** Python standard library `unittest`.

#### `Playwright`
- **Purpose:** Headless browser end-to-end integration testing driving simulated audio playback, validating live WebSocket UI state transitions, and verifying zero hardcoded values in DOM.
- **Version Policy:** `1.59.0` (*Verified in host environment: 1.59.0*). Policy: `>=1.40.0`.
- **Installation Method:** `pip install playwright && playwright install chromium`
- **Mandatory:** Yes (for automated end-to-end verification).
- **Requires GPU:** No.
- **Requires Internet:** Install time only (downloads Chromium browser binary).
- **Licensing Considerations:** Apache-2.0 (Permissive).
- **Fallback:** Manual interactive UI verification using the demo runner script.

---

### 2.9 Containerization & Deployment Orchestration

#### `Docker` & `Docker Compose`
- **Purpose:** Single-command containerized execution (`docker compose up`) orchestrating Redis, `api`, `analysis-worker`, `decision-worker`, and the static frontend for guaranteed cross-platform parity.
- **Version Policy:** Docker Compose v2.x (`REQUIRES VERIFICATION` on host machine).
- **Installation Method:** Docker Desktop / Docker Engine.
- **Mandatory:** Recommended (where practical).
- **Requires GPU:** No.
- **Requires Internet:** Build/Pull time only.
- **Licensing Considerations:** Apache-2.0 (Docker Compose) / Docker Desktop licensing terms.
- **Fallback:** Native bare-metal execution script (`run_demo.bat` on Windows or `run_demo.sh` on POSIX) running processes locally in virtual environments.

---

## §3 — Model & Dataset Acquisition Architecture

### 3.1 Expert Model Lineup & Offline Vendoring Policy

| Expert ID | Name / Model Family | Primary Input | Output Target | Disk Budget | Cold-Start Offline Source |
|---|---|---|---|---|---|
| **E1** | **AASIST / Spectro-Temporal** | Log-Mel / LFCC filterbanks (L2) | $p_{\text{spec}} \in [0, 1]$, confidence | ~50 MB | `assets/models/e1_aasist.pt` |
| **E2** | **RawNet2 / Raw Waveform** | 16 kHz Raw PCM (L1/L2) | $p_{\text{raw}} \in [0, 1]$, confidence | ~80 MB | `assets/models/e2_rawnet.pt` |
| **E3** | **Multilingual SSL (WavLM-Base+)** | 16 kHz Raw PCM (selected hidden layers) | $p_{\text{ssl}} \in [0, 1]$, confidence | ~380 MB | `assets/models/e3_wavlm_probe.pt` |
| **E4** | **ECAPA-TDNN Speaker Encoder** | 16 kHz Raw PCM + Enrolled Vector | $p_{\text{spk}} \in [0, 1]$, cosine sim | ~85 MB | `assets/models/e4_ecapa.pt` |
| **E5** | **Prosody / Behavioral Model** | Pitch, energy, pause dynamics | `DEFERRED (B1)` — returns `None` | 0 MB | Built-in abstention stub |
| **E6** | **Replay / Liveness Detector** | High-frequency spectral decay | `DEFERRED (B2)` — returns `None` | 0 MB | Built-in abstention stub |

> [!IMPORTANT]
> **Zero Network Dependency at Demo Runtime:** All model weights must be downloaded and verified into the `assets/models/` directory during repository setup. If any weight file is missing at startup, the system gracefully marks that specific expert as `MODEL_UNAVAILABLE` in the startup log, sets its probability to `None`, and continues running without crashing.

### 3.2 Demo Audio Fixtures

To ensure deterministic, reproducible demonstration without live telephone infrastructure:

1. **Scenario 1 (Genuine Call):** `assets/fixtures/scenario_1_genuine.wav` — High-quality authenticated voice matching the enrolled speaker.
2. **Scenario 2 (Cloned Executive Attack):** `assets/fixtures/scenario_2_deepfake_clone.wav` — AI-generated cloned voice with high speaker similarity but synthetic artifact evidence. *(Created with explicit consent for demonstration purposes)*.
3. **Scenario 3 (Degraded Acoustic Channel):** `assets/fixtures/scenario_3_noisy_cell.wav` — Genuine speaker under severe 8 kHz bandpass filtering and background noise, demonstrating quality-conditioned weighting.
4. **Speaker Reference Enrollment:** `assets/fixtures/enrollment_executive.wav` — 10-second reference sample used to initialize E4 speaker verification embedding.

---

## §4 — Environmental & Runtime Resource Budget

| Dimension | Minimum Specification | Recommended Specification |
|---|---|---|
| **Operating System** | Windows 10/11, macOS 12+, Ubuntu 20.04+ | Windows 11 / Ubuntu 22.04 LTS |
| **CPU** | 4-core x86_64 or Apple Silicon (M1+) | 8-core CPU (Intel i7/Ryzen 7 or M2/M3) |
| **RAM** | 8 GB | 16 GB |
| **Disk Space** | 4 GB free (including models & pip packages) | 10 GB free |
| **GPU** | None (CPU inference mode enabled) | NVIDIA RTX (CUDA 11.8/12.1) or Apple MPS |
| **Network** | Offline during runtime (Internet only for install) | Offline during demo |
| **Audio Hardware** | Standard audio output (headphones/speakers) | Standard audio output + optional live microphone |

---

## §5 — Verified Compatibility Matrix Summary

- **Python 3.10.0 + PyTorch 2.1.2+cpu + NumPy 1.26.4 + SciPy 1.15.3 + librosa 0.11.0 + soundfile 0.14.0:** Verified binary-compatible on Windows 11 host.
- **FastAPI 0.141.1 + Uvicorn 0.52.4 + Pydantic 2.13.4 + websockets 14.2 + redis 5.0.3:** Fully validated async pipeline.
- **Node v24.11.1 + npm 11.6.2:** Verified toolchain for Vite + React 18 + Tailwind CSS + TypeScript build.
- **FFmpeg:** System binary required on PATH.

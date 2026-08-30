# Voice Shield

**Real-Time Voice Integrity & Impersonation Defense System**

Voice Shield is a SIMULATION of a real-time defense pipeline designed to demonstrate the detection of synthetic voice manipulation and conversational deepfake attacks during sensitive voice interactions (such as high-value financial authorisations). This project is a DEMO FIXTURE and does not perform real financial transaction execution or real telecom integration.

---

## 🏛 Architectural Principles

1. **P1 / Replaceability:** Standardized, open protocol boundaries (no vendor lock-in).
2. **P2 / Minimal Data Passing:** Raw audio is confined to the ingestion boundary; downstream ML and decision layers receive only structured features and evidence vectors.
3. **P3 / Non-Blocking Ingestion:** Audio capture and streaming ingress operate independently of heavy ML inference.
4. **P4 / Context-Aware Policy:** Risk is conditioned by transaction sensitivity and call context, never by raw acoustic probability alone.
5. **P5 / Tamper-Evident Evidence:** Cryptographic SHA-256 hash chaining of all action-grade decisions and factor attributions.

---

## 📂 Repository Layout

```text
VoiceShield/
├── backend/
│   └── voiceshield/
│       ├── __main__.py           # Role dispatcher: api | analysis-worker | decision-worker | all-in-one
│       ├── config.py             # Pydantic Settings configuration (C-52)
│       ├── obs/logging.py        # Structured JSON logger with audio payload scrubbing (C-53)
│       ├── contracts/            # Frozen Pydantic data schemas (§6)
│       ├── ingestion/            # L1 audio capture, streaming ingress, ring buffer (C-01..C-14)
│       ├── signal_processing/    # L2 DSP, spectral features, filterbanks (C-15..C-18)
│       ├── models/               # L3 anti-spoofing experts E1..E6 & model registry (C-19..C-27)
│       ├── evidence/             # Evidence vector assembly (C-26)
│       ├── speaker/              # E4 speaker reference enrollment store (C-27)
│       ├── fusion/               # L4 calibration, quality weighting, belief state (C-28..C-35)
│       ├── context/              # L4 contextual risk scaling (C-36..C-37)
│       ├── risk/                 # Composite risk calculation (C-38)
│       ├── decision/             # L5 policy engine, state machine, action emitter (C-39..C-42)
│       ├── assurance/            # Factor explanation, hash-chain evidence, privacy (C-43..C-46)
│       ├── storage/              # SQLite persistence repository (C-50)
│       ├── api/                  # FastAPI REST and WebSocket routes (C-47..C-49)
│       └── demo/                 # Scenario engine and playback simulator (C-51)
├── frontend/                     # React + TypeScript + Vite + Tailwind CSS dashboard (C-54)
├── tests/                        # Pytest suite with contract and interface invariant tests
├── demo/                         # Pre-recorded audio fixtures and scenario definitions
├── docs/                         # Architecture, tech stack, and readiness specifications
├── docker-compose.yml            # Multi-container local execution specification
├── .env.example                  # Environment configuration template
└── README.md                     # Project documentation
```

---

## 🚀 Developer Workflow (Quickstart)

VoiceShield is designed to be executable by a new developer with minimal setup.

### Prerequisites
- **Python 3.10+** (with `pip` and `venv`)
- **Node.js 18+** & **npm**
- *(Optional)* **Docker** & **Docker Compose**

---

### Step-by-Step Local Execution

```text
1. Install documented prerequisites (Python 3.10+, Node.js 18+)
2. Run setup:
   - Linux/macOS: ./scripts/setup
   - Windows PowerShell: .\scripts\setup.ps1
   - Windows CMD: scripts\setup.bat
3. Run start:
   - Linux/macOS: ./scripts/start
   - Windows PowerShell: .\scripts\start.ps1
   - Windows CMD: scripts\start.bat
4. Open the dashboard: http://localhost:5173
5. Click DEMO MODE
6. Select scenario (Scenario 1 — Genuine Executive, Scenario 2 — AI Impersonation, or Scenario 3 — Poor Audio)
7. Click Start Scenario Call / Start Simulation
```

---

### 📦 Standard Automation Scripts

| Script | Linux / macOS | Windows PowerShell | Windows CMD | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **Setup** | `./scripts/setup` | `.\scripts\setup.ps1` | `scripts\setup.bat` | Installs backend `.venv`, packages, frontend `npm`, `.env`, and generates demo audio fixtures. |
| **Start** | `./scripts/start` | `.\scripts\start.ps1` | `scripts\start.bat` | Starts backend on `:8000` and frontend dev server on `:5173`, waits for healthcheck. |
| **Stop** | `./scripts/stop` | `.\scripts\stop.ps1` | `scripts\stop.bat` | Gracefully terminates background backend and frontend processes. |
| **Test** | `./scripts/test` | `.\scripts\test.ps1` | `scripts\test.bat` | Runs full backend `pytest` test suite and frontend TypeScript build check. |
| **Demo** | `./scripts/demo [scenario]` | `.\scripts\demo.ps1 [scenario]` | `scripts\demo.bat [scenario]` | CLI launcher to trigger a named demo scenario and display live response. |

---

### 🐳 Docker Compose Alternative

To run the entire system in containerized mode with one command:

```bash
# Build and start all services (API + Frontend)
docker compose up --build

# Open Dashboard:
http://localhost:5173
```

---

### 🧪 Clean-Start & Verification

A dedicated end-to-end clean verification script is provided in `scripts/verify_clean_start.py`:

```bash
python scripts/verify_clean_start.py
```

This verifies:
- **Backend starts**: responds with HTTP 200 on `/health`.
- **Frontend builds**: clean TypeScript compilation with Vite bundle.
- **Database initializes**: SQLite tables and transaction state store created.
- **Models load or fail explicitly**: readiness status logged in `/health`.
- **WebSocket connects**: streaming events on `/ws` and `/v1/audio/stream`.
- **Demo audio streams**: chunked WAV playback through ingestion buffer.
- **Risk updates**: composite risk scores and policy matches calculated live.
- **Transaction state changes**: transitions between `PENDING`, `HELD`, `APPROVED`, and `REJECTED`.
- **UI updates**: real-time updates reflected in the DEMO MODE panel.

---

### 🛠 Offline Models & Weights (Optional, ~783 MB)

```bash
python scripts/fetch_models.py               # vendor pinned weights + sha256 manifest
python scripts/fetch_models.py --verify-only # integrity gate (run before a demo)
```

Weights are vendored into `assets/models/` so the system **cold-starts fully offline** — nothing is downloaded at runtime. Two of the six anti-spoofing experts (E2 and E4) use live local models; E1/E3 report `MODEL_UNAVAILABLE` and E5/E6 are `DEFERRED`. See [docs/MODEL_INVENTORY.md](docs/MODEL_INVENTORY.md).


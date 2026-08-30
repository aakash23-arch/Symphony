# DEPENDENCY MATRIX — VOICE SHIELD

**Document Authority:** [docs/EXECUTION_TECH_STACK.md](file:///e:/Symphony%201/docs/EXECUTION_TECH_STACK.md) · [docs/EXECUTABLE_ARCHITECTURE.md](file:///e:/Symphony%201/docs/EXECUTABLE_ARCHITECTURE.md)  
**Scope:** Internal-Round Executable Demo (Profile A)  
**Status:** Canonical Reference Matrix  

---

| Dependency | Purpose | Required | Installation | Verification Command | Fallback |
|---|---|---|---|---|---|
| **Python** | Backend runtime for API, DSP, ML, and decision workers | Yes (Mandatory) | Download from python.org / `winget install Python.Python.3.10` / `apt install python3.10` | `python --version` | None (core runtime) |
| **Node.js & npm** | Frontend build environment & package manager | Yes (Mandatory) | Download from nodejs.org / `winget install OpenJS.NodeJS` / `nvm install 20` | `node -v && npm -v` | Serve pre-built static bundle via FastAPI |
| **FastAPI** | REST API endpoints & WebSocket routing | Yes (Mandatory) | `pip install fastapi` | `python -c "import fastapi; print(fastapi.__version__)"` | None (contracts bind to FastAPI) |
| **Uvicorn** | ASGI server for running the FastAPI application | Yes (Mandatory) | `pip install uvicorn[standard]` | `python -c "import uvicorn; print(uvicorn.__version__)"` | `hypercorn` ASGI server |
| **Pydantic** | Frozen schema validation and data serialization (`extra="forbid"`) | Yes (Mandatory) | `pip install pydantic pydantic-settings` | `python -c "import pydantic; print(pydantic.__version__)"` | None (invariant enforcement depends on it) |
| **websockets** | WebSocket transport protocol handler | Yes (Mandatory) | `pip install websockets` | `python -c "import websockets; print(websockets.__version__)"` | Server-Sent Events (SSE) for egress / chunked POST |
| **Redis (Engine)** | In-memory message broker for Redis Streams (`vs:frames`, `vs:evidence`) & Pub/Sub | Yes (Mandatory in 3-process mode) | `docker run -d -p 6379:6379 redis:7-alpine` or native Redis service | `docker exec -it <container_id> redis-cli ping` or `redis-cli ping` | In-memory `asyncio.Queue` via `all-in-one` process mode |
| **redis (Python)** | Async client for Redis Streams and Pub/Sub communication | Yes (Mandatory) | `pip install redis` | `python -c "import redis; print(redis.__version__)"` | In-memory queue shim in `all-in-one` mode |
| **FFmpeg** | System binary for audio decoding, demuxing, and 16 kHz 16-bit mono PCM transcoding | Yes (Mandatory for general audio formats) | Windows: `winget install Gyan.FFmpeg`<br>Linux: `apt-get install -y ffmpeg`<br>macOS: `brew install ffmpeg` | `ffmpeg -version` | Python standard library `wave` (strictly for 16 kHz 16-bit PCM WAV) |
| **soundfile** | C-backed audio buffer & WAV file read/write using libsndfile | Yes (Mandatory) | `pip install soundfile` | `python -c "import soundfile; print(soundfile.__version__)"` | Python standard library `wave` module |
| **NumPy** | High-performance N-dimensional array processing and vector math | Yes (Mandatory) | `pip install "numpy<2.0.0"` | `python -c "import numpy; print(numpy.__version__)"` | None (fundamental mathematical substrate) |
| **SciPy** | Scientific digital signal processing, filtering, and STFT transforms | Yes (Mandatory) | `pip install scipy` | `python -c "import scipy; print(scipy.__version__)"` | Hand-rolled discrete Fourier transforms in NumPy |
| **librosa** | Audio feature extraction (LFCC, Mel-filterbanks, CQCC, spectral statistics) | Yes (Mandatory) | `pip install librosa` | `python -c "import librosa; print(librosa.__version__)"` | Custom Mel filterbank and spectral feature extraction via SciPy |
| **PyTorch (`torch`)** | Deep learning tensor engine and model inference execution | Yes (Mandatory) | `pip install torch==2.1.2 --index-url https://download.pytorch.org/whl/cpu` | `python -c "import torch; print(torch.__version__)"` | ONNX Runtime (`onnxruntime`) |
| **SpeechBrain** | Pretrained ECAPA-TDNN speaker recognition architecture (Expert E4) | Yes (Mandatory for E4) | `pip install speechbrain` | `python -c "import speechbrain; print(speechbrain.__version__)"` | Pre-computed speaker embedding vector from disk fixture; or emit `ABSTAIN` |
| **Hugging Face Transformers** | Self-Supervised Learning (SSL) model loader and layer probe (Expert E3) | Yes (Mandatory for E3) | `pip install transformers` | `python -c "import transformers; print(transformers.__version__)"` | Lightweight linear spectral probe on filterbanks, or emit `MODEL_UNAVAILABLE` |
| **Anti-Spoofing Models (E1/E2)** | AASIST spectro-temporal (E1) and RawNet raw waveform (E2) detectors | Yes (Mandatory) | Vendored checkpoint weights placed in `assets/models/` | `python -c "import os; assert os.path.exists('assets/models/e1_aasist.pt')"` | Deterministic heuristic benchmark; or emit `MODEL_UNAVAILABLE` |
| **scikit-learn** | Probability calibration (Platt scaling / Isotonic regression) | Yes (Mandatory) | `pip install scikit-learn` | `python -c "import sklearn; print(sklearn.__version__)"` | Hand-rolled logistic sigmoid mapping in NumPy |
| **SQLite (`sqlite3` / `aiosqlite`)** | Local zero-configuration relational database for session metadata & hash-chained evidence | Yes (Mandatory) | Bundled with Python standard library / `pip install aiosqlite` | `python -c "import sqlite3, aiosqlite; print(sqlite3.sqlite_version, aiosqlite.__version__)"` | In-memory SQLite (`:memory:`) or JSON-Lines audit log file |
| **React** | Reactive UI framework for the financial fraud operations dashboard | Yes (Mandatory) | `npm install react react-dom` | `node -e "console.log(require('react/package.json').version)"` | None (core frontend UI library) |
| **TypeScript** | Static typing ensuring frontend event schema parity with backend Pydantic models | Yes (Mandatory) | `npm install -D typescript @types/react @types/react-dom` | `npx tsc -v` | Transpiled plain JavaScript |
| **Vite** | Frontend dev server, Hot Module Replacement (HMR), and production bundler | Yes (Mandatory) | `npm install -D vite @vitejs/plugin-react` | `npx vite -v` | Next.js or standard Webpack build |
| **Tailwind CSS** | Utility-first CSS styling engine for dark-mode SOC dashboard | Yes (Mandatory) | `npm install -D tailwindcss postcss autoprefixer` | `npx tailwindcss -v` | Plain vanilla CSS stylesheets |
| **shadcn/ui** | Accessible, headless UI component primitives (Radix UI) | Yes (Mandatory) | Installed via `shadcn/ui` CLI or component copy | `cat components.json` or check `src/components/ui/` | Custom styled React components |
| **Recharts** | Real-time temporal risk trajectory chart ($R_t$, bands, and thresholds) | Yes (Mandatory) | `npm install recharts` | `node -e "console.log(require('recharts/package.json').version)"` | HTML5 Canvas-based direct chart or Chart.js |
| **lucide-react** | Clean vector iconography for system security states and panel indicators | Optional (Recommended) | `npm install lucide-react` | `node -e "console.log(require('lucide-react/package.json').version)"` | Unicode symbols or inline SVG assets |
| **pytest & pytest-asyncio** | Unit, contract invariance (I1-I5), policy rule-table, and tamper test suite | Yes (Mandatory) | `pip install pytest pytest-asyncio` | `pytest --version` | Python standard library `unittest` |
| **Playwright** | End-to-end headless browser test suite verifying live WebSocket UI rendering | Yes (Mandatory for E2E) | `pip install playwright && playwright install chromium` | `playwright --version` | Manual interactive UI smoke test |
| **Docker & Docker Compose** | Multi-container runtime packaging for Redis, API, and workers | Optional (Recommended) | Install Docker Desktop / Docker Engine | `docker --version && docker compose version` | Native shell run script (`run_demo.bat` / `run_demo.sh`) |

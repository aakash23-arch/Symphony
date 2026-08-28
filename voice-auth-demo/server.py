"""
server.py — API + static host for the redesigned web frontend.
================================================================
Thin FastAPI wrapper around the existing detection pipeline
(features.py / risk_engine.py, both untouched). The Streamlit app
(app.py) is kept as-is; this is an alternate, fully custom frontend
for the same backend logic.

Now includes a WebSocket endpoint (/api/stream) for true real-time
streaming inference. Audio chunks (Int16 PCM) are sent from the
browser every ~500 ms, analyzed on a sliding 3-second buffer, and
results are streamed back as JSON — no need to finish recording first.
"""

import asyncio
import io
import json
import os
from typing import Optional

import numpy as np
import soundfile as sf
from fastapi import FastAPI, File, Form, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from features import extract_features
from risk_engine import run_pipeline

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
SAMPLE_PATH = os.path.join(BASE_DIR, "sample_audio", "synthetic_sample.wav")

app = FastAPI(title="Voice Authenticity Engine API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _flag(v: str) -> bool:
    return str(v).lower() in ("1", "true", "yes", "on")


# ------------------------------------------------------------------ REST ---

@app.post("/api/analyze")
async def analyze(
    audio: Optional[UploadFile] = File(None),
    use_sample: str = Form("false"),
    unknown_number: str = Form("false"),
    transaction_request: str = Form("false"),
    high_urgency: str = Form("false"),
    allow_max: float = Form(30),
    flag_max: float = Form(65),
):
    if _flag(use_sample):
        if not os.path.exists(SAMPLE_PATH):
            return JSONResponse(
                {"error": "Bundled sample not found. Run synth_bootstrap.py first."},
                status_code=404,
            )
        with open(SAMPLE_PATH, "rb") as f:
            raw = f.read()
    elif audio is not None:
        raw = await audio.read()
    else:
        return JSONResponse({"error": "No audio provided."}, status_code=400)

    try:
        y, sr = sf.read(io.BytesIO(raw), always_2d=False)
    except Exception:
        return JSONResponse(
            {"error": "Could not decode audio. Try a WAV/FLAC file."},
            status_code=400,
        )

    if y.ndim > 1:
        y = np.mean(y, axis=1)
    y = y.astype(np.float32)

    raw_features = extract_features(y, sr)
    result = run_pipeline(
        raw_features,
        _flag(unknown_number),
        _flag(transaction_request),
        _flag(high_urgency),
        allow_max=allow_max,
        flag_max=flag_max,
    )

    return JSONResponse(
        {
            "acoustic_risk": result.acoustic_risk,
            "composite_risk": result.composite_risk,
            "action": result.action,
            "feature_contributions": result.feature_contributions,
            "metadata_contributions": result.metadata_contributions,
            "raw_features": raw_features,
            "duration_sec": round(len(y) / sr, 2),
            "sample_rate": sr,
        }
    )


# --------------------------------------------------------------- WebSocket ---

@app.websocket("/api/stream")
async def stream(ws: WebSocket):
    """
    Real-time streaming inference over WebSocket.

    Browser protocol
    ----------------
    1. Client sends a JSON init message as soon as the socket opens:
         { "type": "init", "sampleRate": 44100,
           "unknownNumber": true, "transactionRequest": true,
           "highUrgency": false, "allowMax": 30, "flagMax": 65 }
    2. Client sends raw binary Int16 PCM (mono) chunks every ~500 ms.
    3. Client can send JSON metadata updates at any time mid-recording:
         { "type": "metadata", "unknownNumber": false, ... }
    4. Client closes the socket when recording stops.

    Server responds after every binary chunk with analysis JSON:
         { "acoustic_risk": 42.1, "composite_risk": 51.3,
           "action": "FLAG_FOR_CALLBACK",
           "feature_contributions": [...],
           "metadata_contributions": [...],
           "buffer_sec": 2.5 }
    """
    await ws.accept()

    # Per-connection state
    sr = 44100
    buffer: np.ndarray = np.array([], dtype=np.float32)
    MAX_BUFFER_SEC = 3
    MIN_ANALYZE_SEC = 0.5  # need at least this much audio before analyzing

    unknown_number = False
    transaction_request = False
    high_urgency = False
    allow_max = 30.0
    flag_max = 65.0

    loop = asyncio.get_event_loop()

    try:
        while True:
            msg = await ws.receive()

            # ---- binary audio chunk ----------------------------------------
            if msg.get("bytes") is not None:
                raw_bytes = msg["bytes"]
                chunk = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0

                # Append to sliding buffer
                buffer = np.concatenate([buffer, chunk])
                max_samples = int(sr * MAX_BUFFER_SEC)
                if len(buffer) > max_samples:
                    buffer = buffer[-max_samples:]

                # Wait until we have enough audio to produce meaningful features
                if len(buffer) < int(sr * MIN_ANALYZE_SEC):
                    continue

                # Run feature extraction in a thread pool so the async loop isn't blocked
                _buf = buffer.copy()
                _sr = sr
                _unk, _txn, _urg = unknown_number, transaction_request, high_urgency
                _amax, _fmax = allow_max, flag_max

                def _run_analysis():
                    feats = extract_features(_buf, _sr)
                    return run_pipeline(
                        feats, _unk, _txn, _urg,
                        allow_max=_amax, flag_max=_fmax,
                    )

                try:
                    result = await loop.run_in_executor(None, _run_analysis)
                    await ws.send_json({
                        "acoustic_risk":        result.acoustic_risk,
                        "composite_risk":       result.composite_risk,
                        "action":               result.action,
                        "feature_contributions": result.feature_contributions,
                        "metadata_contributions": result.metadata_contributions,
                        "buffer_sec":           round(len(buffer) / sr, 1),
                    })
                except Exception:
                    # Skip this frame — short/silent chunks may throw in librosa
                    pass

            # ---- JSON metadata / init message ------------------------------
            elif msg.get("text") is not None:
                try:
                    data = json.loads(msg["text"])
                    msg_type = data.get("type", "")
                    if msg_type in ("init", "metadata"):
                        sr                = int(data.get("sampleRate", sr))
                        unknown_number    = bool(data.get("unknownNumber",    unknown_number))
                        transaction_request = bool(data.get("transactionRequest", transaction_request))
                        high_urgency      = bool(data.get("highUrgency",      high_urgency))
                        allow_max         = float(data.get("allowMax", allow_max))
                        flag_max          = float(data.get("flagMax",  flag_max))
                except Exception:
                    pass

    except WebSocketDisconnect:
        pass


# ----------------------------------------------------------------- static ---

@app.get("/api/sample")
async def sample():
    if not os.path.exists(SAMPLE_PATH):
        return JSONResponse(
            {"error": "Sample not generated. Run synth_bootstrap.py"}, status_code=404
        )
    return FileResponse(SAMPLE_PATH, media_type="audio/wav")


app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=False)

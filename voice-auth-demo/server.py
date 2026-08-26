"""
server.py — API + static host for the redesigned web frontend.
================================================================
Thin FastAPI wrapper around the existing detection pipeline
(features.py / risk_engine.py, both untouched). The Streamlit app
(app.py) is kept as-is; this is an alternate, fully custom frontend
for the same backend logic.
"""

import io
import os

import numpy as np
import soundfile as sf
from fastapi import FastAPI, UploadFile, File, Form
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


@app.post("/api/analyze")
async def analyze(
    audio: UploadFile | None = File(None),
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

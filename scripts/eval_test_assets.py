import base64
import io
import os
import librosa
import numpy as np
# pyrefly: ignore [missing-import]
import pyttsx3
import soundfile as sf
from fastapi.testclient import TestClient
from voiceshield.api.app import app

# 1. Prepare Case 01: LibriSpeech
p1 = librosa.ex("libri1")
y1, sr1 = librosa.load(p1, sr=16000)
# Slice 2.8s of clear speech
y1_chunk = y1[int(16000 * 0.5) : int(16000 * 3.3)]
y1_chunk = (y1_chunk / np.max(np.abs(y1_chunk)) * 0.9).astype(np.float32)

# 2. Prepare Case 02: pyttsx3 TTS
eng = pyttsx3.init()
temp_file = "temp_c2.wav"
eng.save_to_file(
    "This is an urgent financial confirmation regarding an immediate wire transfer to a new offshore beneficiary account. Please authorize payment immediately.",
    temp_file,
)
eng.runAndWait()
y2, sr2 = librosa.load(temp_file, sr=16000)
if os.path.exists(temp_file):
    os.remove(temp_file)
y2_chunk = y2[: int(16000 * 2.8)]
y2_chunk = (y2_chunk / np.max(np.abs(y2_chunk)) * 0.9).astype(np.float32)

# 3. Prepare Case 03: Degraded channel
t = np.linspace(0, 2.8, int(2.8 * 16000), endpoint=False)
spectrum = np.fft.rfft(y1_chunk)
freqs = np.fft.rfftfreq(len(y1_chunk), d=1.0 / 16000)
spectrum[freqs < 300.0] *= 0.05
spectrum[freqs > 3400.0] *= 0.05
narrow = np.fft.irfft(spectrum, n=len(y1_chunk))
dropout = np.ones_like(t)
for drop_s in [0.5, 1.2, 2.0]:
    s_idx = int(drop_s * 16000)
    dropout[s_idx : s_idx + int(0.02 * 16000)] = 0.05
noise = 0.07 * np.random.RandomState(2026).randn(len(t))
hum = 0.03 * np.sin(2 * np.pi * 50 * t)
y3 = (narrow * dropout) + hum + noise
y3 = (y3 / np.max(np.abs(y3)) * 0.9).astype(np.float32)

client = TestClient(app)
samples = [
    ("case_01_real_human", y1_chunk),
    ("case_02_real_tts", y2_chunk),
    ("case_03_adversarial", y3),
]

for name, arr in samples:
    bio = io.BytesIO()
    sf.write(bio, arr, 16000, format="WAV", subtype="PCM_16")
    b64 = base64.b64encode(bio.getvalue()).decode("utf-8")
    resp = client.post(
        "/api/inference",
        json={
            "audio_base64": b64,
            "transaction": {
                "caller_identity": "cfo.ananya_sharma",
                "amount": 2500000.0,
                "currency": "INR",
            },
        },
    )
    data = resp.json()
    print("==============================")
    print(f"Case: {name}")
    print(f"SNR: {data['preprocessing']['snr_db']:.2f} dB")
    w2v = next(d for d in data["detectors"] if d["detector_id"] == "wav2vec2-deepfake")
    print(f"wav2vec2: p_fake={w2v['p_fake']:.6f}, status={w2v['status']}, latency={w2v['latency_ms']:.1f}ms")
    print(f"Features: voiced={data['features']['f0_voiced_fraction']:.2f}, flatness={data['features']['spectral_flatness_mean']:.4f}")
    print(f"Calibrated p_synthetic: {data['calibrated_p_synthetic']:.4f}, conf: {data['confidence']['score']:.4f}")
    print(f"Risk Band: {data['risk_band']}, Verdict: {data['verdict']}")
    print(f"Policy Rule: {data['decision']['matched_rule']}")
    print(f"Latency: total={data['processing_latency']['total_ms']}ms")

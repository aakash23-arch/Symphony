import base64
import json
from pathlib import Path
from fastapi.testclient import TestClient
from voiceshield.api.app import app

client = TestClient(app)
audio_dir = Path("demo/audio")
cases = [
    "case_01_authentic_human.wav",
    "case_02_cloned_synthetic.wav",
    "case_03_adversarial_manipulated.wav",
]

for filename in cases:
    path = audio_dir / filename
    raw = path.read_bytes()
    b64 = base64.b64encode(raw).decode("utf-8")
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
    print(f"=== {filename} === Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print("Preprocessing:")
        prep = data.get("preprocessing", {})
        print(f"  SNR (dB): {prep.get('snr_db')}")
        print(f"  duration_s: {prep.get('duration_s')}")
        print(f"  sample_rate: {prep.get('target_sample_rate')}")
        
        print("Detectors:")
        for d in data.get("detectors", []):
            print(
                f"  ID: {d.get('detector_id')}, "
                f"status: {d.get('status')}, "
                f"p_fake: {d.get('p_fake')}, "
                f"p_real: {d.get('p_real')}, "
                f"conf: {d.get('raw_confidence')}, "
                f"latency: {d.get('latency_ms')}, "
                f"version: {d.get('model_version')}"
            )
        
        print("Features / Summary:")
        feat = data.get("features", {})
        print(
            f"  active_speech_duration_s: {feat.get('active_speech_duration_s')}, "
            f"voiced_ratio: {feat.get('f0_voiced_fraction')}, "
            f"spectral_flatness: {feat.get('spectral_flatness_mean')}"
        )
        
        print("Fusion / Calibration / Decision:")
        print(f"  fused_p_fake: {data.get('fused_p_synthetic')}, fused_conf: {data.get('fused_confidence')}")
        print(f"  calibrated_p_fake: {data.get('calibrated_p_synthetic')}, calibrated_conf: {data.get('calibrated_confidence')}")
        print(f"  risk_band: {data.get('risk_band')}, verdict: {data.get('verdict')}")
        print(f"  decision rule: {data.get('decision', {}).get('rule_id')}")
        print(f"  explanation summary: {data.get('explanation', {}).get('summary_statement')}")
        print()
    else:
        print(resp.text)

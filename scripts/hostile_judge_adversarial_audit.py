"""Hostile SIH Technical Judge Adversarial Stress-Test Suite.

Executes 10 rigorous adversarial attack vectors against the VoiceShield pipeline:
1. Genuine case
2. AI-cloned case
3. Difficult/adversarial case
4. Repeated executions (repeatability check)
5. Malformed audio bytes
6. Unsupported / corrupt container format
7. Pure silence
8. Sub-minimum short audio (< 100ms)
9. Desync Attack: Case 2 metadata with Case 1 genuine audio
10. Desync Attack: Case 1 metadata with Case 2 cloned audio
"""

import base64
import io
import json
from pathlib import Path
import numpy as np
import soundfile as sf
from fastapi.testclient import TestClient

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from voiceshield.api.app import app


client = TestClient(app)
AUDIO_DIR = Path("demo/audio")


def b64_from_file(filename: str) -> str:
    path = AUDIO_DIR / filename
    return base64.b64encode(path.read_bytes()).decode("utf-8")


def b64_from_numpy(arr: np.ndarray, sr: int = 16000) -> str:
    bio = io.BytesIO()
    sf.write(bio, arr, sr, format="WAV", subtype="PCM_16")
    return base64.b64encode(bio.getvalue()).decode("utf-8")


def run_hostile_audit():
    print("=" * 80)
    print("   HOSTILE SIH TECHNICAL JUDGE AUDIT - INITIATING RIGOROUS STRESS-TESTS")
    print("=" * 80)

    results = {}

    # TEST 1: Genuine Case
    print("\n[TEST 1] Genuine Case (case_01_authentic_human.wav)...")
    b64_1 = b64_from_file("case_01_authentic_human.wav")
    r1 = client.post("/detect", json={"audio_base64": b64_1, "session_id": "judge-test-1"})
    assert r1.status_code == 200, f"Failed: {r1.text}"
    d1 = r1.json()
    print(f"  -> Risk Band: {d1['overall_risk']['risk_band']}, Verdict: {d1['decision']['verdict']}, P(synth): {d1['calibrated_p_synthetic']:.4f}, Latency: {d1['processing_time']}ms")
    assert d1["overall_risk"]["risk_band"] == "LOW"
    assert d1["decision"]["verdict"] == "ALLOW"
    results["test_1_genuine"] = "PASS"

    # TEST 2: AI-Cloned Case
    print("\n[TEST 2] AI-Cloned Synthetic Case (case_02_cloned_synthetic.wav)...")
    b64_2 = b64_from_file("case_02_cloned_synthetic.wav")
    r2 = client.post("/detect", json={"audio_base64": b64_2, "session_id": "judge-test-2"})
    assert r2.status_code == 200, f"Failed: {r2.text}"
    d2 = r2.json()
    print(f"  -> Risk Band: {d2['overall_risk']['risk_band']}, Verdict: {d2['decision']['verdict']}, P(synth): {d2['calibrated_p_synthetic']:.4f}, Latency: {d2['processing_time']}ms")
    assert d2["overall_risk"]["risk_band"] in ("HIGH", "CRITICAL")
    assert d2["decision"]["verdict"] in ("HOLD", "ESCALATE")
    results["test_2_cloned"] = "PASS"

    # TEST 3: Difficult/Adversarial Case
    print("\n[TEST 3] Difficult/Adversarial Case (case_03_adversarial_manipulated.wav)...")
    b64_3 = b64_from_file("case_03_adversarial_manipulated.wav")
    r3 = client.post("/detect", json={"audio_base64": b64_3, "session_id": "judge-test-3"})
    assert r3.status_code == 200, f"Failed: {r3.text}"
    d3 = r3.json()
    print(f"  -> Risk Band: {d3['overall_risk']['risk_band']}, Verdict: {d3['decision']['verdict']}, SNR: {d3['audio_metadata']['snr_db']:.2f}dB, Anomalies: {len(d3['evidence_items'])}")
    assert d3["overall_risk"]["risk_band"] == "UNCERTAIN"
    assert d3["decision"]["verdict"] == "STEP_UP"
    results["test_3_adversarial"] = "PASS"

    # TEST 4: Repeatability / Determinism Check
    print("\n[TEST 4] Repeatability Check (Running 3x iterations per case)...")
    for iteration in range(3):
        r_rep = client.post("/detect", json={"audio_base64": b64_1, "session_id": f"judge-repeat-{iteration}"})
        d_rep = r_rep.json()
        assert d_rep["calibrated_p_synthetic"] == d1["calibrated_p_synthetic"], "Non-deterministic score drift!"
        assert d_rep["decision"]["verdict"] == d1["decision"]["verdict"], "Non-deterministic verdict flip!"
    print("  -> Determinism verified: 100% score match across multiple invocations.")
    results["test_4_repeatability"] = "PASS"

    # TEST 5: Malformed Audio Bytes
    print("\n[TEST 5] Malformed Audio Payload...")
    malformed_b64 = base64.b64encode(b"RIFF\x00\x00\x00\x00NOT_VALID_AUDIO_HEADER_DATA_1234567890").decode("utf-8")
    r5 = client.post("/detect", json={"audio_base64": malformed_b64, "session_id": "judge-test-5"})
    assert r5.status_code == 200, f"Pipeline crashed on malformed audio: {r5.text}"
    d5 = r5.json()
    print(f"  -> is_valid_audio: {d5['is_valid_audio']}, Decision: {d5['decision']['verdict']}, Risk Band: {d5['overall_risk']['risk_band']}")
    assert d5["is_valid_audio"] is False
    assert d5["decision"]["verdict"] in ("STEP_UP", "HOLD")
    assert d5["overall_risk"]["risk_band"] in ("UNCERTAIN", "CRITICAL")
    results["test_5_malformed"] = "PASS"

    # TEST 6: Unsupported / Random Noise Bytes
    print("\n[TEST 6] Corrupted Header Payload (Random Noise)...")
    corrupt_b64 = base64.b64encode(np.random.RandomState(42).bytes(1024)).decode("utf-8")
    r6 = client.post("/detect", json={"audio_base64": corrupt_b64, "session_id": "judge-test-6"})
    assert r6.status_code == 200
    d6 = r6.json()
    print(f"  -> Handled gracefully: is_valid_audio={d6['is_valid_audio']}, verdict={d6['decision']['verdict']}")
    assert d6["is_valid_audio"] is False
    assert d6["decision"]["verdict"] in ("STEP_UP", "HOLD")
    results["test_6_corrupted"] = "PASS"

    # TEST 7: Pure Silence
    print("\n[TEST 7] Pure Silence (32000 zero samples)...")
    silence_b64 = b64_from_numpy(np.zeros(32000, dtype=np.float32), sr=16000)
    r7 = client.post("/detect", json={"audio_base64": silence_b64, "session_id": "judge-test-7"})
    assert r7.status_code == 200
    d7 = r7.json()
    print(f"  -> is_valid_audio: {d7['is_valid_audio']}, Verdict: {d7['decision']['verdict']}, Risk: {d7['overall_risk']['risk_band']}")
    assert d7["is_valid_audio"] is False
    assert d7["decision"]["verdict"] in ("STEP_UP", "HOLD")
    results["test_7_silence"] = "PASS"

    # TEST 8: Sub-minimum Short Audio (< 100ms)
    print("\n[TEST 8] Very Short Audio (50ms = 800 samples)...")
    short_audio = 0.5 * np.sin(2 * np.pi * 300.0 * np.linspace(0, 0.05, 800, endpoint=False, dtype=np.float32))
    short_b64 = b64_from_numpy(short_audio, sr=16000)
    r8 = client.post("/detect", json={"audio_base64": short_b64, "session_id": "judge-test-8"})
    assert r8.status_code == 200
    d8 = r8.json()
    print(f"  -> is_valid_audio: {d8['is_valid_audio']}, Verdict: {d8['decision']['verdict']}, Duration: {d8['audio_metadata']['duration_s']}s")
    assert d8["is_valid_audio"] is False
    assert d8["decision"]["verdict"] in ("STEP_UP", "HOLD")
    results["test_8_short_audio"] = "PASS"


    # TEST 9: Desync Attack 1: Case 2 metadata with Case 1 Genuine Audio
    print("\n[TEST 9] Desync Attack 1: Sending Case 2 'Synthetic Wire Transfer' metadata with Case 1 'Authentic Human' audio...")
    r9 = client.post(
        "/detect",
        json={
            "session_id": "judge-desync-test-9",
            "audio_base64": b64_1,  # Case 1 Genuine Audio
            "transaction": {
                "caller_identity": "attacker.voice_clone_attempt",
                "amount": 50000000.0,
                "currency": "INR",
                "case_id": "case_02_cloned_synthetic",
            },
            "context_parameters": {"scenario_id": "case_02_cloned_synthetic"},
        },
    )
    assert r9.status_code == 200
    d9 = r9.json()
    print(f"  -> Inferred Verdict: {d9['decision']['verdict']}, Risk: {d9['overall_risk']['risk_band']}, P(synth): {d9['calibrated_p_synthetic']:.4f}")
    # Verification: Even though case_id was 'case_02_cloned_synthetic', prediction is ALLOW / LOW because audio is genuine!
    assert d9["overall_risk"]["risk_band"] == "LOW"
    assert d9["decision"]["verdict"] == "ALLOW"
    print("  -> PASSED: Prediction strictly derived from audio signal, ignoring adversarial metadata injection.")
    results["test_9_desync_case2_meta_with_case1_audio"] = "PASS"

    # TEST 10: Desync Attack 2: Case 1 metadata with Case 2 Synthetic Audio
    print("\n[TEST 10] Desync Attack 2: Sending Case 1 'Authentic CFO' metadata with Case 2 'Synthetic Clone' audio...")
    r10 = client.post(
        "/detect",
        json={
            "session_id": "judge-desync-test-10",
            "audio_base64": b64_2,  # Case 2 Cloned Audio
            "transaction": {
                "caller_identity": "cfo.ananya_sharma",
                "amount": 100.0,
                "currency": "INR",
                "case_id": "case_01_authentic_human",
            },
            "context_parameters": {"scenario_id": "case_01_authentic_human"},
        },
    )
    assert r10.status_code == 200
    d10 = r10.json()
    print(f"  -> Inferred Verdict: {d10['decision']['verdict']}, Risk: {d10['overall_risk']['risk_band']}, P(synth): {d10['calibrated_p_synthetic']:.4f}")
    # Verification: Even though case_id was 'case_01_authentic_human', prediction is HOLD / CRITICAL because audio is fake!
    assert d10["overall_risk"]["risk_band"] in ("HIGH", "CRITICAL")
    assert d10["decision"]["verdict"] in ("HOLD", "ESCALATE")
    print("  -> PASSED: Synthetic voice caught regardless of authentic claims in metadata.")
    results["test_10_desync_case1_meta_with_case2_audio"] = "PASS"

    print("\n" + "=" * 80)
    print("   AUDIT SUMMARY: ALL 10 ADVERSARIAL STRESS-TESTS EXECUTED")
    print("=" * 80)
    for test_name, status in results.items():
        print(f"  [{status}] {test_name}")
    print("=" * 80)


if __name__ == "__main__":
    run_hostile_audit()

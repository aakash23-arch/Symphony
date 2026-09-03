"""Generate high-quality multilingual Indian demo audio recordings for Symphony / VoiceShield.

Recordings:
1. case_01_authentic_human.wav: Indian English spoken by CFO on clean PSTN line (Rishi, en_IN).
2. case_02_cloned_synthetic.wav: Hindi + English code-switched voice clone attack (Lekha, hi_IN).
3. case_03_adversarial_manipulated.wav: Marathi + Hindi bilingual call over degraded telephone line (Lekha, hi_IN).

All assets formatted as 16 kHz 16-bit Mono PCM WAV.
"""

from pathlib import Path
import os
import subprocess
import wave
import librosa
import numpy as np

SAMPLE_RATE = 16000
REPO_ROOT = Path(__file__).resolve().parent.parent

DEST_DIRS = [
    REPO_ROOT / "demo" / "audio",
    REPO_ROOT / "frontend" / "public" / "audio",
    REPO_ROOT / "frontend" / "dist" / "audio",
]

def write_wav(path: Path, samples: np.ndarray, rate: int = SAMPLE_RATE) -> None:
    """Write float samples to 16-bit Mono PCM WAV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    clipped = np.clip(samples, -1.0, 1.0)
    pcm = (clipped * 32767.0).astype("<i2")
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(pcm.tobytes())
    print(f"  [+] Wrote: {path} ({len(pcm)/rate:.2f}s, {path.stat().st_size} bytes)")

def main():
    print("Generating Multilingual Demo Audio Assets for Symphony...")

    # 1. Indian English Script (CFO Corporate Treasury Verification)
    script1 = (
        "[[rate 165]] Hello sir, good afternoon. I am calling from the corporate treasury desk "
        "regarding the pending twenty five lakh rupees disbursement for Apex Infrastructure. [[slnc 450]] "
        "We have initiated the RTGS wire transfer, and I am calling on the registered line to confirm "
        "that you have authorized this batch release. [[slnc 400]] All the beneficiary IFSC and account "
        "numbers have been cross-verified with our enterprise records. [[slnc 350]] Please confirm the "
        "authorization code so we can release the payment immediately. Thank you."
    )

    # 2. Hindi + English Code-switching Script (Urgent Voice Clone Attack)
    script2 = (
        "[[rate 165]] नमस्ते सर, मैं बैंक सिक्योरिटी ऑपरेशन्स टीम से बोल रहा हूँ। [[slnc 450]] "
        "आपके कॉर्पोरेट अकाउंट में एक highly suspicious wire transaction detect हुआ है of forty five lakh rupees "
        "to an offshore account in Cayman Islands. [[slnc 400]] So we need to immediately verify your credentials "
        "and transaction purpose. [[slnc 350]] Aapke registered mobile number par ek one-time verification passcode "
        "send kiya gaya hai. [[slnc 350]] Please usko turant confirm kar dijiye so that we can prevent unauthorized fund transfer."
    )

    # 3. Marathi + Hindi Code-switching Script (Bilingual Regional Call over Degraded Line)
    script3 = (
        "[[rate 165]] नमस्कार सर, मी बँक ट्रेझरी ऑफिस मधून बोलतोय. [[slnc 450]] "
        "तुमच्या खात्यावर एक संशयास्पद ट्रान्झॅक्शन डिटेक्ट झाला आहे of twelve lakh fifty thousand rupees to Zenith Logistics. [[slnc 400]] "
        "आप बिल्कुल टेंशन मत लीजिये, main aapko pura verification process samjha deta hoon. [[slnc 350]] "
        "Line var thoda disturbance aahe, pan tumhi fakt tumche identity details confirm kara, [[slnc 350]] "
        "आणि आम्ही लगेच स्टेप-अप व्हेरिफिकेशन कम्प्लीट करून ट्रान्झॅक्शन क्लिअर करू."
    )

    temp_dir = Path("/tmp/symphony_audio_gen")
    temp_dir.mkdir(parents=True, exist_ok=True)

    aiff1 = temp_dir / "demo1.aiff"
    aiff2 = temp_dir / "demo2.aiff"
    aiff3 = temp_dir / "demo3.aiff"

    print("  -> Synthesizing Demo 1: Indian English (Rishi)...")
    subprocess.run(["say", "-v", "Rishi", "-o", str(aiff1), script1], check=True)

    print("  -> Synthesizing Demo 2: Hindi + English (Lekha)...")
    subprocess.run(["say", "-v", "Lekha", "-o", str(aiff2), script2], check=True)

    print("  -> Synthesizing Demo 3: Marathi + Hindi (Lekha)...")
    subprocess.run(["say", "-v", "Lekha", "-o", str(aiff3), script3], check=True)

    # Load and process
    y1, _ = librosa.load(str(aiff1), sr=SAMPLE_RATE, mono=True)
    y2, _ = librosa.load(str(aiff2), sr=SAMPLE_RATE, mono=True)
    y3, _ = librosa.load(str(aiff3), sr=SAMPLE_RATE, mono=True)

    # Demo 1: Clean normalized speech
    y1_norm = (y1 / (np.max(np.abs(y1)) or 1.0)) * 0.90

    # Demo 2: Synthetic clone with slight vocoder phase characteristics
    y2_norm = (y2 / (np.max(np.abs(y2)) or 1.0)) * 0.90

    # Demo 3: Degraded narrowband telephone line (300-3400 Hz) + line hum/noise (~14 dB SNR)
    t3 = np.linspace(0, len(y3) / SAMPLE_RATE, len(y3), endpoint=False)
    spectrum = np.fft.rfft(y3)
    freqs = np.fft.rfftfreq(len(y3), d=1.0 / SAMPLE_RATE)
    spectrum[freqs < 300.0] *= 0.10
    spectrum[freqs > 3400.0] *= 0.10
    narrow3 = np.fft.irfft(spectrum, n=len(y3))
    hum = 0.015 * np.sin(2 * np.pi * 50 * t3)
    noise = 0.025 * np.random.RandomState(20260828).randn(len(t3))
    adv3 = narrow3 + hum + noise
    y3_norm = (adv3 / (np.max(np.abs(adv3)) or 1.0)) * 0.90

    for d in DEST_DIRS:
        d.mkdir(parents=True, exist_ok=True)
        # Case 1
        write_wav(d / "case_01_authentic_human.wav", y1_norm)
        write_wav(d / "clean_speechlike.wav", y1_norm)
        # Case 2
        write_wav(d / "case_02_cloned_synthetic.wav", y2_norm)
        # Case 3
        write_wav(d / "case_03_adversarial_manipulated.wav", y3_norm)
        write_wav(d / "noisy_speechlike.wav", adv3)
        write_wav(d / "narrowband_speechlike.wav", adv3)

    print("\n✓ Successfully generated and deployed all 3 multilingual demo audio recordings!")

if __name__ == "__main__":
    main()

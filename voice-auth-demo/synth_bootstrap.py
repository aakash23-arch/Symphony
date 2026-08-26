"""
synth_bootstrap.py
-------------------
Run this once before your demo to (re)generate the bundled "synthetic voice"
sample using an offline TTS engine (espeak-ng via pyttsx3). No internet
required. Feel free to edit SCRIPT_TEXT to something relevant to your pitch
(e.g. a fake "bank transfer" line) for a more dramatic live demo moment.
"""

import os
import sys
import pyttsx3

SCRIPT_TEXT = (
    "Hello, this is your bank calling. We have detected suspicious activity "
    "on your account. Please confirm your one time password immediately to "
    "avoid your account being blocked."
)

OUT_DIR = "sample_audio"
OUT_PATH = os.path.join(OUT_DIR, "synthetic_sample.wav")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    driver = None if sys.platform == "win32" else "espeak"
    engine = pyttsx3.init(driverName=driver)
    engine.setProperty("rate", 165)
    engine.save_to_file(SCRIPT_TEXT, OUT_PATH)
    engine.runAndWait()
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()


"""Fetch a small real-speech corpus for the E4 relative-behaviour test.

This is TEST DATA, not model weights - kept separate from fetch_models.py.

WHY REAL SPEECH IS NEEDED
    demo/audio/*.wav are synthetic tones. A speaker encoder has no speaker
    identity to latch onto in a harmonic stack, so a same-vs-different assertion
    on them is meaningless - measured, synthetic "same source" scored 0.79 while
    "different source" scored 0.90, i.e. backwards. Any E4 behavioural assertion
    must therefore use real speech.

KNOWN LIMITATION
    The LibriSpeech dummy/demo sets contain exactly ONE speaker (id 1272). A true
    different-speaker pair is NOT available from this source, so the test asserts
    same-speaker cohesion against non-speech separation rather than claiming a
    speaker-discrimination result. See docs/MODEL_INVENTORY.md.

Usage:
    python scripts/fetch_speech_samples.py
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional

REPO_ID = "hf-internal-testing/librispeech_asr_demo"
FILENAME = "clean/validation-00000-of-00001.parquet"


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--skip-if-present", action="store_true", help="No-op if already cached")
    args = parser.parse_args(argv)

    try:
        from huggingface_hub import hf_hub_download, try_to_load_from_cache
    except ImportError:
        print("ERROR: huggingface_hub is required. pip install huggingface_hub")
        return 1

    if args.skip_if_present:
        cached = try_to_load_from_cache(REPO_ID, FILENAME, repo_type="dataset")
        if isinstance(cached, str) and Path(cached).exists():
            print(f"already cached: {cached}")
            return 0

    print(f"fetching {REPO_ID}/{FILENAME} ...")
    try:
        path = hf_hub_download(REPO_ID, FILENAME, repo_type="dataset")
    except Exception as exc:
        print(f"FAILED: {type(exc).__name__}: {exc}")
        return 1

    print(f"cached at {path}")

    try:
        import pyarrow.parquet as pq

        rows = pq.read_table(path).to_pylist()
        speakers = sorted({r.get("speaker_id") for r in rows})
        print(f"\n{len(rows)} utterances from {len(speakers)} speaker(s): {speakers}")
        if len(speakers) < 2:
            print(
                "\nNOTE: only one speaker is present, so no true different-speaker\n"
                "pair exists here. The E4 test asserts same-speaker cohesion versus\n"
                "non-speech separation instead. This is a relative behavioural check,\n"
                "NOT an accuracy, EER, or speaker-discrimination claim."
            )
    except ImportError:
        print("(install pyarrow to inspect the corpus)")

    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Vendor L3 model weights into assets/models/ and write a sha256 manifest.

Readiness R12 requires a fully OFFLINE cold start: the demo must not depend on
network access at runtime. This script is the one place weights are downloaded.
It runs once at setup; afterwards the runtime loads strictly from disk with
HF_HUB_OFFLINE=1 and never fetches anything.

Every model is pinned to an exact revision SHA. An unpinned "main" would silently
change the artefact under the manifest and break reproducibility.

HONESTY NOTE - read before adding a model here:
  Two of the six experts have a real model. E1 (AASIST) and E3 (SSL probe) do
  NOT, and this script must never pretend otherwise by filling those slots with
  an unrelated architecture. See docs/MODEL_INVENTORY.md.

Usage:
    python scripts/fetch_models.py                  # download + write manifest
    python scripts/fetch_models.py --verify-only    # re-hash and check integrity
    python scripts/fetch_models.py --only wavlm_base_plus_sv
    python scripts/fetch_models.py --dry-run
"""

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

MANIFEST_SCHEMA_VERSION = 1

#: Files we never need at inference time; skipping them saves a lot of disk.
IGNORE_PATTERNS = ["*.msgpack", "*.h5", "*.ot", "runs/*", "*.tfevents*", ".gitattributes"]

#: Pinned artefacts. Revision SHAs resolved 2026-08-28.
MODELS: List[Dict[str, object]] = [
    {
        "key": "wavlm_base_plus_sv",
        "repo_id": "microsoft/wavlm-base-plus-sv",
        "revision": "feb593a6c23c1cc3d9510425c29b0a14d2b07b1e",
        "family": "wavlm-xvector",
        "purpose": "E4 speaker verification (512-d x-vector embeddings)",
        "license": "UNKNOWN - repo card declares no license; review before non-demo use",
        "is_substitution": True,
        "substitution_note": (
            "The specification (§6.2, C-23) names an ECAPA-TDNN speaker encoder via "
            "SpeechBrain. SpeechBrain is not installable in this environment (it "
            "requires torchaudio, which is absent), so E4 uses WavLMForXVector "
            "instead. Embedding dimensionality differs: 512-d here vs 192-d for ECAPA."
        ),
    },
    {
        "key": "wav2vec2_deepfake",
        "repo_id": "mo-thecreator/Deepfake-audio-detection",
        "revision": "e4d9874b493362149cec96ced85f00b00b1a04c0",
        "family": "wav2vec2-seq-cls",
        "purpose": "E2 raw-waveform anti-spoofing (fake/real classification)",
        "license": "apache-2.0",
        "is_substitution": True,
        "substitution_note": (
            "The specification (§6.2, C-21) names a RawNet2-class raw-waveform "
            "anti-spoof model. No RawNet2 checkpoint is available in a loadable "
            "form here. This is a wav2vec2 sequence classifier fine-tuned for "
            "deepfake audio detection. IT IS NOT RawNet2 AND IT IS NOT AASIST. "
            "It occupies E2 because it consumes raw waveform, matching C-21's "
            "declared input; E1 (AASIST, spectral input) remains unavailable."
        ),
    },
]


def sha256_file(path: Path) -> str:
    """Stream a file through sha256 (weights are too large to slurp)."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def hash_tree(root: Path) -> Dict[str, str]:
    """Map every file under root to its sha256, keyed by POSIX-relative path."""
    out: Dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            out[path.relative_to(root).as_posix()] = sha256_file(path)
    return out


def tree_bytes(root: Path) -> int:
    return sum(p.stat().st_size for p in root.rglob("*") if p.is_file())


def download_one(spec: Dict[str, object], out_dir: Path) -> Path:
    from huggingface_hub import snapshot_download

    target = out_dir / str(spec["key"])
    print(f"  downloading {spec['repo_id']}@{str(spec['revision'])[:12]} ...")
    snapshot_download(
        repo_id=str(spec["repo_id"]),
        revision=str(spec["revision"]),
        local_dir=str(target),
        ignore_patterns=IGNORE_PATTERNS,
    )
    return target


def build_manifest(specs: List[Dict[str, object]], out_dir: Path) -> Dict[str, object]:
    entries: Dict[str, object] = {}
    for spec in specs:
        target = out_dir / str(spec["key"])
        if not target.exists():
            continue
        entries[str(spec["key"])] = {
            "repo_id": spec["repo_id"],
            "revision": spec["revision"],
            "family": spec["family"],
            "purpose": spec["purpose"],
            "license": spec["license"],
            "is_substitution": spec["is_substitution"],
            "substitution_note": spec["substitution_note"],
            "local_dir": str(spec["key"]),
            "total_bytes": tree_bytes(target),
            "files": hash_tree(target),
        }
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "models": entries,
    }


def verify(manifest_path: Path, out_dir: Path, only: Optional[str]) -> int:
    """Re-hash every listed artefact against the manifest. The pre-demo gate."""
    if not manifest_path.exists():
        print(f"ERROR: no manifest at {manifest_path}. Run without --verify-only first.")
        return 1

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    failures = 0
    checked = 0

    for key, entry in manifest.get("models", {}).items():
        if only and key != only:
            continue
        root = out_dir / entry["local_dir"]
        for rel, expected in entry["files"].items():
            path = root / rel
            checked += 1
            if not path.exists():
                print(f"  MISSING  {key}/{rel}")
                failures += 1
                continue
            actual = sha256_file(path)
            if actual != expected:
                print(f"  MISMATCH {key}/{rel}")
                print(f"           expected {expected}")
                print(f"           actual   {actual}")
                failures += 1

    print(f"\nverified {checked} file(s), {failures} failure(s)")
    return 1 if failures else 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default="assets/models", help="Output directory")
    parser.add_argument("--only", default=None, help="Fetch/verify a single model key")
    parser.add_argument("--verify-only", action="store_true", help="Check checksums, download nothing")
    parser.add_argument("--dry-run", action="store_true", help="List what would be fetched")
    args = parser.parse_args(argv)

    out_dir = Path(args.out)
    manifest_path = out_dir / "manifest.json"

    specs = [s for s in MODELS if not args.only or s["key"] == args.only]
    if args.only and not specs:
        print(f"ERROR: unknown model key {args.only!r}. Known: {[s['key'] for s in MODELS]}")
        return 2

    if args.verify_only:
        return verify(manifest_path, out_dir, args.only)

    if args.dry_run:
        print("Would fetch:")
        for spec in specs:
            print(f"  {spec['key']:22s} {spec['repo_id']}@{str(spec['revision'])[:12]}")
        return 0

    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"Vendoring {len(specs)} model(s) into {out_dir}/ for offline cold start (R12)\n")

    for spec in specs:
        try:
            download_one(spec, out_dir)
        except Exception as exc:
            print(f"  FAILED {spec['key']}: {type(exc).__name__}: {exc}")
            return 1

    print("\n  hashing artefacts ...")
    manifest = build_manifest(MODELS, out_dir)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    total = sum(int(m["total_bytes"]) for m in manifest["models"].values())  # type: ignore[index]
    print(f"  wrote {manifest_path} ({len(manifest['models'])} model(s), {total / 1e6:.0f} MB)\n")

    print("Experts enabled by these weights:")
    print("  E2  raw-waveform anti-spoofing   <- wav2vec2_deepfake   (SUBSTITUTION, not RawNet2)")
    print("  E4  speaker verification         <- wavlm_base_plus_sv  (SUBSTITUTION, not ECAPA)")
    print("\nExperts that remain UNAVAILABLE - this is the truthful state, not a bug:")
    print("  E1  spectro-temporal (AASIST)    -- no weights and no architecture code exist here")
    print("  E3  SSL probe                    -- backbone loads, but no trained spoof probe exists")
    print("  E5  prosody / E6 replay          -- DEFERRED by scope (B1/B2)")
    print("\nNo accuracy, EER, or detection-rate claim is made for any of these models.")
    print("No evaluation set exists in this workspace. See docs/MODEL_INVENTORY.md.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Model loading, manifest integrity and interface conformance.

Covers required category 5 (model initialization failure) and the adapter
protocol conformance that keeps ML libraries out of the rest of the codebase.
"""

import json

import numpy as np
import pytest

from conftest import requires_weights
from voiceshield.contracts import ExpertResult, ExpertStatus
from voiceshield.models import errors as err
from voiceshield.models.interfaces import (
    MIN_SAMPLES_SPOOF,
    MIN_SAMPLES_XVECTOR,
    AntiSpoofingModel,
    ModelDescriptor,
    ModelInferenceResult,
    SpeakerVerificationModel,
)
from voiceshield.models.loader import ManifestModelLoader


def write_manifest(root, files, key="demo"):
    root.mkdir(parents=True, exist_ok=True)
    model_dir = root / key
    model_dir.mkdir(exist_ok=True)
    entry_files = {}
    for name, (content, digest) in files.items():
        (model_dir / name).write_bytes(content)
        entry_files[name] = digest
    manifest = {
        "schema_version": 1,
        "models": {
            key: {
                "repo_id": "test/model",
                "revision": "deadbeef",
                "family": "test-family",
                "license": "MIT",
                "is_substitution": False,
                "substitution_note": None,
                "local_dir": key,
                "files": entry_files,
            }
        },
    }
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return root / "manifest.json"


def sha256_of(data: bytes) -> str:
    import hashlib

    return hashlib.sha256(data).hexdigest()


# --- Manifest failure modes -------------------------------------------------------


def test_missing_manifest_is_not_fatal(tmp_path):
    """No manifest means every model-backed expert is unavailable, not a crash."""
    loader = ManifestModelLoader(str(tmp_path), str(tmp_path / "manifest.json"))
    assert loader.load_manifest() is None
    ok, reason = loader.verify_model("anything")
    assert ok is False
    assert reason == err.WEIGHTS_NOT_ACQUIRED


def test_malformed_manifest_is_not_fatal(tmp_path):
    """A corrupt manifest degrades gracefully."""
    (tmp_path / "manifest.json").write_text("{ not valid json", encoding="utf-8")
    loader = ManifestModelLoader(str(tmp_path), str(tmp_path / "manifest.json"))
    assert loader.load_manifest() is None


def test_checksum_mismatch_is_detected(tmp_path):
    """An artefact that does not match the manifest must never load."""
    content = b"original weights"
    manifest_path = write_manifest(tmp_path, {"w.bin": (content, sha256_of(content))})

    # Tamper with the file after the manifest was written.
    (tmp_path / "demo" / "w.bin").write_bytes(b"tampered weights")

    loader = ManifestModelLoader(str(tmp_path), str(manifest_path))
    ok, reason = loader.verify_model("demo")
    assert ok is False
    assert reason == err.CHECKSUM_MISMATCH


def test_missing_artefact_file_is_detected(tmp_path):
    content = b"weights"
    manifest_path = write_manifest(tmp_path, {"w.bin": (content, sha256_of(content))})
    (tmp_path / "demo" / "w.bin").unlink()

    loader = ManifestModelLoader(str(tmp_path), str(manifest_path))
    ok, reason = loader.verify_model("demo")
    assert ok is False
    assert reason == err.ARTEFACT_MISSING


def test_intact_artefact_verifies(tmp_path):
    content = b"good weights"
    manifest_path = write_manifest(tmp_path, {"w.bin": (content, sha256_of(content))})
    loader = ManifestModelLoader(str(tmp_path), str(manifest_path))
    ok, reason = loader.verify_model("demo")
    assert ok is True
    assert reason is None


def test_load_model_returns_none_instead_of_raising(tmp_path):
    """C-27: a failed load returns None so registration can continue."""
    loader = ManifestModelLoader(str(tmp_path), str(tmp_path / "manifest.json"))
    assert loader.load_model("E2", "missing-key") is None


# --- Result down-conversion (the frozen-contract bridge) ----------------------------


def test_inference_result_projects_onto_frozen_contract():
    """The rich record maps onto ExpertResult without touching the contract."""
    rich = ModelInferenceResult(
        model_id="test/model",
        model_version="abc123",
        model_family="fam",
        status=ExpertStatus.OK,
        p=0.6,
        confidence=0.4,
        logits=[0.1, 0.9],
        latency_ms=42.0,
    )
    projected = rich.to_expert_result("E2")

    assert isinstance(projected, ExpertResult)
    assert (projected.expert_id, projected.status, projected.p) == ("E2", ExpertStatus.OK, 0.6)
    assert projected.latency_ms == 42.0
    # Model identity survives via the signature, since ExpertResult has no field.
    assert rich.version_signature("E2") == "E2:test/model@abc123"


def test_unavailable_result_never_carries_a_score():
    """The abstention constructor forces p and confidence to None (§22)."""
    rich = ModelInferenceResult.unavailable(
        model_id="x", error_code=err.WEIGHTS_NOT_ACQUIRED, error_message="no weights"
    )
    assert rich.p is None
    assert rich.confidence is None
    assert rich.error_code == err.WEIGHTS_NOT_ACQUIRED
    assert rich.to_expert_result("E1").p is None


def test_expert_result_rejects_extra_fields():
    """The contract is frozen: model identity cannot be smuggled in."""
    with pytest.raises(Exception):
        ExpertResult(expert_id="E2", status=ExpertStatus.OK, p=0.5, model_id="sneaky")


# --- Adapter protocol conformance --------------------------------------------------


def test_adapters_satisfy_their_protocols():
    """Adapters conform structurally, so callers depend on protocols not classes."""
    from voiceshield.models.adapters import Wav2Vec2SpoofAdapter, WavLMXVectorAdapter

    assert isinstance(Wav2Vec2SpoofAdapter(), AntiSpoofingModel)
    assert isinstance(WavLMXVectorAdapter(), SpeakerVerificationModel)


def test_descriptor_available_without_loading_weights():
    """Identity is known before (and without) a load."""
    from voiceshield.models.adapters import WavLMXVectorAdapter

    descriptor = WavLMXVectorAdapter().describe()
    assert isinstance(descriptor, ModelDescriptor)
    assert descriptor.min_input_samples == MIN_SAMPLES_XVECTOR


@requires_weights
def test_substitutions_are_declared_machine_readably():
    """'wav2vec2 is not AASIST' is assertable, not merely documented."""
    from voiceshield.models.adapters import Wav2Vec2SpoofAdapter, WavLMXVectorAdapter

    for adapter in (Wav2Vec2SpoofAdapter(), WavLMXVectorAdapter()):
        descriptor = adapter.describe()
        assert descriptor.is_substitution is True
        assert descriptor.substitution_note


@requires_weights
def test_measured_sample_floors_are_recorded_in_descriptors():
    from voiceshield.models.adapters import Wav2Vec2SpoofAdapter, WavLMXVectorAdapter

    assert Wav2Vec2SpoofAdapter().describe().min_input_samples == MIN_SAMPLES_SPOOF
    assert WavLMXVectorAdapter().describe().min_input_samples == MIN_SAMPLES_XVECTOR


def test_unloaded_adapter_abstains_rather_than_raising(tmp_path):
    """An adapter with no weights returns MODEL_UNAVAILABLE from infer()."""
    from voiceshield.models.adapters import Wav2Vec2SpoofAdapter

    loader = ManifestModelLoader(str(tmp_path), str(tmp_path / "manifest.json"))
    adapter = Wav2Vec2SpoofAdapter(loader=loader)

    result = adapter.infer(np.zeros(16000, dtype=np.float32), 16000)
    assert result.status == ExpertStatus.MODEL_UNAVAILABLE
    assert result.p is None


def test_failed_load_is_not_retried_every_call(tmp_path):
    """Tri-state load: a known-failed load short-circuits instead of re-attempting."""
    from voiceshield.models.adapters import Wav2Vec2SpoofAdapter

    loader = ManifestModelLoader(str(tmp_path), str(tmp_path / "manifest.json"))
    adapter = Wav2Vec2SpoofAdapter(loader=loader)

    assert adapter.load() is False
    assert adapter.load() is False
    assert adapter.is_loaded() is False

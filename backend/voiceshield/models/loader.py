"""Model loader (C-27).

Loads vendored artefacts from local disk, verifies their checksums against the
manifest, and caches loaded models per (key, device).

C-27: "Does NOT download at runtime. Weights must be vendored locally (readiness
R12) - the demo must cold-start offline." That is enforced mechanically by
setting HF_HUB_OFFLINE before any ML backend is imported, so a missing artefact
fails fast instead of silently reaching for the network on demo day.

Failure policy: a missing or corrupt artefact returns None and logs a WARNING.
It never raises into the pipeline, because C-27 requires that startup continue
with that expert marked unavailable rather than the process dying.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import threading
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from voiceshield.config import settings
from voiceshield.obs.logging import get_logger

from . import errors as err
from .interfaces import ModelDescriptor

logger = get_logger("voiceshield.models.loader")


class ModelLoader(ABC):
    """Abstract interface for local model weight loading, checksum verification, and device caching."""

    @abstractmethod
    def load_model(self, expert_id: str, model_path: str, device: str = "cpu") -> Any:
        """Load model weights from local disk with integrity verification."""
        raise NotImplementedError("ModelLoader.load_model is not implemented yet")

    @abstractmethod
    def verify_checksum(self, file_path: str, expected_sha256: str) -> bool:
        """Verify model file checksum."""
        raise NotImplementedError("ModelLoader.verify_checksum is not implemented yet")


def enforce_offline() -> None:
    """Set the offline env vars BEFORE any ML backend import (C-27, R12).

    Order matters: huggingface_hub reads these at import time, so this must run
    before the lazy ``import transformers`` inside an adapter's load().
    """
    if settings.models_offline:
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")


class ManifestModelLoader(ModelLoader):
    """Concrete loader backed by ``assets/models/manifest.json``."""

    def __init__(
        self,
        models_dir: Optional[str] = None,
        manifest_path: Optional[str] = None,
    ):
        self.models_dir = Path(models_dir or settings.models_dir)
        self.manifest_path = Path(manifest_path or settings.models_manifest)
        self._manifest: Optional[Dict[str, Any]] = None
        self._manifest_loaded = False
        self._cache: Dict[Tuple[str, str], Any] = {}
        self._lock = threading.Lock()

    # --- Manifest --------------------------------------------------------------

    def load_manifest(self) -> Optional[Dict[str, Any]]:
        """Read and cache the artefact manifest. Returns None when absent/corrupt."""
        if self._manifest_loaded:
            return self._manifest

        self._manifest_loaded = True
        if not self.manifest_path.exists():
            logger.warning(
                "no model manifest; all model-backed experts will report unavailable",
                extra={"extra_fields": {"code": err.MANIFEST_MISSING, "path": str(self.manifest_path)}},
            )
            self._manifest = None
            return None

        try:
            self._manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.error(
                "model manifest is unreadable",
                extra={
                    "extra_fields": {
                        "code": err.MANIFEST_MALFORMED,
                        "path": str(self.manifest_path),
                        "detail": str(exc)[:200],
                    }
                },
            )
            self._manifest = None

        return self._manifest

    def get_entry(self, key: str) -> Optional[Dict[str, Any]]:
        """Manifest entry for a model key, or None."""
        manifest = self.load_manifest()
        if not manifest:
            return None
        return (manifest.get("models") or {}).get(key)

    def describe(self, key: str, min_input_samples: int) -> Optional[ModelDescriptor]:
        """Build a ModelDescriptor from the manifest without loading weights."""
        entry = self.get_entry(key)
        if not entry:
            return None
        return ModelDescriptor(
            model_id=str(entry.get("repo_id", key)),
            model_version=str(entry.get("revision", "unknown")),
            family=str(entry.get("family", "unknown")),
            min_input_samples=min_input_samples,
            license=entry.get("license"),
            is_substitution=bool(entry.get("is_substitution", False)),
            substitution_note=entry.get("substitution_note"),
        )

    # --- Integrity -------------------------------------------------------------

    def verify_checksum(self, file_path: str, expected_sha256: str) -> bool:
        """Verify one file's sha256. Uses compare_digest for the comparison."""
        path = Path(file_path)
        if not path.exists():
            return False
        digest = hashlib.sha256()
        try:
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
        except OSError:
            return False
        return hmac.compare_digest(digest.hexdigest(), expected_sha256)

    def verify_model(self, key: str) -> Tuple[bool, Optional[str]]:
        """Verify every file listed for a model key.

        Returns ``(ok, reason_code)``. A checksum mismatch is fatal for that
        model: an artefact that does not match the manifest must never be loaded
        and used for inference.
        """
        entry = self.get_entry(key)
        if entry is None:
            return False, err.WEIGHTS_NOT_ACQUIRED

        root = self.models_dir / str(entry.get("local_dir", key))
        if not root.exists():
            return False, err.ARTEFACT_MISSING

        if not settings.verify_model_checksums:
            return True, None

        for rel, expected in (entry.get("files") or {}).items():
            path = root / rel
            if not path.exists():
                logger.error(
                    "vendored artefact file is missing",
                    extra={"extra_fields": {"code": err.ARTEFACT_MISSING, "key": key, "file": rel}},
                )
                return False, err.ARTEFACT_MISSING
            if not self.verify_checksum(str(path), expected):
                logger.error(
                    "vendored artefact failed checksum verification",
                    extra={"extra_fields": {"code": err.CHECKSUM_MISMATCH, "key": key, "file": rel}},
                )
                return False, err.CHECKSUM_MISMATCH

        return True, None

    def resolve_path(self, key: str) -> Optional[Path]:
        """Local directory holding a verified model, or None."""
        entry = self.get_entry(key)
        if entry is None:
            return None
        root = self.models_dir / str(entry.get("local_dir", key))
        return root if root.exists() else None

    # --- Loading ---------------------------------------------------------------

    def load_model(self, expert_id: str, model_path: str, device: str = "cpu") -> Any:
        """Load a verified artefact via a factory registered by an adapter.

        ``model_path`` is a manifest key. Returns None on any failure so the
        caller can mark the expert unavailable and continue (C-27).
        """
        ok, reason = self.verify_model(model_path)
        if not ok:
            logger.warning(
                f"expert {expert_id}: model unavailable",
                extra={"extra_fields": {"code": reason, "expert_id": expert_id, "key": model_path}},
            )
            return None
        return self.resolve_path(model_path)

    def cache_get(self, key: str, device: str) -> Optional[Any]:
        with self._lock:
            return self._cache.get((key, device))

    def cache_put(self, key: str, device: str, value: Any) -> None:
        """Cache a loaded model so E3 and E4 sharing a backbone load one copy."""
        with self._lock:
            self._cache[(key, device)] = value

    def clear_cache(self) -> None:
        with self._lock:
            self._cache.clear()


#: Process-wide loader.
model_loader = ManifestModelLoader()

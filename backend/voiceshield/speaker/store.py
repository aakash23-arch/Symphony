"""JSON-backed speaker enrollment store (C-27).

Holds the reference embedding E4 compares against. Records the embedding
dimension and the model that produced it, so a reference enrolled with one
encoder is never silently compared against another's output - a 192-d ECAPA
vector and a 512-d WavLM vector are incomparable, and E4 must abstain rather
than raise inside a forward pass.

Stores embeddings only, never audio: a speaker profile is a vector, and raw
enrolment audio never needs to persist here (P2).
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np

from voiceshield.config import settings
from voiceshield.obs.logging import get_logger

from .enrollment import EnrollmentStore

logger = get_logger("voiceshield.speaker.store")


class JsonEnrollmentStore(EnrollmentStore):
    """Enrollment store persisted as a single JSON document."""

    def __init__(self, path: Optional[str] = None, autoload: bool = True):
        self.path = Path(path or settings.enrollment_path)
        self._records: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        if autoload:
            self.load()

    def load(self) -> None:
        """Read the store from disk. A missing file is normal (nobody enrolled)."""
        if not self.path.exists():
            self._records = {}
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self._records = data.get("speakers", {}) if isinstance(data, dict) else {}
        except (json.JSONDecodeError, OSError) as exc:
            # A corrupt store means "nobody is enrolled", which makes E4 abstain.
            # That is the safe reading: it must not mean "anyone matches".
            logger.error(
                "enrollment store unreadable; treating as empty",
                extra={"extra_fields": {"path": str(self.path), "detail": str(exc)[:200]}},
            )
            self._records = {}

    def save(self) -> None:
        """Persist the store, creating parent directories as needed."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"schema_version": 1, "speakers": self._records}
        self.path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    @property
    def embedding_dim(self) -> Optional[int]:
        with self._lock:
            for record in self._records.values():
                dim = record.get("dim")
                if dim:
                    return int(dim)
        return None

    def get_embedding(self, speaker_id: str) -> Optional[np.ndarray]:
        """Reference embedding for a speaker, or None if not enrolled."""
        with self._lock:
            record = self._records.get(speaker_id)
        if not record:
            return None
        values = record.get("embedding")
        if not values:
            return None
        return np.asarray(values, dtype=np.float32)

    def get_metadata(self, speaker_id: str) -> Optional[Dict[str, Any]]:
        """Provenance of an enrolment: dim, model id/version, timestamp."""
        with self._lock:
            record = self._records.get(speaker_id)
        if not record:
            return None
        return {k: v for k, v in record.items() if k != "embedding"}

    def enroll_speaker(
        self,
        speaker_id: str,
        embedding: np.ndarray,
        model_id: str = "unknown",
        model_version: str = "unknown",
        persist: bool = True,
    ) -> None:
        """Enroll a reference embedding together with its provenance."""
        vector = np.asarray(embedding, dtype=np.float32).ravel()
        if vector.size == 0:
            raise ValueError("cannot enroll an empty embedding")
        if not np.all(np.isfinite(vector)):
            raise ValueError("cannot enroll a non-finite embedding")

        with self._lock:
            self._records[speaker_id] = {
                "embedding": [float(x) for x in vector.tolist()],
                "dim": int(vector.size),
                "model_id": model_id,
                "model_version": model_version,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

        if persist:
            self.save()

        logger.info(
            "speaker enrolled",
            extra={
                "extra_fields": {
                    "speaker_id": speaker_id,
                    "dim": int(vector.size),
                    "model_id": model_id,
                    "model_version": model_version,
                }
            },
        )

    def is_enrolled(self, speaker_id: str) -> bool:
        with self._lock:
            return speaker_id in self._records

    def remove(self, speaker_id: str, persist: bool = True) -> bool:
        with self._lock:
            existed = self._records.pop(speaker_id, None) is not None
        if existed and persist:
            self.save()
        return existed

    def list_speakers(self) -> list:
        with self._lock:
            return sorted(self._records.keys())

"""Privacy controller interface (C-45)."""

from abc import ABC, abstractmethod


class PrivacyController(ABC):
    """Abstract interface enforcing zero-PCM persistence in SQLite and bounded TTL in Redis."""

    @abstractmethod
    def enforce_buffer_expiry(self, session_id: str) -> bool:
        """Trigger and verify active deletion of session audio frames in memory."""
        raise NotImplementedError("PrivacyController.enforce_buffer_expiry is not implemented yet")

    @abstractmethod
    def get_privacy_status(self) -> dict:
        """Return audit telemetry regarding active audio buffers and retention state."""
        raise NotImplementedError("PrivacyController.get_privacy_status is not implemented yet")

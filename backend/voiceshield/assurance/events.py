"""Event publisher interface (C-46)."""

from abc import ABC, abstractmethod
from typing import Any, Dict
from voiceshield.contracts import EventType, WebSocketEventEnvelope


class EventPublisher(ABC):
    """Abstract interface for publishing monotonic WebSocket event envelopes to Redis pub/sub."""

    @abstractmethod
    async def publish(
        self,
        session_id: str,
        event_type: EventType,
        data: Dict[str, Any],
    ) -> WebSocketEventEnvelope:
        """Publish event envelope with monotonically incremented sequence number."""
        raise NotImplementedError("EventPublisher.publish is not implemented yet")

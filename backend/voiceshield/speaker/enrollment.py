"""Speaker enrollment store interface (C-27)."""

from abc import ABC, abstractmethod
from typing import List, Optional
import numpy as np


class EnrollmentStore(ABC):
    """Abstract interface for managing enrolled speaker reference embeddings.

    Embedding dimensionality is MODEL-DEPENDENT and must not be assumed:
    WavLMForXVector emits 512-d, ECAPA-TDNN emits 192-d. A store therefore
    records the dimension alongside each embedding so a reference enrolled with
    one encoder is never silently compared against another's output.
    """

    @property
    @abstractmethod
    def embedding_dim(self) -> Optional[int]:
        """Dimensionality of stored embeddings, or None if nothing is enrolled."""
        raise NotImplementedError("EnrollmentStore.embedding_dim is not implemented yet")

    @abstractmethod
    def get_embedding(self, speaker_id: str) -> Optional[np.ndarray]:
        """Retrieve the reference speaker embedding for an enrolled speaker ID."""
        raise NotImplementedError("EnrollmentStore.get_embedding is not implemented yet")

    @abstractmethod
    def enroll_speaker(self, speaker_id: str, embedding: np.ndarray) -> None:
        """Enroll reference speaker embedding."""
        raise NotImplementedError("EnrollmentStore.enroll_speaker is not implemented yet")

    @abstractmethod
    def is_enrolled(self, speaker_id: str) -> bool:
        """Check if speaker has an enrolled profile."""
        raise NotImplementedError("EnrollmentStore.is_enrolled is not implemented yet")

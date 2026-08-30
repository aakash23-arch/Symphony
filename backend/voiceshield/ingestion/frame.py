"""FrameObject assembly (C-13).

Assembles the frozen FrameObject (§6.1) from the outputs of C-07..C-12 and
validates it. Adds no field that is not in the frozen contract -- the model's
extra="forbid" makes that a hard failure rather than a convention.

On a validation error the frame is dropped, FRAME_INVALID is logged and counted,
and the session continues: one bad frame must not end a call.
"""

from datetime import datetime, timezone
from typing import Optional

import numpy as np
from pydantic import ValidationError

from voiceshield.contracts.frame import CodecDescriptor, FrameObject
from voiceshield.obs.logging import get_logger

from .channel import ChannelProfile
from .errors import FRAME_INVALID
from .language import LanguageResult
from .quality import QualityReport
from .turns import TurnResult
from .vad import VadResult

logger = get_logger("voiceshield.ingestion.frame")


class FrameObjectAssembler:
    """Build and validate FrameObjects. Counts, but never re-raises, bad frames."""

    def __init__(self) -> None:
        self.invalid_count = 0
        self.assembled_count = 0

    def assemble(
        self,
        session_id: str,
        frame_id: int,
        pcm: np.ndarray,
        sample_rate: int,
        t_start: float,
        t_end: float,
        channel: ChannelProfile,
        quality: QualityReport,
        vad: VadResult,
        turns: TurnResult,
        language: LanguageResult,
        source_type: str,
    ) -> Optional[FrameObject]:
        """Return a validated FrameObject, or None if it failed validation."""
        try:
            frame = FrameObject(
                session_id=session_id,
                frame_id=frame_id,
                pcm=[float(x) for x in np.asarray(pcm, dtype=np.float32).tolist()],
                sample_rate=sample_rate,
                t_start=float(t_start),
                t_end=float(t_end),
                codec_vec=channel.codec_vec,
                bandwidth=channel.bandwidth,
                packet_loss=channel.packet_loss,
                q_t=quality.q_t,
                is_speech=bool(vad.is_speech),
                speaker_turn=turns.speaker_turn,
                overlap_flag=turns.overlap_flag,
                lang_t=language.lang_t,
                switch_flag=bool(language.switch_flag),
                source_type=source_type,
                created_at=datetime.now(timezone.utc),
            )
        except (ValidationError, TypeError, ValueError) as exc:
            self.invalid_count += 1
            logger.warning(
                "Dropping invalid frame; session continues",
                extra={
                    "extra_fields": {
                        "code": FRAME_INVALID,
                        "session_id": session_id,
                        "frame_id": frame_id,
                        "error": str(exc),
                    }
                },
            )
            return None

        self.assembled_count += 1
        return frame


__all__ = ["FrameObjectAssembler", "CodecDescriptor", "FrameObject"]

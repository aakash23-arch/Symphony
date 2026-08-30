"""FrameObject contract (C-01..C-14, §6.1)."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class CodecDescriptor(BaseModel):
    """Audio codec metadata descriptor."""
    model_config = ConfigDict(extra="forbid")
    name: str = Field(description="Codec name, e.g. 'pcm_s16le', 'opus', 'g711a'")
    sample_rate: int = Field(description="Sample rate in Hz")
    bitrate: Optional[int] = Field(default=None, description="Bitrate in bps if known")
    packet_loss_rate: Optional[float] = Field(default=None, description="Estimated packet loss rate [0, 1]")


class FrameObject(BaseModel):
    """Audio frame object representing a canonical audio chunk with DSP telemetry."""
    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(description="Unique session identifier")
    frame_id: int = Field(description="Monotonic sequence number within session")

    pcm: List[float] = Field(description="Canonical mono audio PCM float32 samples")
    sample_rate: int = Field(default=16000, description="Sample rate in Hz (canonical: 16000)")

    t_start: float = Field(description="Start time in seconds from session start")
    t_end: float = Field(description="End time in seconds from session start")

    codec_vec: Optional[CodecDescriptor] = Field(default=None, description="Codec descriptor or None if UNKNOWN")
    bandwidth: Optional[float] = Field(default=None, description="Estimated effective bandwidth in Hz")
    packet_loss: Optional[float] = Field(default=None, description="Packet loss fraction [0, 1]")

    q_t: Optional[float] = Field(default=None, description="Frame acoustic quality score [0, 1]")

    is_speech: bool = Field(default=True, description="Voice Activity Detection (VAD) flag")
    speaker_turn: Optional[int] = Field(default=None, description="Diarization speaker turn index")
    overlap_flag: Optional[bool] = Field(default=None, description="Multi-speaker overlap flag")

    lang_t: str = Field(default="UNKNOWN", description="Language ISO code or 'UNKNOWN'")
    switch_flag: bool = Field(default=False, description="Code-switch transition detected")

    source_type: str = Field(default="wav", description="Opaque source tag: 'wav' | 'mic' | 'ws'")
    created_at: datetime = Field(description="UTC timestamp of frame creation")

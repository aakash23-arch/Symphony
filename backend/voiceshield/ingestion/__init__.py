"""Ingestion module (L1).

Turns raw audio from any source into validated FrameObjects. Performs no ML
classification, produces no detection scores, and hardcodes no risk result.
"""

from .buffering import FrameAssembler, RawFrame
from .channel import ChannelProfile, ChannelProfiler
from .errors import (
    AudioFormatRejected,
    FrameRejected,
    SessionError,
    SourceUnavailable,
)
from .frame import FrameObjectAssembler
from .language import LanguageResult, LanguageTagger
from .pipeline import IngestionPipeline, L1IngestionPipeline
from .preprocessing import Normaliser
from .publisher import FramePublisher, InMemoryFramePublisher
from .quality import QualityEstimator, QualityReport
from .session import SessionManager, SessionRecord, SessionState
from .sources import (
    AudioSource,
    FakeSource,
    MicrophoneSource,
    WavFileSource,
    WebSocketSource,
)
from .turns import TurnResult, TurnSegmenter
from .vad import VadResult, VoiceActivityDetector

__all__ = [
    # sources (C-01..C-04)
    "AudioSource",
    "FakeSource",
    "WavFileSource",
    "MicrophoneSource",
    "WebSocketSource",
    # session (C-05)
    "SessionManager",
    "SessionRecord",
    "SessionState",
    # buffering (C-06)
    "FrameAssembler",
    "RawFrame",
    # preprocessing (C-07)
    "Normaliser",
    # analysis (C-08..C-12)
    "ChannelProfiler",
    "ChannelProfile",
    "QualityEstimator",
    "QualityReport",
    "VoiceActivityDetector",
    "VadResult",
    "TurnSegmenter",
    "TurnResult",
    "LanguageTagger",
    "LanguageResult",
    # assembly + publish (C-13, C-14)
    "FrameObjectAssembler",
    "FramePublisher",
    "InMemoryFramePublisher",
    # pipeline
    "IngestionPipeline",
    "L1IngestionPipeline",
    # errors
    "SourceUnavailable",
    "AudioFormatRejected",
    "FrameRejected",
    "SessionError",
]

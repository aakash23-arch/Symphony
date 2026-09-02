"""Audio validation module for inspecting raw audio inputs before decoding."""

import io
import os
import wave
from pathlib import Path
from typing import Optional, Tuple, Union

import numpy as np

from .contracts import (
    AudioFormat,
    AudioValidationResult,
    ValidationStatus,
)


class AudioValidator:
    """Validates audio file integrity, headers, formats, and basic bounds."""

    MIN_DURATION_S = 0.3
    MAX_DURATION_S = 180.0
    MIN_SAMPLE_RATE = 8000
    MAX_SAMPLE_RATE = 96000
    CLIPPING_THRESHOLD = 0.999
    CLIPPING_RATIO_ALERT = 0.05

    def detect_format(self, audio_bytes: bytes) -> AudioFormat:
        """Inspect magic bytes to detect container format."""
        if len(audio_bytes) < 12:
            return AudioFormat.UNKNOWN

        if audio_bytes[:4] == b"RIFF" and audio_bytes[8:12] == b"WAVE":
            return AudioFormat.WAV
        if audio_bytes[:3] == b"ID3" or audio_bytes[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"):
            return AudioFormat.MP3
        if audio_bytes[:4] == b"fLaC":
            return AudioFormat.FLAC
        if audio_bytes[:4] == b"OggS":
            return AudioFormat.OGG

        return AudioFormat.RAW_PCM

    def validate_bytes(
        self, audio_bytes: bytes, filename_hint: Optional[str] = None
    ) -> Tuple[bool, AudioValidationResult]:
        """Validate raw audio bytes."""
        notes = []
        if not audio_bytes or len(audio_bytes) == 0:
            res = AudioValidationResult(
                status=ValidationStatus.EMPTY,
                is_valid=False,
                detected_format=AudioFormat.UNKNOWN,
                sample_rate=0,
                channels=0,
                duration_seconds=0.0,
                samples_count=0,
                clipping_ratio=0.0,
                is_silent=True,
                validation_notes=["Audio payload is empty (0 bytes)."],
            )
            return False, res

        fmt = self.detect_format(audio_bytes)
        
        # If WAV, inspect header without external heavy libraries
        if fmt == AudioFormat.WAV:
            try:
                with wave.open(io.BytesIO(audio_bytes), "rb") as wf:
                    channels = wf.getnchannels()
                    sr = wf.getframerate()
                    frames = wf.getnframes()
                    sampwidth = wf.getsampwidth()
                    duration = frames / float(sr) if sr > 0 else 0.0

                    if sr < self.MIN_SAMPLE_RATE or sr > self.MAX_SAMPLE_RATE:
                        notes.append(f"Sample rate {sr} Hz outside standard range ({self.MIN_SAMPLE_RATE}-{self.MAX_SAMPLE_RATE} Hz).")

                    if duration < self.MIN_DURATION_S:
                        notes.append(f"Audio duration {duration:.2f}s is below minimum {self.MIN_DURATION_S}s.")
                    elif duration > self.MAX_DURATION_S:
                        notes.append(f"Audio duration {duration:.2f}s exceeds maximum {self.MAX_DURATION_S}s.")

                    is_valid = len(notes) == 0
                    status = ValidationStatus.VALID if is_valid else ValidationStatus.INVALID
                    
                    return is_valid, AudioValidationResult(
                        status=status,
                        is_valid=is_valid,
                        detected_format=fmt,
                        sample_rate=sr,
                        channels=channels,
                        duration_seconds=duration,
                        samples_count=frames,
                        clipping_ratio=0.0,
                        is_silent=False,
                        validation_notes=notes,
                    )
            except Exception as e:
                return False, AudioValidationResult(
                    status=ValidationStatus.CORRUPTED,
                    is_valid=False,
                    detected_format=fmt,
                    sample_rate=0,
                    channels=0,
                    duration_seconds=0.0,
                    samples_count=0,
                    clipping_ratio=0.0,
                    is_silent=False,
                    validation_notes=[f"Failed to parse WAV header: {str(e)}"],
                )

        # For non-WAV formats or raw PCM, return valid format descriptor to be verified post-decode
        return True, AudioValidationResult(
            status=ValidationStatus.VALID,
            is_valid=True,
            detected_format=fmt,
            sample_rate=16000,
            channels=1,
            duration_seconds=0.0,
            samples_count=0,
            clipping_ratio=0.0,
            is_silent=False,
            validation_notes=notes,
        )

    def validate_pcm(self, pcm: np.ndarray, sample_rate: int = 16000) -> AudioValidationResult:
        """Validate decoded float32 PCM numpy array."""
        notes = []
        if pcm is None or len(pcm) == 0:
            return AudioValidationResult(
                status=ValidationStatus.EMPTY,
                is_valid=False,
                detected_format=AudioFormat.RAW_PCM,
                sample_rate=sample_rate,
                channels=1,
                duration_seconds=0.0,
                samples_count=0,
                clipping_ratio=0.0,
                is_silent=True,
                validation_notes=["PCM array is empty."],
            )

        if not np.isfinite(pcm).all():
            return AudioValidationResult(
                status=ValidationStatus.CORRUPTED,
                is_valid=False,
                detected_format=AudioFormat.RAW_PCM,
                sample_rate=sample_rate,
                channels=1,
                duration_seconds=len(pcm) / sample_rate,
                samples_count=len(pcm),
                clipping_ratio=0.0,
                is_silent=False,
                validation_notes=["PCM array contains NaN or Inf values."],
            )

        duration = len(pcm) / float(sample_rate)
        max_amp = float(np.max(np.abs(pcm)))
        is_silent = max_amp < 1e-4

        if is_silent:
            notes.append("Audio is virtually silent (max amplitude < 1e-4).")

        clipping_count = np.sum(np.abs(pcm) >= self.CLIPPING_THRESHOLD)
        clipping_ratio = float(clipping_count) / len(pcm)

        if clipping_ratio > self.CLIPPING_RATIO_ALERT:
            notes.append(f"High digital clipping detected: {clipping_ratio * 100:.1f}% of samples exceed threshold.")

        if duration < self.MIN_DURATION_S:
            notes.append(f"Audio duration {duration:.2f}s is below minimum {self.MIN_DURATION_S}s.")
        elif duration > self.MAX_DURATION_S:
            notes.append(f"Audio duration {duration:.2f}s exceeds maximum {self.MAX_DURATION_S}s.")

        is_valid = len(notes) == 0 and not is_silent
        status = ValidationStatus.VALID if is_valid else ValidationStatus.INVALID

        return AudioValidationResult(
            status=status,
            is_valid=is_valid,
            detected_format=AudioFormat.RAW_PCM,
            sample_rate=sample_rate,
            channels=1 if pcm.ndim == 1 else pcm.shape[1],
            duration_seconds=duration,
            samples_count=len(pcm),
            clipping_ratio=clipping_ratio,
            is_silent=is_silent,
            validation_notes=notes,
        )

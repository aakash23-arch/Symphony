"""PCM normalisation (C-07).

Decode to float PCM, downmix to mono, resample to the canonical rate, apply
amplitude normalisation.

HARD RULE (C-07): this stage must NOT denoise, dereverb, or apply any spectral
enhancement. Aggressive enhancement destroys the synthesis artefacts that L3
depends on. Only channel downmix, rate conversion and scalar gain are permitted.

Note on module placement: the architecture document names this component
``signal_processing.preprocessing``, but the enforced import-boundary test
forbids ``ingestion`` -> ``signal_processing``. It lives here so L1 stays
self-contained; behaviour is unchanged.
"""

from typing import Optional

import numpy as np
from scipy.signal import resample_poly

from voiceshield.config import settings

from .errors import FRAME_REJECTED, FrameRejected
from .sources import PCM_F32LE, PCM_S16LE

#: Peak below which amplitude normalisation is skipped, so that near-silence is
#: not amplified into noise.
SILENCE_PEAK_FLOOR = 1e-4

#: Target peak for amplitude normalisation.
TARGET_PEAK = 0.95

MIN_SAMPLE_RATE = 4000
MAX_SAMPLE_RATE = 384000


class Normaliser:
    """Convert raw source bytes into canonical float32 mono PCM at the target rate."""

    def __init__(
        self,
        target_sample_rate: Optional[int] = None,
        target_channels: Optional[int] = None,
        normalise_amplitude: bool = True,
    ):
        self.target_sample_rate = target_sample_rate or settings.audio_sample_rate
        self.target_channels = target_channels or settings.audio_channels
        self.normalise_amplitude = normalise_amplitude
        self.rejected_count = 0

    # -- decode ---------------------------------------------------------------

    @staticmethod
    def decode(data: bytes, encoding: str, channels: int) -> np.ndarray:
        """Decode raw bytes into a float32 array shaped (frames, channels)."""
        if encoding == PCM_S16LE:
            flat = np.frombuffer(data, dtype="<i2").astype(np.float32) / 32768.0
        elif encoding == PCM_F32LE:
            flat = np.frombuffer(data, dtype="<f4").astype(np.float32)
        else:
            raise FrameRejected(f"Unsupported encoding: {encoding!r}")

        if channels < 1:
            raise FrameRejected(f"Invalid channel count: {channels}")
        usable = (flat.size // channels) * channels
        if usable == 0:
            return np.zeros((0, channels), dtype=np.float32)
        return flat[:usable].reshape(-1, channels)

    # -- downmix --------------------------------------------------------------

    @staticmethod
    def to_mono(samples: np.ndarray) -> np.ndarray:
        """Downmix to a single channel by averaging (no enhancement)."""
        if samples.ndim == 1:
            return samples.astype(np.float32, copy=False)
        if samples.shape[1] == 1:
            return samples[:, 0].astype(np.float32, copy=False)
        return samples.mean(axis=1, dtype=np.float32)

    # -- resample -------------------------------------------------------------

    def resample(self, mono: np.ndarray, source_rate: int) -> np.ndarray:
        """Rate-convert to the canonical rate via polyphase filtering."""
        if source_rate == self.target_sample_rate or mono.size == 0:
            return mono.astype(np.float32, copy=False)
        if not (MIN_SAMPLE_RATE <= source_rate <= MAX_SAMPLE_RATE):
            raise FrameRejected(f"Unsupported source sample rate: {source_rate}")

        gcd = np.gcd(int(source_rate), int(self.target_sample_rate))
        up = int(self.target_sample_rate // gcd)
        down = int(source_rate // gcd)
        resampled = resample_poly(mono.astype(np.float64), up, down)
        return np.asarray(resampled, dtype=np.float32)

    # -- amplitude ------------------------------------------------------------

    @staticmethod
    def apply_gain(mono: np.ndarray, target_peak: float = TARGET_PEAK) -> np.ndarray:
        """Scalar peak normalisation. Skipped for near-silence; never a spectral op."""
        if mono.size == 0:
            return mono
        peak = float(np.max(np.abs(mono)))
        if peak < SILENCE_PEAK_FLOOR:
            return mono
        return (mono * (target_peak / peak)).astype(np.float32, copy=False)

    # -- pipeline -------------------------------------------------------------

    def normalise(
        self,
        data: bytes,
        source_rate: int,
        channels: int,
        encoding: str = PCM_S16LE,
    ) -> np.ndarray:
        """Full C-07 path: decode -> mono -> resample -> gain.

        Raises FrameRejected on unsupported rate/format; the caller drops the
        frame, increments a counter, and the session continues.
        """
        try:
            decoded = self.decode(data, encoding, channels)
            mono = self.to_mono(decoded)
            resampled = self.resample(mono, source_rate)
        except FrameRejected:
            self.rejected_count += 1
            raise
        except Exception as exc:
            self.rejected_count += 1
            raise FrameRejected(f"Normalisation failed: {exc}", reason=FRAME_REJECTED) from exc

        if self.normalise_amplitude:
            resampled = self.apply_gain(resampled)

        return np.clip(resampled, -1.0, 1.0).astype(np.float32, copy=False)

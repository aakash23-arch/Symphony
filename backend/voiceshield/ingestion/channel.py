"""Channel profiling (C-08).

Estimate codec_vec, bandwidth and packet_loss from the signal and source
metadata. Never guesses a codec when the source is a WAV file with no codec
history: UNKNOWN (None) is the expected value for file input, not an error.
"""

from dataclasses import dataclass
from typing import Optional

import numpy as np

from voiceshield.contracts.frame import CodecDescriptor

#: Fraction of total spectral energy used to define "effective" bandwidth.
BANDWIDTH_ENERGY_FRACTION = 0.99

#: Source types whose codec history is genuinely known from the container.
_KNOWN_CODEC_SOURCES = {"ws"}


@dataclass
class ChannelProfile:
    """Channel descriptors attached to a frame."""

    codec_vec: Optional[CodecDescriptor]
    bandwidth: Optional[float]
    packet_loss: Optional[float]


class ChannelProfiler:
    """Estimate channel descriptors from canonical PCM plus source metadata."""

    def __init__(self, energy_fraction: float = BANDWIDTH_ENERGY_FRACTION):
        self.energy_fraction = energy_fraction

    def estimate_bandwidth(self, pcm: np.ndarray, sample_rate: int) -> Optional[float]:
        """Highest frequency below which `energy_fraction` of the energy lies."""
        if pcm.size < 32 or sample_rate <= 0:
            return None
        try:
            windowed = pcm.astype(np.float64) * np.hanning(pcm.size)
            spectrum = np.abs(np.fft.rfft(windowed)) ** 2
            total = float(spectrum.sum())
            if total <= 0.0:
                return None
            cumulative = np.cumsum(spectrum) / total
            idx = int(np.searchsorted(cumulative, self.energy_fraction))
            freqs = np.fft.rfftfreq(pcm.size, d=1.0 / sample_rate)
            idx = min(idx, freqs.size - 1)
            return float(freqs[idx])
        except Exception:
            return None

    def profile(
        self,
        pcm: np.ndarray,
        sample_rate: int,
        source_type: str,
        native_sample_rate: Optional[int] = None,
        packet_loss: Optional[float] = None,
    ) -> ChannelProfile:
        """Build the channel descriptors for one frame."""
        bandwidth = self.estimate_bandwidth(pcm, sample_rate)

        codec_vec: Optional[CodecDescriptor] = None
        if source_type in _KNOWN_CODEC_SOURCES:
            # The browser pushes linear PCM over the wire; that much is known.
            codec_vec = CodecDescriptor(
                name="pcm_s16le",
                sample_rate=native_sample_rate or sample_rate,
                bitrate=None,
                packet_loss_rate=packet_loss,
            )

        return ChannelProfile(
            codec_vec=codec_vec,
            bandwidth=bandwidth,
            packet_loss=packet_loss,
        )

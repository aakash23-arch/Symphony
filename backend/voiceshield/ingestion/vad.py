"""Voice activity detection (C-10).

Classifies each frame is_speech from short-time energy, zero-crossing rate and
an adaptive noise floor. It does not identify who is speaking, transcribe, or
decide language.

Fail-open: any detector error yields is_speech = True with a logged warning.
For a security system, sending an uncertain frame into analysis is the
conservative direction.
"""

from dataclasses import dataclass
from typing import Optional

import numpy as np

from voiceshield.obs.logging import get_logger

logger = get_logger("voiceshield.ingestion.vad")

_EPS = 1e-12

#: Energy (dB) a sub-window must exceed above the adaptive noise floor.
DEFAULT_ENERGY_MARGIN_DB = 8.0
#: Absolute floor: sub-windows quieter than this are never speech.
DEFAULT_ABSOLUTE_FLOOR_DB = -60.0
#: Zero-crossing rate above which a loud sub-window is treated as fricative-like
#: rather than tonal noise.
DEFAULT_ZCR_CEILING = 0.45
#: Fraction of speech sub-windows needed to mark the whole frame as speech.
DEFAULT_SPEECH_RATIO = 0.30
#: Sub-windows of hangover after speech, so word-final fricatives are not cut.
DEFAULT_HANGOVER = 3


@dataclass
class VadResult:
    """VAD decision plus a margin. Only is_speech fits the frozen contract."""

    is_speech: bool
    #: Mean dB by which speech sub-windows exceeded the decision threshold.
    margin_db: float = 0.0
    speech_ratio: float = 0.0
    noise_floor_db: Optional[float] = None
    failed_open: bool = False


class VoiceActivityDetector:
    """Energy + ZCR VAD with an adaptive noise floor and hangover."""

    def __init__(
        self,
        sub_window_ms: int = 20,
        energy_margin_db: float = DEFAULT_ENERGY_MARGIN_DB,
        absolute_floor_db: float = DEFAULT_ABSOLUTE_FLOOR_DB,
        zcr_ceiling: float = DEFAULT_ZCR_CEILING,
        speech_ratio: float = DEFAULT_SPEECH_RATIO,
        hangover: int = DEFAULT_HANGOVER,
        noise_adapt: float = 0.05,
    ):
        self.sub_window_ms = sub_window_ms
        self.energy_margin_db = energy_margin_db
        self.absolute_floor_db = absolute_floor_db
        self.zcr_ceiling = zcr_ceiling
        self.speech_ratio = speech_ratio
        self.hangover = hangover
        self.noise_adapt = noise_adapt

        self._noise_floor_db: Optional[float] = None
        self._hangover_left = 0
        self.failure_count = 0

    def reset(self) -> None:
        self._noise_floor_db = None
        self._hangover_left = 0

    @staticmethod
    def _zcr(window: np.ndarray) -> float:
        if window.size < 2:
            return 0.0
        return float(np.count_nonzero(np.diff(np.signbit(window))) / (window.size - 1))

    def detect(self, pcm: np.ndarray, sample_rate: int) -> VadResult:
        """Classify one frame. Never raises: failures fail open to speech."""
        try:
            return self._detect(pcm, sample_rate)
        except Exception as exc:
            self.failure_count += 1
            logger.warning(
                "VAD failed; failing open to is_speech=True",
                extra={"extra_fields": {"error": str(exc)}},
            )
            return VadResult(is_speech=True, failed_open=True)

    def _detect(self, pcm: np.ndarray, sample_rate: int) -> VadResult:
        if pcm.size == 0 or sample_rate <= 0:
            return VadResult(is_speech=False, noise_floor_db=self._noise_floor_db)

        win = max(int(sample_rate * self.sub_window_ms / 1000.0), 1)
        if pcm.size < win:
            win = pcm.size
        usable = (pcm.size // win) * win
        windows = pcm[:usable].reshape(-1, win).astype(np.float64)

        rms = np.sqrt(np.mean(windows**2, axis=1))
        energies_db = 20.0 * np.log10(np.maximum(rms, _EPS))

        if self._noise_floor_db is None:
            # Seed the floor from the quietest part of the first frame, but only
            # trust it as a NOISE estimate if the frame actually contains a quiet
            # part. A uniformly loud first frame (all speech) would otherwise
            # seed the floor at speech level and mask every later frame.
            quiet_db = float(np.percentile(energies_db, 10))
            loud_db = float(np.percentile(energies_db, 90))
            if loud_db - quiet_db >= self.energy_margin_db:
                self._noise_floor_db = quiet_db
            else:
                self._noise_floor_db = min(quiet_db, self.absolute_floor_db)

        speech_flags = []
        margins = []
        for idx in range(windows.shape[0]):
            energy_db = float(energies_db[idx])
            threshold = max(
                self._noise_floor_db + self.energy_margin_db,
                self.absolute_floor_db,
            )
            zcr = self._zcr(windows[idx])

            loud_enough = energy_db > threshold
            # Very high ZCR at low energy is noise, not voice.
            tonal_enough = zcr <= self.zcr_ceiling or energy_db > threshold + 12.0
            is_speech_win = bool(loud_enough and tonal_enough)

            if is_speech_win:
                self._hangover_left = self.hangover
                margins.append(energy_db - threshold)
            elif self._hangover_left > 0:
                self._hangover_left -= 1
                is_speech_win = True
            else:
                # Adapt the noise floor only on genuine non-speech.
                self._noise_floor_db = (
                    (1.0 - self.noise_adapt) * self._noise_floor_db
                    + self.noise_adapt * energy_db
                )

            speech_flags.append(is_speech_win)

        ratio = float(np.mean(speech_flags)) if speech_flags else 0.0
        return VadResult(
            is_speech=ratio >= self.speech_ratio,
            margin_db=float(np.mean(margins)) if margins else 0.0,
            speech_ratio=ratio,
            noise_floor_db=self._noise_floor_db,
        )

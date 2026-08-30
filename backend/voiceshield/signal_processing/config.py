import dataclasses

@dataclasses.dataclass(frozen=True)
class SpectrogramConfig:
    sample_rate: int = 16000
    n_fft: int = 512
    hop_length: int = 160
    win_length: int = 400
    window: str = "hann"
    n_mels: int = 80
    f_min: float = 0.0
    f_max: float = 8000.0
    power: float = 2.0
    top_db: float = 80.0
    eps: float = 1e-6

@dataclasses.dataclass(frozen=True)
class MFCCConfig:
    n_mfcc: int = 13
    include_delta: bool = True
    include_delta_delta: bool = True
    dct_type: int = 2
    lifter: float = 0.0

@dataclasses.dataclass(frozen=True)
class PitchConfig:
    f0_min: float = 50.0
    f0_max: float = 500.0
    voicing_threshold: float = 0.45
    silence_threshold: float = 1e-4
    method: str = "autocorr"

@dataclasses.dataclass(frozen=True)
class ProsodyConfig:
    pause_threshold_db: float = -40.0
    min_pause_duration_ms: float = 100.0
    speaking_rate_min_voiced_ms: float = 60.0

@dataclasses.dataclass(frozen=True)
class SignalProcessingConfig:
    spectrogram: SpectrogramConfig = dataclasses.field(default_factory=SpectrogramConfig)
    mfcc: MFCCConfig = dataclasses.field(default_factory=MFCCConfig)
    pitch: PitchConfig = dataclasses.field(default_factory=PitchConfig)
    prosody: ProsodyConfig = dataclasses.field(default_factory=ProsodyConfig)

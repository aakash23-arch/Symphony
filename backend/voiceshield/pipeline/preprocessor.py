"""Audio preprocessing, resampling, normalization, VAD, and segmentation module."""

import io
from typing import List, Tuple
import librosa
import numpy as np
import soundfile as sf

from .contracts import AudioSegment, PreprocessingSummary


class AudioPreprocessor:
    """Decodes, resamples, normalizes, detects speech, and segments audio."""

    TARGET_SAMPLE_RATE = 16000
    TARGET_PEAK_DB = -1.0
    VAD_FRAME_MS = 30
    VAD_ENERGY_THRESHOLD_DB = -40.0
    SEGMENT_WINDOW_S = 3.0
    SEGMENT_HOP_S = 1.5

    def decode_audio(self, audio_bytes: bytes) -> Tuple[np.ndarray, int]:
        """Decode audio bytes to float32 numpy array and native sample rate."""
        bio = io.BytesIO(audio_bytes)
        try:
            pcm, sr = sf.read(bio, dtype="float32", always_2d=False)
            return pcm, int(sr)
        except Exception:
            # Fallback to librosa
            bio.seek(0)
            pcm, sr = librosa.load(bio, sr=None, mono=False, dtype=np.float32)
            return pcm, int(sr)

    def downmix_to_mono(self, pcm: np.ndarray) -> np.ndarray:
        """Downmix multi-channel audio to single-channel mono."""
        if pcm.ndim == 1:
            return pcm
        if pcm.ndim == 2:
            # Shape can be (samples, channels) or (channels, samples)
            if pcm.shape[1] < pcm.shape[0]:
                return np.mean(pcm, axis=1)
            else:
                return np.mean(pcm, axis=0)
        return pcm.flatten()

    def resample(self, pcm: np.ndarray, source_sr: int, target_sr: int = 16000) -> np.ndarray:
        """Resample audio signal to canonical 16,000 Hz."""
        if source_sr == target_sr:
            return pcm
        return librosa.resample(pcm, orig_sr=source_sr, target_sr=target_sr)

    def normalize_amplitude(self, pcm: np.ndarray, target_peak_db: float = -1.0) -> Tuple[np.ndarray, float]:
        """Peak-normalize audio to a target dBFS level."""
        current_peak = np.max(np.abs(pcm)) if len(pcm) > 0 else 0.0
        if current_peak <= 1e-6:
            return pcm, 0.0

        target_peak = 10.0 ** (target_peak_db / 20.0)
        gain = target_peak / current_peak
        gain_db = 20.0 * np.log10(gain + 1e-12)

        normalized = np.clip(pcm * gain, -1.0, 1.0)
        return normalized.astype(np.float32), float(gain_db)

    def estimate_snr_db(self, pcm: np.ndarray, sample_rate: int = 16000) -> float:
        """Estimate Signal-to-Noise Ratio (SNR) using spectral & percentile energy."""
        if len(pcm) == 0:
            return 0.0
        frame_len = int(sample_rate * 0.02)  # 20ms
        hop_len = int(sample_rate * 0.01)
        frames = librosa.util.frame(pcm, frame_length=frame_len, hop_length=hop_len)
        energies = np.sum(frames ** 2, axis=0) / frame_len
        energies_db = 10.0 * np.log10(energies + 1e-12)

        signal_db = float(np.percentile(energies_db, 90))
        noise_db = float(np.percentile(energies_db, 10))
        diff_db = signal_db - noise_db

        # If dynamic range is very small but overall RMS is high, it's a clean continuous tone
        rms_db = float(20.0 * np.log10(np.sqrt(np.mean(pcm ** 2)) + 1e-12))
        if diff_db < 3.0 and rms_db > -25.0:
            snr = float(rms_db + 60.0)  # High SNR for clean continuous waveform
        else:
            snr = float(diff_db)

        return float(np.clip(snr, 0.0, 60.0))

    def detect_voice_activity(
        self, pcm: np.ndarray, sample_rate: int = 16000
    ) -> Tuple[np.ndarray, float, float]:
        """Perform energy and spectral flux-based VAD. Returns (voiced_mask, voiced_ratio, active_duration_s)."""
        frame_len = int(sample_rate * (self.VAD_FRAME_MS / 1000.0))
        hop_len = frame_len // 2

        if len(pcm) < frame_len:
            return np.ones(1, dtype=bool), 1.0, len(pcm) / sample_rate

        frames = librosa.util.frame(pcm, frame_length=frame_len, hop_length=hop_len)
        rms = np.sqrt(np.mean(frames ** 2, axis=0) + 1e-12)
        rms_db = 20.0 * np.log10(rms + 1e-12)

        # Adaptive threshold based on noise floor
        noise_floor_db = np.percentile(rms_db, 15)
        vad_thresh_db = max(self.VAD_ENERGY_THRESHOLD_DB, noise_floor_db + 8.0)

        voiced_mask = rms_db >= vad_thresh_db
        voiced_ratio = float(np.mean(voiced_mask)) if len(voiced_mask) > 0 else 0.0
        active_speech_duration_s = float(np.sum(voiced_mask) * (hop_len / sample_rate))

        return voiced_mask, voiced_ratio, active_speech_duration_s

    def segment_audio(
        self, pcm: np.ndarray, sample_rate: int = 16000
    ) -> List[AudioSegment]:
        """Segment 16kHz PCM audio into analysis windows for detector inference."""
        window_samples = int(self.SEGMENT_WINDOW_S * sample_rate)
        hop_samples = int(self.SEGMENT_HOP_S * sample_rate)
        total_samples = len(pcm)

        segments: List[AudioSegment] = []

        if total_samples <= window_samples:
            # Audio shorter than or equal to window size: single segment
            rms = float(np.sqrt(np.mean(pcm ** 2))) if len(pcm) > 0 else 0.0
            segments.append(
                AudioSegment(
                    segment_index=0,
                    start_time_s=0.0,
                    end_time_s=total_samples / sample_rate,
                    duration_s=total_samples / sample_rate,
                    samples_count=total_samples,
                    is_voiced=rms > 1e-4,
                    rms_energy=rms,
                )
            )
            return segments

        # Sliding window
        start = 0
        seg_idx = 0
        while start < total_samples:
            end = min(start + window_samples, total_samples)
            chunk = pcm[start:end]
            rms = float(np.sqrt(np.mean(chunk ** 2))) if len(chunk) > 0 else 0.0

            # Only add segments with sufficient sample length (> 0.5s)
            if len(chunk) >= int(0.5 * sample_rate):
                segments.append(
                    AudioSegment(
                        segment_index=seg_idx,
                        start_time_s=start / float(sample_rate),
                        end_time_s=end / float(sample_rate),
                        duration_s=len(chunk) / float(sample_rate),
                        samples_count=len(chunk),
                        is_voiced=rms > 1e-4,
                        rms_energy=rms,
                    )
                )
                seg_idx += 1

            if end >= total_samples:
                break
            start += hop_samples

        return segments

    def process(
        self, audio_bytes: bytes
    ) -> Tuple[np.ndarray, List[AudioSegment], PreprocessingSummary]:
        """Execute full preprocessing pipeline on raw audio bytes."""
        raw_pcm, orig_sr = self.decode_audio(audio_bytes)
        orig_channels = 1 if raw_pcm.ndim == 1 else (raw_pcm.shape[1] if raw_pcm.shape[1] < raw_pcm.shape[0] else raw_pcm.shape[0])
        orig_duration = (len(raw_pcm) if raw_pcm.ndim == 1 else raw_pcm.shape[0]) / float(orig_sr)

        # 1. Downmix
        mono_pcm = self.downmix_to_mono(raw_pcm)

        # 2. Resample to canonical 16,000 Hz
        resampled_pcm = self.resample(mono_pcm, orig_sr, self.TARGET_SAMPLE_RATE)

        # 3. Peak Normalization
        norm_pcm, gain_db = self.normalize_amplitude(resampled_pcm, self.TARGET_PEAK_DB)

        # 4. VAD Analysis
        _, voiced_ratio, active_duration = self.detect_voice_activity(norm_pcm, self.TARGET_SAMPLE_RATE)

        # 5. SNR Estimation
        snr_db = self.estimate_snr_db(norm_pcm, self.TARGET_SAMPLE_RATE)

        # 6. Audio Segmentation
        segments = self.segment_audio(norm_pcm, self.TARGET_SAMPLE_RATE)

        summary = PreprocessingSummary(
            original_sample_rate=orig_sr,
            target_sample_rate=self.TARGET_SAMPLE_RATE,
            original_channels=orig_channels,
            original_duration_s=float(orig_duration),
            active_speech_duration_s=float(active_duration),
            voiced_ratio=float(voiced_ratio),
            snr_db=float(snr_db),
            num_segments=len(segments),
            peak_amplitude=float(np.max(np.abs(norm_pcm))) if len(norm_pcm) > 0 else 0.0,
            normalization_gain_db=float(gain_db),
        )

        return norm_pcm, segments, summary

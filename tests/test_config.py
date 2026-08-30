"""Tests for configuration management (C-52)."""

from voiceshield.config import Settings, AppRole, Environment


def test_default_settings():
    settings = Settings()
    assert settings.app_version == "0.1.0"
    assert settings.audio_sample_rate == 16000
    assert settings.audio_frame_ms == 20
    assert settings.policy_version == "1.0.0"
    assert settings.risk_threshold_warn == 0.45
    assert settings.risk_threshold_crit == 0.75


def test_redacted_dict():
    settings = Settings(redis_url="redis://user:secretpassword@redis.internal:6379/0")
    redacted = settings.redacted_dict()
    assert "secretpassword" not in redacted["redis_url"]
    assert "***:***" in redacted["redis_url"]

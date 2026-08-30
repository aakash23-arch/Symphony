"""Tests for structured logging and privacy scrubbing (C-53)."""

import json
import logging
from voiceshield.obs.logging import StructuredJsonFormatter


def test_structured_json_logging_scrubs_audio():
    formatter = StructuredJsonFormatter()
    record = logging.LogRecord(
        name="voiceshield.test",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Processing frame",
        args=(),
        exc_info=None,
    )
    record.correlation_id = "corr-12345"
    record.session_id = "sess-67890"
    record.extra_fields = {
        "frame_id": 42,
        "pcm": [0.1, 0.2, 0.3, 0.4],  # Forbidden audio key
        "raw_audio": b"binary_blob",   # Forbidden audio key
    }

    formatted = formatter.format(record)
    parsed = json.loads(formatted)

    assert parsed["message"] == "Processing frame"
    assert parsed["correlation_id"] == "corr-12345"
    assert parsed["session_id"] == "sess-67890"
    assert parsed["frame_id"] == 42
    assert parsed["pcm"] == "[SCRUBBED_AUDIO_PAYLOAD]"
    assert parsed["raw_audio"] == "[SCRUBBED_AUDIO_PAYLOAD]"

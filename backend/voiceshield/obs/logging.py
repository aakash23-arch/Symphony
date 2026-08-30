
"""VoiceShield structured logging module (C-53).

Provides structured JSON logging with correlation IDs, timestamps, and audio payload scrubbing.
"""

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional


class StructuredJsonFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects with privacy scrubbing."""

    FORBIDDEN_KEYS = {"pcm", "audio", "audio_data", "raw_audio", "wav_bytes", "payload"}

    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "role": getattr(record, "role", "unknown"),
        }

        if hasattr(record, "correlation_id"):
            log_entry["correlation_id"] = record.correlation_id
        if hasattr(record, "session_id"):
            log_entry["session_id"] = record.session_id

        # Attach extra structured fields while scrubbing forbidden audio keys
        if hasattr(record, "extra_fields") and isinstance(record.extra_fields, dict):
            for k, v in record.extra_fields.items():
                if k.lower() in self.FORBIDDEN_KEYS:
                    log_entry[k] = "[SCRUBBED_AUDIO_PAYLOAD]"
                else:
                    log_entry[k] = v

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)


def setup_logging(
    level: str = "INFO",
    log_format: str = "json",
    role: str = "all-in-one"
) -> logging.Logger:
    """Initialize and configure root and voiceshield loggers."""
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    if log_format.lower() == "json":
        handler.setFormatter(StructuredJsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

    root_logger.addHandler(handler)
    logger = logging.getLogger("voiceshield")
    logger.info("VoiceShield logging initialized", extra={"extra_fields": {"role": role}})
    return logger


def get_logger(name: str = "voiceshield") -> logging.Logger:
    """Get a named logger."""
    return logging.getLogger(name)

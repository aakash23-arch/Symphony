"""Standard error envelopes and exceptions (C-47, §7.1)."""

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class ErrorDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(description="Machine-readable error code")
    message: str = Field(description="Human-readable error description")
    session_id: Optional[str] = Field(default=None, description="Related session ID if applicable")
    correlation_id: str = Field(description="Unique correlation ID for tracing")
    retriable: bool = Field(default=False, description="Whether client should retry request")


class ErrorEnvelope(BaseModel):
    """Standardized API error response format."""
    model_config = ConfigDict(extra="forbid")
    error: ErrorDetail


class VoiceShieldException(Exception):
    """Base exception for VoiceShield errors."""
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        session_id: Optional[str] = None,
        retriable: bool = False,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.session_id = session_id
        self.retriable = retriable

"""Canonical inference API endpoint for modular audio anti-spoofing."""

import base64
import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import ValidationError

from voiceshield.pipeline.contracts import (
    InferenceRequest,
    InferenceResponse,
    TransactionContext,
)
from voiceshield.pipeline.orchestrator import default_orchestrator


def build_router(prefix: str, suffix: str = "") -> APIRouter:
    router = APIRouter(prefix=prefix, tags=["Inference"])

    @router.post(
        "",
        response_model=InferenceResponse,
        status_code=status.HTTP_200_OK,
        operation_id=f"run_inference{suffix}",
        summary="Run full modular anti-spoofing pipeline on audio asset",
    )
    async def run_inference_json(
        request: InferenceRequest,
    ) -> InferenceResponse:
        """Run modular inference pipeline using JSON request payload."""
        audio_bytes: Optional[bytes] = None

        if request.audio_base64:
            try:
                audio_bytes = base64.b64decode(request.audio_base64)
            except Exception as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"INVALID_BASE64: Failed to decode audio payload: {str(exc)}",
                ) from exc
        elif request.audio_fixture:
            # Resolve from demo/audio
            fixture_path = Path("demo/audio") / f"{request.audio_fixture}.wav"
            if not fixture_path.exists():
                fixture_path = Path("demo/audio") / request.audio_fixture
            if not fixture_path.exists():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"FIXTURE_NOT_FOUND: Audio fixture '{request.audio_fixture}' not found",
                )
            audio_bytes = fixture_path.read_bytes()
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="MISSING_AUDIO: Either 'audio_base64' or 'audio_fixture' must be provided.",
            )

        response = default_orchestrator.process_audio(
            audio_bytes=audio_bytes,
            session_id=request.session_id,
            request=request,
        )
        return response

    @router.post(
        "/upload",
        response_model=InferenceResponse,
        status_code=status.HTTP_200_OK,
        operation_id=f"upload_audio_inference{suffix}",
        summary="Upload audio file directly for anti-spoofing inference",
    )
    async def upload_audio_inference(
        file: UploadFile = File(..., description="Audio file (WAV, MP3, FLAC, OGG)"),
        session_id: Optional[str] = Form(None),
        transaction_json: Optional[str] = Form(None),
    ) -> InferenceResponse:
        """Run modular inference pipeline on uploaded audio multipart file."""
        try:
            audio_bytes = await file.read()
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"FILE_READ_ERROR: Could not read uploaded file: {str(exc)}",
            ) from exc

        tx_context = None
        if transaction_json:
            try:
                tx_data = json.loads(transaction_json)
                tx_context = TransactionContext(**tx_data)
            except Exception:
                pass

        req = InferenceRequest(
            session_id=session_id,
            transaction=tx_context,
        )

        response = default_orchestrator.process_audio(
            audio_bytes=audio_bytes,
            session_id=session_id,
            request=req,
        )
        return response

    return router


router = build_router("/v1/inference", "_v1")
api_router = build_router("/api/inference", "_api")
detect_router = build_router("/detect", "_root_detect")
v1_detect_router = build_router("/v1/detect", "_v1_detect")
api_detect_router = build_router("/api/detect", "_api_detect")

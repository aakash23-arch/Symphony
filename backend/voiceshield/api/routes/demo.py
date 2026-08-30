"""Demo Control API endpoints (C-51).

Provides routes to inspect available demo scenarios and launch a named scenario
through the real pipeline without allowing client-supplied risk scores.

Mounted on both /v1/demo and /api/demo.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Path, Query, status
from pydantic import BaseModel, ConfigDict, Field

from voiceshield.contracts import DEMO_ENVIRONMENT_LABEL
from voiceshield.demo.engine import default_scenario_engine

from ..runtime import get_runtime


class ScenarioOutcomeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    risk_band: str
    action: str
    decision_label: str
    target_policy: Optional[str] = None


class ScenarioDetailResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scenario_id: str
    title: str
    summary: str
    caller_name: str
    caller_ref: str
    audio_fixture: str
    context: Dict[str, Any]
    transaction: Optional[Dict[str, Any]] = None
    expected_outcome: Optional[ScenarioOutcomeResponse] = None
    environment: str = Field(default=DEMO_ENVIRONMENT_LABEL)


class ScenarioListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scenarios: List[ScenarioDetailResponse]
    environment: str = Field(default=DEMO_ENVIRONMENT_LABEL)
    disclaimer: str = Field(
        default="DEMO MODE: This environment uses controlled test audio and simulated transaction context. Scenarios are for demonstration only and not production functionality."
    )


class ScenarioStartResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: str
    scenario_id: str
    transaction_id: Optional[str] = None
    audio_fixture: str
    caller_name: str
    caller_ref: str
    state: str
    environment: str = Field(default=DEMO_ENVIRONMENT_LABEL)
    disclaimer: str = Field(
        default="DEMO MODE: Controlled test audio and simulated transaction context."
    )
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


def build_router(prefix: str, suffix: str = "") -> APIRouter:
    router = APIRouter(prefix=prefix, tags=["Demo"])

    @router.get(
        "/scenarios",
        response_model=ScenarioListResponse,
        status_code=status.HTTP_200_OK,
        operation_id=f"list_scenarios{suffix}",
        summary="List available demo scenarios",
    )
    def list_scenarios() -> ScenarioListResponse:
        """Return the frozen demo scenarios available for controlled demonstration."""
        raw_list = default_scenario_engine.list_scenarios()
        scenarios = [ScenarioDetailResponse(**s) for s in raw_list]
        return ScenarioListResponse(scenarios=scenarios)

    @router.get(
        "/scenarios/{scenario_id}",
        response_model=ScenarioDetailResponse,
        status_code=status.HTTP_200_OK,
        operation_id=f"get_scenario{suffix}",
        summary="Get a demo scenario definition",
    )
    def get_scenario(
        scenario_id: str = Path(description="Scenario identifier"),
    ) -> ScenarioDetailResponse:
        scenario = default_scenario_engine.get_scenario(scenario_id)
        if scenario is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"SCENARIO_NOT_FOUND: Unknown demo scenario '{scenario_id}'",
            )
        return ScenarioDetailResponse(**scenario.to_dict())

    @router.post(
        "/scenarios/{scenario_id}/start",
        response_model=ScenarioStartResponse,
        status_code=status.HTTP_202_ACCEPTED,
        operation_id=f"start_scenario{suffix}",
        summary="Start a named demo scenario",
    )
    async def start_scenario(
        scenario_id: str = Path(description="Scenario identifier"),
        speed: float = Query(default=1.0, gt=0, description="Replay speed factor"),
    ) -> ScenarioStartResponse:
        """Start a session initialized with the specified scenario fixture.
        
        The scenario engine ONLY supplies the audio fixture, call context, and
        transaction context. The real pipeline produces the risk evaluation.
        """
        runtime = get_runtime()
        try:
            result = await default_scenario_engine.start_scenario(
                scenario_id=scenario_id, runtime=runtime, speed=speed
            )
        except KeyError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"SCENARIO_NOT_FOUND: Unknown demo scenario '{scenario_id}'",
            ) from exc
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc

        return ScenarioStartResponse(**result)

    return router


router = build_router("/v1/demo", "_v1")
api_router = build_router("/api/demo", "_api")

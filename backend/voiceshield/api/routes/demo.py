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

    # Primary Cases routes
    @router.get(
        "/cases",
        response_model=ScenarioListResponse,
        status_code=status.HTTP_200_OK,
        operation_id=f"list_cases{suffix}",
        summary="List available demo cases",
    )
    def list_cases() -> ScenarioListResponse:
        raw_list = default_scenario_engine.list_scenarios()
        scenarios = [ScenarioDetailResponse(**s) for s in raw_list]
        return ScenarioListResponse(scenarios=scenarios)

    @router.get(
        "/cases/{case_id}",
        response_model=ScenarioDetailResponse,
        status_code=status.HTTP_200_OK,
        operation_id=f"get_case{suffix}",
        summary="Get a demo case definition",
    )
    def get_case(
        case_id: str = Path(description="Case identifier"),
    ) -> ScenarioDetailResponse:
        scenario = default_scenario_engine.get_scenario(case_id)
        if scenario is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"SCENARIO_NOT_FOUND: Unknown demo scenario/case '{case_id}'",
            )
        return ScenarioDetailResponse(**scenario.to_dict())

    @router.post(
        "/cases/{case_id}/start",
        response_model=ScenarioStartResponse,
        status_code=status.HTTP_202_ACCEPTED,
        operation_id=f"start_case{suffix}",
        summary="Start a named demo case",
    )
    async def start_case(
        case_id: str = Path(description="Case identifier"),
        speed: float = Query(default=1.0, gt=0, description="Replay speed factor"),
    ) -> ScenarioStartResponse:
        runtime = get_runtime()
        try:
            result = await default_scenario_engine.start_scenario(
                scenario_id=case_id, runtime=runtime, speed=speed
            )
        except KeyError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"SCENARIO_NOT_FOUND: Unknown demo scenario/case '{case_id}'",
            ) from exc
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc

        return ScenarioStartResponse(**result)

    # Scenarios aliases for test and backward compatibility
    @router.get(
        "/scenarios",
        response_model=ScenarioListResponse,
        status_code=status.HTTP_200_OK,
        operation_id=f"list_scenarios{suffix}",
        summary="List available demo scenarios",
    )
    def list_scenarios() -> ScenarioListResponse:
        return list_cases()

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
        return get_case(scenario_id)

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
        return await start_case(scenario_id, speed)

    return router


router = build_router("/v1/demo", "_v1")
api_router = build_router("/api/demo", "_api")
root_demo_router = build_router("/demo", "_root_demo")


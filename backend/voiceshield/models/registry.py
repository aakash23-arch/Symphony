"""Expert registry module (C-19).

Owns expert registration, dispatch, per-expert timeout enforcement, and the
availability report that the startup log and the health endpoint consume.

The central invariant (C-19, §22):

    One dead expert never kills the pipeline, and never becomes a default
    probability.

Every failure path - unregistered, unavailable, timed out, raised - produces an
ExpertResult with ``p=None`` and an explicit status. There is no code path in
this module that invents a number.
"""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional

from voiceshield.config import settings
from voiceshield.contracts import ExpertResult, ExpertStatus
from voiceshield.obs.logging import get_logger
from voiceshield.signal_processing import FeatureBundle

from .base import Expert

logger = get_logger("voiceshield.models.registry")

# The six contract slots, in EvidenceVector field order. score_all always returns
# exactly these, so downstream indexing is total and a missing expert is visible
# as MODEL_UNAVAILABLE rather than as an absent entry.
ALL_EXPERT_IDS: List[str] = ["E1", "E2", "E3", "E4", "E5", "E6"]

# Experts deferred by scope decision rather than by missing weights (B1/B2).
DEFERRED_EXPERT_IDS = {"E5", "E6"}


class ExpertRegistry:
    """Central registry managing expert lifecycle, dispatch, and availability telemetry."""

    def __init__(self, max_workers: Optional[int] = None) -> None:
        self._experts: Dict[str, Expert] = {}
        self._executor: Optional[ThreadPoolExecutor] = None
        self._max_workers = max_workers or settings.expert_max_workers
        self._timeout_counts: Dict[str, int] = {}

    # --- Registration ----------------------------------------------------------

    def register(self, expert: Expert) -> None:
        """Register an expert instance."""
        self._experts[expert.expert_id] = expert

    def get(self, expert_id: str) -> Optional[Expert]:
        """Retrieve an expert by ID."""
        return self._experts.get(expert_id)

    def list_expert_ids(self) -> List[str]:
        """List all registered expert IDs."""
        return list(self._experts.keys())

    def clear(self) -> None:
        """Remove all registered experts (used by tests)."""
        self._experts.clear()
        self._timeout_counts.clear()

    @property
    def executor(self) -> ThreadPoolExecutor:
        """Lazily-created inference thread pool."""
        if self._executor is None:
            self._executor = ThreadPoolExecutor(
                max_workers=self._max_workers, thread_name_prefix="vs-expert"
            )
        return self._executor

    def shutdown(self) -> None:
        """Release the inference thread pool."""
        if self._executor is not None:
            self._executor.shutdown(wait=False)
            self._executor = None

    # --- Availability ----------------------------------------------------------

    def get_availability_report(self) -> Dict[str, Dict[str, str]]:
        """Return availability status for all known experts (E1..E6)."""
        report: Dict[str, Dict[str, str]] = {}
        for eid in ALL_EXPERT_IDS:
            expert = self._experts.get(eid)

            if expert is None:
                report[eid] = {
                    "status": (
                        ExpertStatus.DEFERRED.value
                        if eid in DEFERRED_EXPERT_IDS
                        else ExpertStatus.MODEL_UNAVAILABLE.value
                    ),
                    "reason": (
                        "Deferred in internal demo (B1/B2)"
                        if eid in DEFERRED_EXPERT_IDS
                        else "Expert not registered"
                    ),
                }
                continue

            try:
                available = expert.is_available()
            except NotImplementedError:
                report[eid] = {
                    "status": ExpertStatus.MODEL_UNAVAILABLE.value,
                    "reason": "Weights not loaded / interface uninstantiated",
                    "version": expert.version,
                }
                continue

            if available:
                status = ExpertStatus.OK.value
            elif eid in DEFERRED_EXPERT_IDS:
                status = ExpertStatus.DEFERRED.value
            else:
                status = ExpertStatus.MODEL_UNAVAILABLE.value

            entry = {"status": status, "version": expert.version}
            reason = getattr(expert, "unavailable_reason", None)
            if not available and reason:
                entry["reason"] = str(reason)
            model_id = getattr(expert, "model_id", None)
            if model_id:
                entry["model_id"] = str(model_id)
            report[eid] = entry

        return report

    def log_availability_report(self) -> Dict[str, Dict[str, str]]:
        """Log which experts are live and which are not (C-27).

        C-27 requires the startup log to state plainly which experts are
        unavailable: startup must not silently proceed as if all six were live.
        """
        report = self.get_availability_report()

        for eid in ALL_EXPERT_IDS:
            entry = report[eid]
            logger.info(
                f"expert {eid}: {entry['status']}"
                + (f" ({entry['reason']})" if entry.get("reason") else ""),
                extra={"extra_fields": {"expert_id": eid, **entry}},
            )

        live = [e for e in ALL_EXPERT_IDS if report[e]["status"] == ExpertStatus.OK.value]
        down = [e for e in ALL_EXPERT_IDS if report[e]["status"] != ExpertStatus.OK.value]

        if down:
            logger.warning(
                f"{len(live)}/{len(ALL_EXPERT_IDS)} experts live; "
                f"unavailable or deferred: {', '.join(down)}",
                extra={"extra_fields": {"live": live, "unavailable": down}},
            )
        else:  # pragma: no cover - not reachable in this build
            logger.info("all experts live")

        return report

    # --- Dispatch --------------------------------------------------------------

    def _synthetic_unavailable(self, expert_id: str) -> ExpertResult:
        """Result for a slot with no registered expert. Never carries a score."""
        return ExpertResult(
            expert_id=expert_id,
            status=(
                ExpertStatus.DEFERRED
                if expert_id in DEFERRED_EXPERT_IDS
                else ExpertStatus.MODEL_UNAVAILABLE
            ),
            p=None,
            confidence=None,
            latency_ms=0.0,
        )

    async def _score_one(self, expert: Expert, bundle: FeatureBundle) -> ExpertResult:
        """Run one expert under its time budget, converting any failure to a status.

        TIMEOUT LIMITATION, STATED HONESTLY: torch inference is blocking C++ that
        does not observe asyncio cancellation. When wait_for fires we stop
        AWAITING the task and return TIMEOUT immediately, but the worker thread
        keeps running to completion and cannot be killed. The thread pool is
        therefore sized with slack and repeated timeouts are counted below, so
        pool exhaustion shows up in the logs instead of manifesting as a mystery
        stall. Do not rewrite this comment to claim the work is cancelled.
        """
        timeout_s = max(0.001, settings.expert_timeout_ms / 1000.0)
        try:
            return await asyncio.wait_for(expert.score(bundle), timeout=timeout_s)
        except asyncio.TimeoutError:
            self._timeout_counts[expert.expert_id] = (
                self._timeout_counts.get(expert.expert_id, 0) + 1
            )
            logger.warning(
                f"expert {expert.expert_id} exceeded its time budget",
                extra={
                    "extra_fields": {
                        "expert_id": expert.expert_id,
                        "timeout_ms": settings.expert_timeout_ms,
                        "timeout_count": self._timeout_counts[expert.expert_id],
                        "note": "worker thread continues; it cannot be cancelled",
                    }
                },
            )
            return ExpertResult(
                expert_id=expert.expert_id,
                status=ExpertStatus.TIMEOUT,
                p=None,
                confidence=None,
                latency_ms=float(settings.expert_timeout_ms),
            )
        except Exception as exc:
            # Deliberately broad: an expert raising anything at all must not take
            # down the other five or the call. The detail is logged, not placed
            # in the contract (ExpertResult has no field for it).
            logger.error(
                f"expert {expert.expert_id} raised during inference",
                extra={
                    "extra_fields": {
                        "expert_id": expert.expert_id,
                        "error_type": type(exc).__name__,
                        "detail": str(exc)[:200],
                    }
                },
            )
            return ExpertResult(
                expert_id=expert.expert_id,
                status=ExpertStatus.ERROR,
                p=None,
                confidence=None,
                latency_ms=0.0,
            )

    async def score_all(self, bundle: FeatureBundle) -> List[ExpertResult]:
        """Run all experts against a feature bundle, returning exactly six results.

        Every expert receives the SAME bundle object and no expert sees another's
        output (§6.1 evidence independence). Results are returned in E1..E6 order
        regardless of registration order or failures.
        """
        if bundle is None:
            # A None bundle is a programming error upstream. Returning six
            # abstentions would hide it; raising surfaces it at the seam.
            raise ValueError("score_all requires a FeatureBundle, got None")

        registered = [(eid, self._experts[eid]) for eid in ALL_EXPERT_IDS if eid in self._experts]

        gathered = await asyncio.gather(
            *(self._score_one(expert, bundle) for _, expert in registered),
            return_exceptions=True,
        )

        by_id: Dict[str, ExpertResult] = {}
        for (eid, _), outcome in zip(registered, gathered):
            if isinstance(outcome, ExpertResult):
                by_id[eid] = outcome
            else:
                # _score_one already traps exceptions; this covers anything that
                # escapes it (e.g. cancellation) so the slot still gets a result.
                logger.error(
                    f"expert {eid} dispatch failed",
                    extra={"extra_fields": {"expert_id": eid, "error_type": type(outcome).__name__}},
                )
                by_id[eid] = ExpertResult(
                    expert_id=eid, status=ExpertStatus.ERROR, p=None, confidence=None
                )

        return [by_id.get(eid) or self._synthetic_unavailable(eid) for eid in ALL_EXPERT_IDS]


# Singleton instance
expert_registry = ExpertRegistry()

"""Context ingestion and scaling interface (C-36, C-37).

L4-front. Takes an untrusted raw context payload from the caller (in the demo,
the scenario engine; in production, a CRM/telephony bus) and turns it into a
validated ``ContextVector`` where every field carries explicit provenance.

Provenance is the point of this module. A field that was never supplied must
come out ``UNAVAILABLE``, never as a confident default - the risk engine reads
provenance to decide how much of its evidence budget it actually has, and a
silently-defaulted field would let it claim certainty it has not earned.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Optional

from voiceshield.contracts import (
    BehaviourContext,
    BeneficiaryNovelty,
    CallSource,
    ContextVector,
    EnrollmentStatus,
    IdentityContext,
    KnownContactStatus,
    NumberContext,
    ProvenanceType,
    SessionHistory,
    TechnicalContext,
    TransactionContext,
    VoipMobileIndicator,
    WorkflowState,
)
from voiceshield.obs.logging import get_logger

logger = get_logger("voiceshield.context.context_engine")

#: Section name -> sub-model, used to walk fields for provenance marking.
_SECTIONS = {
    "identity": IdentityContext,
    "number": NumberContext,
    "transaction": TransactionContext,
    "behaviour": BehaviourContext,
    "technical": TechnicalContext,
    "history": SessionHistory,
}

#: History counters default to 0 rather than None, so "absent" cannot be read
#: off the value alone - provenance is the only reliable signal for them.
_COUNTER_FIELDS = {"prior_step_up_failures", "prior_step_up_successes", "prior_escalations"}


class ContextEngine(ABC):
    """Abstract interface for contextual telemetry ingestion and risk factor scaling."""

    @abstractmethod
    def ingest_context(self, session_id: str, raw_context: Dict[str, Any]) -> ContextVector:
        """Parse, validate, and assign SIMULATED provenance to context payload."""
        raise NotImplementedError("ContextEngine.ingest_context is not implemented yet")

    @abstractmethod
    def compute_context_modifier(self, context: ContextVector) -> float:
        """Compute contextual risk scaling modifier."""
        raise NotImplementedError("ContextEngine.compute_context_modifier is not implemented yet")


def _coerce_enum(enum_cls, value, default):
    """Best-effort enum coercion; unrecognised input falls back to the default.

    Deliberately lenient: a malformed CRM field should degrade the assessment
    into UNKNOWN, not drop the call.
    """
    if value is None:
        return default
    if isinstance(value, enum_cls):
        return value
    try:
        return enum_cls(str(value).strip().upper())
    except ValueError:
        logger.warning(
            "unrecognised context enum value; falling back to default",
            extra={"extra_fields": {"enum": enum_cls.__name__, "value": str(value)}},
        )
        return default


def _coerce_decimal(value) -> Optional[Decimal]:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        logger.warning(
            "unparseable transaction amount; treating as unavailable",
            extra={"extra_fields": {"value": str(value)}},
        )
        return None


def _coerce_bool(value) -> Optional[bool]:
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, str):
        low = value.strip().lower()
        if low in ("true", "yes", "1"):
            return True
        if low in ("false", "no", "0"):
            return False
        return None
    if isinstance(value, (int, float)):
        return bool(value)
    return None


def _coerce_number(value, cast):
    if value is None:
        return None
    try:
        return cast(value)
    except (TypeError, ValueError):
        return None


class StandardContextEngine(ContextEngine):
    """Concrete context engine (C-36, C-37).

    ``default_provenance`` is SIMULATED because in the demo every context field
    originates from the scenario engine rather than a real bank system, and the
    UI is required to say so. A deployment reading a live CRM would construct
    this with ``ProvenanceType.REAL``.
    """

    def __init__(self, default_provenance: ProvenanceType = ProvenanceType.SIMULATED):
        self._default_provenance = default_provenance

    @property
    def default_provenance(self) -> ProvenanceType:
        return self._default_provenance

    def ingest_context(self, session_id: str, raw_context: Dict[str, Any]) -> ContextVector:
        """Parse, validate, and assign provenance to a raw context payload.

        Accepts either a nested payload (``{"identity": {...}}``) or a flat one
        (``{"claimed_identity": ...}``); scenario files are written both ways.
        """
        raw = dict(raw_context or {})
        provenance: Dict[str, ProvenanceType] = {}

        def section(name: str) -> Dict[str, Any]:
            """Collect a section's fields from either the nested or flat payload."""
            nested = raw.get(name)
            merged: Dict[str, Any] = dict(nested) if isinstance(nested, dict) else {}
            for field in _SECTIONS[name].model_fields:
                if merged.get(field) is None and field in raw:
                    merged[field] = raw[field]
            return merged

        def mark(name: str, supplied: Dict[str, Any]) -> None:
            """Record per-field provenance: supplied -> default, absent -> UNAVAILABLE."""
            for field in _SECTIONS[name].model_fields:
                provenance[f"{name}.{field}"] = (
                    self._default_provenance
                    if supplied.get(field) is not None
                    else ProvenanceType.UNAVAILABLE
                )

        ident_raw = section("identity")
        identity = IdentityContext(
            claimed_identity=ident_raw.get("claimed_identity"),
            verified_identity=ident_raw.get("verified_identity"),
            enrollment_status=_coerce_enum(
                EnrollmentStatus, ident_raw.get("enrollment_status"), EnrollmentStatus.UNKNOWN
            ),
            cnap_state=ident_raw.get("cnap_state"),
            identity_mismatch=_coerce_bool(ident_raw.get("identity_mismatch")),
            known_contact=_coerce_enum(
                KnownContactStatus, ident_raw.get("known_contact"), KnownContactStatus.UNKNOWN
            ),
        )
        mark("identity", ident_raw)

        num_raw = section("number")
        number = NumberContext(
            reputation=_coerce_number(num_raw.get("reputation"), float),
            age_days=_coerce_number(num_raw.get("age_days"), int),
            known_fraud_status=_coerce_bool(num_raw.get("known_fraud_status")),
            port_history=_coerce_bool(num_raw.get("port_history")),
        )
        mark("number", num_raw)

        txn_raw = section("transaction")
        transaction = TransactionContext(
            amount=_coerce_decimal(txn_raw.get("amount")),
            currency=txn_raw.get("currency"),
            transaction_type=txn_raw.get("transaction_type"),
            beneficiary_novelty=_coerce_enum(
                BeneficiaryNovelty, txn_raw.get("beneficiary_novelty"), BeneficiaryNovelty.UNKNOWN
            ),
            velocity=_coerce_number(txn_raw.get("velocity"), float),
            historical_deviation=_coerce_number(txn_raw.get("historical_deviation"), float),
            sensitive_action=txn_raw.get("sensitive_action"),
        )
        mark("transaction", txn_raw)

        beh_raw = section("behaviour")
        behaviour = BehaviourContext(
            urgency=_coerce_bool(beh_raw.get("urgency")),
            secrecy=_coerce_bool(beh_raw.get("secrecy")),
            callback_refusal=_coerce_bool(beh_raw.get("callback_refusal")),
            verification_bypass=_coerce_bool(beh_raw.get("verification_bypass")),
            unusual_request=_coerce_bool(beh_raw.get("unusual_request")),
            prior_fraud_indicator=_coerce_bool(beh_raw.get("prior_fraud_indicator")),
            workflow_state=_coerce_enum(
                WorkflowState, beh_raw.get("workflow_state"), WorkflowState.NONE
            ),
        )
        mark("behaviour", beh_raw)

        tech_raw = section("technical")
        technical = TechnicalContext(
            device_signal=tech_raw.get("device_signal"),
            network_origin=tech_raw.get("network_origin"),
            voip_mobile_indicator=_coerce_enum(
                VoipMobileIndicator, tech_raw.get("voip_mobile_indicator"), VoipMobileIndicator.UNKNOWN
            ),
            call_source=_coerce_enum(CallSource, tech_raw.get("call_source"), CallSource.UNKNOWN),
            codec=tech_raw.get("codec"),
        )
        mark("technical", tech_raw)

        hist_raw = section("history")
        history = SessionHistory(
            prior_sessions=_coerce_number(hist_raw.get("prior_sessions"), int),
            prior_step_up_failures=_coerce_number(hist_raw.get("prior_step_up_failures"), int) or 0,
            prior_step_up_successes=_coerce_number(hist_raw.get("prior_step_up_successes"), int) or 0,
            prior_escalations=_coerce_number(hist_raw.get("prior_escalations"), int) or 0,
            session_duration_s=_coerce_number(hist_raw.get("session_duration_s"), float),
            repeat_caller=_coerce_bool(hist_raw.get("repeat_caller")),
        )
        mark("history", hist_raw)

        language = raw.get("language") or "UNKNOWN"
        provenance["language"] = (
            self._default_provenance if raw.get("language") else ProvenanceType.UNAVAILABLE
        )

        return ContextVector(
            session_id=session_id,
            identity=identity,
            number=number,
            transaction=transaction,
            behaviour=behaviour,
            technical=technical,
            history=history,
            language=str(language),
            provenance=provenance,
            timestamp=datetime.now(timezone.utc),
        )

    def context_completeness(self, context: ContextVector) -> float:
        """Fraction of context fields actually supplied, in [0, 1].

        The risk engine discounts its own confidence by this: a verdict built on
        two known fields out of thirty is not a confident verdict.
        """
        prov = context.provenance
        if not prov:
            return 0.0
        known = sum(1 for p in prov.values() if p != ProvenanceType.UNAVAILABLE)
        return known / len(prov)

    def compute_context_modifier(self, context: ContextVector) -> float:
        """Compute a coarse contextual risk multiplier in [0.5, 2.0] (C-37).

        Retained for the C-37 interface and for callers that want a single
        summary number. The risk engine does NOT score with it - it uses the
        additive per-factor breakdown in :mod:`voiceshield.risk.scoring`,
        because one opaque multiplier cannot be explained to an auditor.
        """
        modifier = 1.0
        if context.behaviour.prior_fraud_indicator:
            modifier *= 1.4
        if context.number.known_fraud_status:
            modifier *= 1.4
        if context.identity.identity_mismatch:
            modifier *= 1.3
        if context.identity.known_contact == KnownContactStatus.KNOWN_CONTACT:
            modifier *= 0.85
        if context.technical.call_source == CallSource.OUTBOUND_CALLBACK:
            modifier *= 0.8
        return max(0.5, min(2.0, modifier))

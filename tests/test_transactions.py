"""Tests for the DEMO TRANSACTION ENVIRONMENT simulator and its API.

    THIS IS NOT A REAL BANKING INTEGRATION.

Covers every legal transition, every illegal transition, the audit trail, the
risk engine interface, determinism, and the labelling that keeps the demo from
reading as a real banking integration.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from itertools import count

import pytest
from fastapi import status

from voiceshield.contracts import (
    DEMO_ENVIRONMENT_LABEL,
    AuditEventType,
    BeneficiaryNovelty,
    PolicyAction,
    TransactionState,
)
from voiceshield.contracts.transaction import LEGAL_TRANSITIONS, TERMINAL_STATES
from voiceshield.transactions import (
    RISK_ACTION_TO_STATE,
    IllegalTransactionTransition,
    InvalidTransactionAmount,
    TransactionNotFound,
    TransactionNotHeld,
    TransactionSimulator,
    VerificationRequired,
)

ALL_STATES = list(TransactionState)


@pytest.fixture
def sim():
    """A simulator with an injected clock and id factory, so tests are exact."""
    ticker = count()
    base = datetime(2026, 8, 28, 12, 0, 0, tzinfo=timezone.utc)
    ids = count()
    return TransactionSimulator(
        clock=lambda: base + timedelta(seconds=next(ticker)),
        id_factory=lambda: f"id-{next(ids):04d}",
    )


@pytest.fixture
def txn(sim):
    """A freshly created PENDING transaction."""
    return sim.create_transaction(
        caller_identity="alice",
        amount="5000.00",
        beneficiary="acme-supplies",
        beneficiary_novelty=BeneficiaryNovelty.NEW,
        transaction_type="WIRE_TRANSFER",
        session_id="sess-1",
    )


def drive_to(sim, state: TransactionState, *, identity="alice") -> str:
    """Create a transaction and drive it to ``state`` by legal edges only."""
    t = sim.create_transaction(caller_identity=identity, amount="100", beneficiary="b")
    tid = t.transaction_id
    if state == TransactionState.PENDING:
        return tid
    if state == TransactionState.HELD:
        sim.hold_transaction(tid, reason="setup")
        return tid
    sim.update_state(tid, state, reason="setup")
    return tid


@pytest.fixture
def api(client):
    """The FastAPI test client with a clean transaction store."""
    from voiceshield.api.runtime import get_runtime

    get_runtime().transactions.reset()
    return client


# =============================================================================
# Demo labelling — this must never read as a real banking integration
# =============================================================================


class TestDemoLabelling:
    def test_the_transaction_carries_the_environment_label(self, txn):
        assert txn.environment == DEMO_ENVIRONMENT_LABEL
        assert txn.environment == "DEMO TRANSACTION ENVIRONMENT"

    def test_the_label_survives_serialisation(self, txn):
        """A docstring would not reach the UI; the field does."""
        payload = txn.model_dump_json()
        assert "DEMO TRANSACTION ENVIRONMENT" in payload

    def test_the_disclaimer_travels_with_the_record(self, txn):
        assert "no real funds move" in txn.disclaimer.lower()
        assert "no external banking system" in txn.disclaimer.lower()

    def test_every_audit_event_is_labelled(self, sim, txn):
        sim.hold_transaction(txn.transaction_id, reason="check")
        for event in sim.get_audit_trail(txn.transaction_id):
            assert event.environment == DEMO_ENVIRONMENT_LABEL

    def test_no_real_banking_fields_exist_on_the_contract(self, txn):
        """Absent by design: inventing them would make this look like a payment."""
        fields = set(type(txn).model_fields)
        for banned in ("account_number", "iban", "sort_code", "routing_number",
                       "card_number", "swift", "balance"):
            assert banned not in fields

    def test_api_responses_carry_the_label(self, api):
        response = api.post("/v1/demo/transactions", json={
            "caller_identity": "alice", "amount": "100", "beneficiary": "b",
        })
        body = response.json()
        assert body["environment"] == DEMO_ENVIRONMENT_LABEL
        assert "no real funds move" in body["disclaimer"].lower()


# =============================================================================
# Creation
# =============================================================================


class TestCreation:
    def test_a_new_transaction_starts_pending(self, txn):
        """There is no path that creates an already-approved transaction."""
        assert txn.state == TransactionState.PENDING

    def test_all_required_attributes_are_recorded(self, txn):
        assert txn.caller_identity == "alice"
        assert txn.amount == Decimal("5000.00")
        assert txn.beneficiary == "acme-supplies"
        assert txn.beneficiary_novelty == BeneficiaryNovelty.NEW
        assert txn.session_id == "sess-1"

    def test_creation_emits_an_audit_event(self, sim, txn):
        trail = sim.get_audit_trail(txn.transaction_id)
        assert len(trail) == 1
        assert trail[0].event_type == AuditEventType.TRANSACTION_CREATED
        assert trail[0].to_state == TransactionState.PENDING

    @pytest.mark.parametrize("bad", ["0", "-1", "-0.01"])
    def test_a_non_positive_amount_is_refused(self, sim, bad):
        with pytest.raises(InvalidTransactionAmount):
            sim.create_transaction(caller_identity="a", amount=bad, beneficiary="b")

    def test_an_unparseable_amount_is_refused(self, sim):
        with pytest.raises(InvalidTransactionAmount):
            sim.create_transaction(caller_identity="a", amount="not-money", beneficiary="b")

    def test_a_duplicate_id_is_refused(self, sim):
        sim.create_transaction(caller_identity="a", amount="1", beneficiary="b", transaction_id="fixed")
        with pytest.raises(IllegalTransactionTransition):
            sim.create_transaction(caller_identity="a", amount="1", beneficiary="b", transaction_id="fixed")

    def test_amounts_keep_decimal_precision(self, sim):
        """Float arithmetic on money is how cent-level drift gets introduced."""
        t = sim.create_transaction(caller_identity="a", amount="0.07", beneficiary="b")
        assert t.amount == Decimal("0.07")
        assert isinstance(t.amount, Decimal)


# =============================================================================
# Retrieval
# =============================================================================


class TestRetrieval:
    def test_a_transaction_can_be_read_back(self, sim, txn):
        assert sim.get_transaction(txn.transaction_id).transaction_id == txn.transaction_id

    def test_an_unknown_id_raises_not_found(self, sim):
        with pytest.raises(TransactionNotFound):
            sim.get_transaction("no-such-transaction")

    def test_an_audit_trail_for_an_unknown_id_raises(self, sim):
        with pytest.raises(TransactionNotFound):
            sim.get_audit_trail("no-such-transaction")

    def test_transactions_can_be_filtered_by_session(self, sim):
        sim.create_transaction(caller_identity="a", amount="1", beneficiary="b", session_id="s1")
        sim.create_transaction(caller_identity="a", amount="1", beneficiary="b", session_id="s2")
        assert len(sim.list_transactions(session_id="s1")) == 1
        assert len(sim.list_transactions()) == 2


# =============================================================================
# Legal state transitions — every declared edge
# =============================================================================


class TestLegalTransitions:
    @pytest.mark.parametrize("target", sorted(LEGAL_TRANSITIONS[TransactionState.PENDING],
                                              key=lambda s: s.value))
    def test_every_edge_out_of_pending_is_permitted(self, sim, target):
        tid = drive_to(sim, TransactionState.PENDING)
        assert sim.update_state(tid, target, reason="t").state == target

    @pytest.mark.parametrize("target", sorted(LEGAL_TRANSITIONS[TransactionState.HELD],
                                              key=lambda s: s.value))
    def test_every_edge_out_of_held_is_permitted(self, sim, target):
        tid = drive_to(sim, TransactionState.HELD)
        assert sim.update_state(tid, target, reason="t").state == target

    def test_the_graph_covers_every_state(self):
        """A state missing from the graph would raise on its first transition."""
        assert set(LEGAL_TRANSITIONS) == set(ALL_STATES)

    def test_terminal_states_have_no_outgoing_edges(self):
        for state in TERMINAL_STATES:
            assert LEGAL_TRANSITIONS[state] == set()

    def test_approved_is_terminal(self):
        """An executed payment is reversed by a second entry, not by an edit."""
        assert TransactionState.APPROVED in TERMINAL_STATES

    def test_a_legal_transition_updates_the_timestamp(self, sim, txn):
        before = txn.updated_at
        after = sim.update_state(txn.transaction_id, TransactionState.APPROVED, reason="t")
        assert after.updated_at > before


# =============================================================================
# Invalid state transitions — every edge NOT in the graph
# =============================================================================


class TestInvalidTransitions:
    @pytest.mark.parametrize(
        "origin,target",
        [
            (o, t)
            for o in ALL_STATES
            for t in ALL_STATES
            if t not in LEGAL_TRANSITIONS[o]
        ],
    )
    def test_every_undeclared_edge_is_refused(self, sim, origin, target):
        """Exhaustive: the full state x state matrix minus the legal edges."""
        tid = drive_to(sim, origin)
        with pytest.raises(IllegalTransactionTransition):
            sim.update_state(tid, target, reason="attempt")

    @pytest.mark.parametrize("origin", sorted(TERMINAL_STATES, key=lambda s: s.value))
    def test_nothing_escapes_a_terminal_state(self, sim, origin):
        tid = drive_to(sim, origin)
        for target in ALL_STATES:
            with pytest.raises(IllegalTransactionTransition):
                sim.update_state(tid, target, reason="attempt")

    def test_a_self_transition_is_refused(self, sim, txn):
        """PENDING -> PENDING is not an edge; it would be a silent no-op."""
        with pytest.raises(IllegalTransactionTransition):
            sim.update_state(txn.transaction_id, TransactionState.PENDING, reason="t")

    def test_a_refused_transition_leaves_the_state_untouched(self, sim):
        tid = drive_to(sim, TransactionState.APPROVED)
        with pytest.raises(IllegalTransactionTransition):
            sim.update_state(tid, TransactionState.HELD, reason="t")
        assert sim.get_transaction(tid).state == TransactionState.APPROVED

    def test_the_error_names_the_attempted_edge(self, sim):
        tid = drive_to(sim, TransactionState.REJECTED)
        with pytest.raises(IllegalTransactionTransition) as exc:
            sim.update_state(tid, TransactionState.APPROVED, reason="t")
        assert exc.value.from_state == "REJECTED"
        assert exc.value.to_state == "APPROVED"
        assert exc.value.status_code == 409

    def test_a_terminal_refusal_is_coded_distinctly(self, sim):
        """'Already resolved' and 'not a legal edge' are different diagnoses."""
        tid = drive_to(sim, TransactionState.CANCELLED)
        with pytest.raises(IllegalTransactionTransition) as exc:
            sim.update_state(tid, TransactionState.HELD, reason="t")
        assert exc.value.code == "TRANSACTION_TERMINAL"

    def test_a_transition_on_an_unknown_transaction_raises_not_found(self, sim):
        with pytest.raises(TransactionNotFound):
            sim.update_state("ghost", TransactionState.APPROVED, reason="t")


# =============================================================================
# Hold
# =============================================================================


class TestHold:
    def test_a_pending_transaction_can_be_held(self, sim, txn):
        held = sim.hold_transaction(txn.transaction_id, reason="voice risk")
        assert held.state == TransactionState.HELD
        assert held.is_held
        assert held.hold_reason == "voice risk"

    def test_holding_emits_a_hold_event(self, sim, txn):
        sim.hold_transaction(txn.transaction_id, reason="voice risk")
        kinds = [e.event_type for e in sim.get_audit_trail(txn.transaction_id)]
        assert AuditEventType.HOLD_PLACED in kinds

    def test_holding_twice_is_idempotent(self, sim, txn):
        """Two risk updates both concluding HOLD is normal, not an error."""
        sim.hold_transaction(txn.transaction_id, reason="first")
        again = sim.hold_transaction(txn.transaction_id, reason="second")
        assert again.state == TransactionState.HELD

    def test_the_repeat_hold_is_still_audited(self, sim, txn):
        sim.hold_transaction(txn.transaction_id, reason="first")
        before = len(sim.get_audit_trail(txn.transaction_id))
        sim.hold_transaction(txn.transaction_id, reason="second")
        after = sim.get_audit_trail(txn.transaction_id)
        assert len(after) == before + 1
        assert "HOLD_ALREADY_ACTIVE" in after[-1].reason_codes

    @pytest.mark.parametrize("origin", sorted(TERMINAL_STATES, key=lambda s: s.value))
    def test_a_resolved_transaction_cannot_be_held(self, sim, origin):
        tid = drive_to(sim, origin)
        with pytest.raises(IllegalTransactionTransition):
            sim.hold_transaction(tid, reason="too late")


# =============================================================================
# Release after verification
# =============================================================================


class TestRelease:
    def test_a_held_transaction_releases_to_approved(self, sim, txn):
        sim.hold_transaction(txn.transaction_id, reason="risk")
        released = sim.release_transaction(txn.transaction_id, "CALLBACK-8891")
        assert released.state == TransactionState.APPROVED
        assert released.verification_reference == "CALLBACK-8891"
        assert released.hold_reason is None

    def test_a_failed_verification_releases_to_rejected(self, sim, txn):
        sim.hold_transaction(txn.transaction_id, reason="risk")
        released = sim.release_transaction(txn.transaction_id, "CALLBACK-FAILED", approve=False)
        assert released.state == TransactionState.REJECTED

    def test_release_requires_a_verification_reference(self, sim, txn):
        """The one operation that undoes a protective decision must say why."""
        sim.hold_transaction(txn.transaction_id, reason="risk")
        with pytest.raises(VerificationRequired):
            sim.release_transaction(txn.transaction_id, "")

    def test_a_whitespace_reference_does_not_count(self, sim, txn):
        sim.hold_transaction(txn.transaction_id, reason="risk")
        with pytest.raises(VerificationRequired):
            sim.release_transaction(txn.transaction_id, "   ")

    def test_a_refused_release_leaves_the_hold_in_place(self, sim, txn):
        sim.hold_transaction(txn.transaction_id, reason="risk")
        with pytest.raises(VerificationRequired):
            sim.release_transaction(txn.transaction_id, "")
        assert sim.get_transaction(txn.transaction_id).state == TransactionState.HELD

    def test_releasing_a_transaction_that_is_not_held_is_refused(self, sim, txn):
        with pytest.raises(TransactionNotHeld):
            sim.release_transaction(txn.transaction_id, "CALLBACK-1")

    def test_the_verification_is_audited_before_the_release(self, sim, txn):
        """Order matters: the justification must precede the act it justifies."""
        sim.hold_transaction(txn.transaction_id, reason="risk")
        sim.release_transaction(txn.transaction_id, "CALLBACK-8891")
        kinds = [e.event_type for e in sim.get_audit_trail(txn.transaction_id)]
        assert kinds.index(AuditEventType.VERIFICATION_RECORDED) < kinds.index(
            AuditEventType.HOLD_RELEASED
        )

    def test_the_reference_appears_in_the_trail(self, sim, txn):
        sim.hold_transaction(txn.transaction_id, reason="risk")
        sim.release_transaction(txn.transaction_id, "CALLBACK-8891")
        assert any("CALLBACK-8891" in e.reason for e in sim.get_audit_trail(txn.transaction_id))

    def test_a_released_transaction_cannot_be_re_held(self, sim, txn):
        """Approval is terminal, so a release cannot silently slide back."""
        sim.hold_transaction(txn.transaction_id, reason="risk")
        sim.release_transaction(txn.transaction_id, "CALLBACK-1")
        with pytest.raises(IllegalTransactionTransition):
            sim.hold_transaction(txn.transaction_id, reason="again")


# =============================================================================
# Risk engine interface
# =============================================================================


class TestRiskActions:
    def test_the_four_required_actions_are_all_mapped(self):
        for action in (PolicyAction.HOLD, PolicyAction.STEP_UP,
                       PolicyAction.ESCALATE, PolicyAction.ALLOW):
            assert action in RISK_ACTION_TO_STATE

    def test_hold_moves_the_transaction_to_held(self, sim, txn):
        result = sim.request_risk_action(txn.transaction_id, PolicyAction.HOLD)
        assert result.state == TransactionState.HELD

    def test_escalate_also_holds(self, sim, txn):
        result = sim.request_risk_action(txn.transaction_id, PolicyAction.ESCALATE)
        assert result.state == TransactionState.HELD

    def test_allow_does_not_approve(self, sim, txn):
        """ALLOW is the absence of an objection, not an instruction to execute.

        Auto-approving here would hand the risk engine the authority to move
        money, which is exactly what §9.3 withholds from it.
        """
        result = sim.request_risk_action(txn.transaction_id, PolicyAction.ALLOW)
        assert result.state == TransactionState.PENDING

    def test_step_up_does_not_move_the_state_machine(self, sim, txn):
        """A request for more evidence about the caller is not yet a verdict."""
        result = sim.request_risk_action(txn.transaction_id, PolicyAction.STEP_UP)
        assert result.state == TransactionState.PENDING

    @pytest.mark.parametrize("action", [PolicyAction.ALLOW, PolicyAction.STEP_UP,
                                        PolicyAction.HOLD, PolicyAction.ESCALATE])
    def test_every_risk_action_is_audited(self, sim, txn, action):
        sim.request_risk_action(txn.transaction_id, action)
        trail = sim.get_audit_trail(txn.transaction_id)
        requested = [e for e in trail if e.event_type == AuditEventType.RISK_ACTION_REQUESTED]
        assert requested
        assert requested[-1].risk_action == action
        assert requested[-1].actor == "RISK_ENGINE"

    def test_risk_actions_accumulate_on_the_transaction(self, sim, txn):
        """Held-released-held is a different story from held once."""
        sim.request_risk_action(txn.transaction_id, PolicyAction.STEP_UP)
        result = sim.request_risk_action(txn.transaction_id, PolicyAction.HOLD)
        assert result.risk_actions == [PolicyAction.STEP_UP, PolicyAction.HOLD]

    def test_a_late_hold_on_a_resolved_transaction_is_audited_not_raised(self, sim, txn):
        """A risk update arriving after an operator resolved the case is expected."""
        sim.update_state(txn.transaction_id, TransactionState.APPROVED, reason="operator")
        result = sim.request_risk_action(txn.transaction_id, PolicyAction.HOLD)
        assert result.state == TransactionState.APPROVED
        trail = sim.get_audit_trail(txn.transaction_id)
        assert any("TRANSACTION_TERMINAL" in e.reason_codes for e in trail)

    def test_a_risk_action_on_an_unknown_transaction_raises(self, sim):
        with pytest.raises(TransactionNotFound):
            sim.request_risk_action("ghost", PolicyAction.HOLD)


# =============================================================================
# Audit trail
# =============================================================================


class TestAuditTrail:
    def test_every_state_change_produces_an_event(self, sim, txn):
        before = len(sim.get_audit_trail(txn.transaction_id))
        sim.update_state(txn.transaction_id, TransactionState.CANCELLED, reason="customer")
        assert len(sim.get_audit_trail(txn.transaction_id)) == before + 1

    def test_refused_changes_are_recorded_too(self, sim):
        """An attacker probing for a way out of HELD leaves exactly this trace."""
        tid = drive_to(sim, TransactionState.REJECTED)
        before = len(sim.get_audit_trail(tid))
        with pytest.raises(IllegalTransactionTransition):
            sim.update_state(tid, TransactionState.APPROVED, reason="probe")
        trail = sim.get_audit_trail(tid)
        assert len(trail) == before + 1
        assert trail[-1].event_type == AuditEventType.TRANSITION_REJECTED

    def test_sequence_numbers_are_monotonic_and_gapless(self, sim, txn):
        sim.request_risk_action(txn.transaction_id, PolicyAction.HOLD)
        sim.release_transaction(txn.transaction_id, "CALLBACK-1")
        sequences = [e.sequence for e in sim.get_audit_trail(txn.transaction_id)]
        assert sequences == list(range(len(sequences)))

    def test_events_record_both_ends_of_the_edge(self, sim, txn):
        sim.update_state(txn.transaction_id, TransactionState.APPROVED, reason="ok")
        last = sim.get_audit_trail(txn.transaction_id)[-1]
        assert last.from_state == TransactionState.PENDING
        assert last.to_state == TransactionState.APPROVED

    def test_the_trail_is_ordered_by_time(self, sim, txn):
        sim.hold_transaction(txn.transaction_id, reason="r")
        sim.release_transaction(txn.transaction_id, "V-1")
        stamps = [e.timestamp for e in sim.get_audit_trail(txn.transaction_id)]
        assert stamps == sorted(stamps)

    def test_the_trail_is_a_copy(self, sim, txn):
        """A caller mutating the returned list must not corrupt the record."""
        trail = sim.get_audit_trail(txn.transaction_id)
        trail.clear()
        assert len(sim.get_audit_trail(txn.transaction_id)) == 1

    def test_audit_events_are_session_linked(self, sim, txn):
        sim.hold_transaction(txn.transaction_id, reason="r", session_id="sess-1")
        assert any(e.session_id == "sess-1" for e in sim.get_audit_trail(txn.transaction_id))

    def test_a_full_lifecycle_leaves_a_complete_narrative(self, sim, txn):
        sim.request_risk_action(txn.transaction_id, PolicyAction.HOLD, reason="synthetic voice")
        sim.release_transaction(txn.transaction_id, "CALLBACK-8891")
        kinds = [e.event_type for e in sim.get_audit_trail(txn.transaction_id)]
        assert kinds == [
            AuditEventType.TRANSACTION_CREATED,
            AuditEventType.RISK_ACTION_REQUESTED,
            AuditEventType.HOLD_PLACED,
            AuditEventType.VERIFICATION_RECORDED,
            AuditEventType.HOLD_RELEASED,
        ]


# =============================================================================
# Determinism
# =============================================================================


class TestDeterminism:
    def _run(self):
        ticker = count()
        base = datetime(2026, 8, 28, 12, 0, 0, tzinfo=timezone.utc)
        ids = count()
        sim = TransactionSimulator(
            clock=lambda: base + timedelta(seconds=next(ticker)),
            id_factory=lambda: f"id-{next(ids):04d}",
        )
        t = sim.create_transaction(caller_identity="alice", amount="5000", beneficiary="acme")
        sim.request_risk_action(t.transaction_id, PolicyAction.HOLD, reason="risk")
        sim.release_transaction(t.transaction_id, "CALLBACK-1")
        return sim.get_transaction(t.transaction_id), sim.get_audit_trail(t.transaction_id)

    def test_the_same_calls_produce_the_same_result(self):
        first_txn, first_trail = self._run()
        second_txn, second_trail = self._run()
        assert first_txn.model_dump_json() == second_txn.model_dump_json()
        assert [e.model_dump_json() for e in first_trail] == [
            e.model_dump_json() for e in second_trail
        ]

    def test_the_clock_is_injectable(self):
        fixed = datetime(2020, 1, 1, tzinfo=timezone.utc)
        sim = TransactionSimulator(clock=lambda: fixed)
        t = sim.create_transaction(caller_identity="a", amount="1", beneficiary="b")
        assert t.created_at == fixed

    def test_reset_clears_all_state(self, sim, txn):
        sim.reset()
        assert sim.list_transactions() == []
        with pytest.raises(TransactionNotFound):
            sim.get_transaction(txn.transaction_id)


# =============================================================================
# API surface
# =============================================================================


class TestTransactionAPI:
    def _create(self, api, **overrides):
        payload = {
            "caller_identity": "alice", "amount": "5000.00",
            "beneficiary": "acme", "beneficiary_novelty": "NEW",
        }
        payload.update(overrides)
        return api.post("/v1/demo/transactions", json=payload)

    def test_create_returns_201_and_pending(self, api):
        response = self._create(api)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["transaction"]["state"] == "PENDING"

    def test_create_rejects_a_non_positive_amount(self, api):
        response = self._create(api, amount="0")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_rejects_unknown_fields(self, api):
        response = api.post("/v1/demo/transactions", json={
            "caller_identity": "a", "amount": "1", "beneficiary": "b", "state": "APPROVED",
        })
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_view_returns_the_transaction(self, api):
        tid = self._create(api).json()["transaction"]["transaction_id"]
        response = api.get(f"/v1/demo/transactions/{tid}")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["transaction"]["transaction_id"] == tid

    def test_view_of_an_unknown_id_is_404(self, api):
        assert api.get("/v1/demo/transactions/ghost").status_code == status.HTTP_404_NOT_FOUND

    def test_update_state_moves_along_a_legal_edge(self, api):
        tid = self._create(api).json()["transaction"]["transaction_id"]
        response = api.patch(f"/v1/demo/transactions/{tid}/state",
                             json={"state": "CANCELLED", "reason": "customer hung up"})
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["transaction"]["state"] == "CANCELLED"

    def test_an_illegal_transition_is_409(self, api):
        tid = self._create(api).json()["transaction"]["transaction_id"]
        api.patch(f"/v1/demo/transactions/{tid}/state", json={"state": "APPROVED"})
        response = api.patch(f"/v1/demo/transactions/{tid}/state", json={"state": "HELD"})
        assert response.status_code == status.HTTP_409_CONFLICT

    def test_hold_then_release_round_trip(self, api):
        tid = self._create(api).json()["transaction"]["transaction_id"]
        held = api.post(f"/v1/demo/transactions/{tid}/hold", json={"reason": "voice risk"})
        assert held.json()["transaction"]["state"] == "HELD"
        released = api.post(f"/v1/demo/transactions/{tid}/release",
                            json={"verification_reference": "CALLBACK-8891"})
        assert released.status_code == status.HTTP_200_OK
        assert released.json()["transaction"]["state"] == "APPROVED"

    def test_release_without_a_reference_is_rejected(self, api):
        tid = self._create(api).json()["transaction"]["transaction_id"]
        api.post(f"/v1/demo/transactions/{tid}/hold", json={})
        response = api.post(f"/v1/demo/transactions/{tid}/release",
                            json={"verification_reference": ""})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_releasing_an_unheld_transaction_is_409(self, api):
        tid = self._create(api).json()["transaction"]["transaction_id"]
        response = api.post(f"/v1/demo/transactions/{tid}/release",
                            json={"verification_reference": "V-1"})
        assert response.status_code == status.HTTP_409_CONFLICT

    @pytest.mark.parametrize("action,expected", [
        ("HOLD", "HELD"), ("ESCALATE", "HELD"),
        ("ALLOW", "PENDING"), ("STEP_UP", "PENDING"),
    ])
    def test_the_risk_engine_can_request_each_action(self, api, action, expected):
        tid = self._create(api).json()["transaction"]["transaction_id"]
        response = api.post(f"/v1/demo/transactions/{tid}/risk-action", json={"action": action})
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["transaction"]["state"] == expected

    def test_an_inapplicable_risk_action_is_refused(self, api):
        """WARN is a voice-session concern; it says nothing about a transaction."""
        tid = self._create(api).json()["transaction"]["transaction_id"]
        response = api.post(f"/v1/demo/transactions/{tid}/risk-action", json={"action": "WARN"})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_the_audit_endpoint_returns_the_trail(self, api):
        tid = self._create(api).json()["transaction"]["transaction_id"]
        api.post(f"/v1/demo/transactions/{tid}/hold", json={"reason": "r"})
        response = api.get(f"/v1/demo/transactions/{tid}/audit")
        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["environment"] == DEMO_ENVIRONMENT_LABEL
        assert [e["event_type"] for e in body["events"]] == [
            "TRANSACTION_CREATED", "HOLD_PLACED",
        ]

    def test_transactions_can_be_listed_by_session(self, api):
        self._create(api, session_id="s1")
        self._create(api, session_id="s2")
        body = api.get("/v1/demo/transactions", params={"session_id": "s1"}).json()
        assert len(body["transactions"]) == 1

    def test_no_endpoint_claims_to_execute_a_real_payment(self, api):
        """Guards the wording, which is what an outside reader actually sees.

        Matches claim-shaped phrases only. "No real funds move" is a denial and
        must be allowed to stand - banning the substring "real funds" outright
        would forbid the very disclaimer this is protecting.
        """
        spec = api.get("/openapi.json").json()
        demo_paths = {p: v for p, v in spec["paths"].items() if "/v1/demo/transactions" in p}
        assert demo_paths
        blob = str(demo_paths).lower()
        for banned in (
            "executes a payment",
            "transfers real funds",
            "settles",
            "sends a wire instruction",
            "connects to the bank",
        ):
            assert banned not in blob

    def test_every_demo_endpoint_is_tagged_as_the_demo_environment(self, api):
        """The tag is what a reader browsing /docs sees before any description."""
        spec = api.get("/openapi.json").json()
        for path, methods in spec["paths"].items():
            if "/v1/demo/transactions" not in path:
                continue
            for operation in methods.values():
                assert "Demo Transaction Environment" in operation.get("tags", [])


# =============================================================================
# Integration with the risk engine
# =============================================================================


class TestRiskEngineIntegration:
    def test_a_hold_decision_actually_holds_the_transaction(self, sim):
        """End to end: the engine's verdict has to be consequential."""
        from tests.test_risk_engine import make_belief, make_context
        from voiceshield.contracts import BeneficiaryNovelty as BN
        from voiceshield.contracts import DecisionBand
        from voiceshield.risk import StandardRiskEngine

        decision = StandardRiskEngine().assess(
            "sess-9",
            make_belief(p_spoof=0.9, confidence=0.9, band=DecisionBand.SYNTHETIC_HIGH_CONFIDENCE),
            make_context(transaction_type="WIRE_TRANSFER", amount=120_000, beneficiary=BN.NEW),
        )
        transaction = sim.create_transaction(
            caller_identity="alice", amount="120000", beneficiary="acme",
            beneficiary_novelty=BN.NEW, session_id="sess-9",
        )
        result = sim.request_risk_action(
            transaction.transaction_id, decision.action,
            reason=decision.matched_policy, session_id="sess-9",
        )
        assert decision.action in (PolicyAction.HOLD, PolicyAction.ESCALATE)
        assert result.state == TransactionState.HELD

    def test_an_ordinary_call_leaves_the_transaction_pending(self, sim):
        from tests.test_risk_engine import make_belief, make_context
        from voiceshield.contracts import KnownContactStatus
        from voiceshield.risk import StandardRiskEngine

        decision = StandardRiskEngine().assess(
            "sess-10",
            make_belief(p_spoof=0.03, confidence=0.95),
            make_context(transaction_type="BALANCE_ENQUIRY",
                         known_contact=KnownContactStatus.KNOWN_CONTACT,
                         verified_identity="alice"),
        )
        transaction = sim.create_transaction(
            caller_identity="alice", amount="50", beneficiary="self", session_id="sess-10",
        )
        result = sim.request_risk_action(transaction.transaction_id, decision.action)
        assert decision.action == PolicyAction.ALLOW
        assert result.state == TransactionState.PENDING

"""Transaction-bound, PHI-minimized audit events for production writes."""

from contextvars import ContextVar
from decimal import Decimal
from json import dumps
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings

_DETAIL_KEYS = frozenset(
    {
        "old_status",
        "new_status",
        "old_role",
        "new_role",
        "clinic_count",
        "payment_method",
        "amount",
        "amount_received",
        "change_due",
        "doctor_id",
        "reason_code",
        "late_entry",
        "care_not_started",
    }
)
audit_request_id: ContextVar[str | None] = ContextVar("audit_request_id", default=None)


def record_audit_event(
    session: Session,
    *,
    actor_user_id: int | None,
    actor_role: str | None,
    action: str,
    entity_type: str,
    entity_id: int | None,
    clinic_id: int | None = None,
    details: dict[str, str | int | Decimal | bool | None] | None = None,
    outcome: str = "SUCCESS",
    request_id: str | None = None,
) -> None:
    """Insert an audit row within the caller's transaction or fail the write.

    Never put clinical notes, names, contact details or secrets in ``details``.
    Only fixed, non-narrative fields are accepted, and production writes fail
    closed if the audit table is unavailable.
    """

    if get_settings().app_mode != "production":
        return
    if request_id is None:
        request_id = audit_request_id.get()
    if not action or len(action) > 80 or not entity_type or len(entity_type) > 50:
        raise ValueError("Audit action or entity type is invalid")
    if outcome not in {"SUCCESS", "DENIED", "FAILED"}:
        raise ValueError("Audit outcome is invalid")
    if actor_role is not None and len(actor_role) > 20:
        raise ValueError("Audit actor role is invalid")
    if request_id is not None and (len(request_id) != 32 or not all(ch in "0123456789abcdef" for ch in request_id)):
        raise ValueError("Audit request ID is invalid")

    safe_details: dict[str, Any] = {}
    for key, value in (details or {}).items():
        if key not in _DETAIL_KEYS:
            raise ValueError(f"Audit detail field is not allowed: {key}")
        if value is not None and not isinstance(value, (str, int, Decimal, bool)):
            raise ValueError(f"Audit detail value is invalid: {key}")
        if isinstance(value, str) and len(value) > 80:
            raise ValueError(f"Audit detail value is too long: {key}")
        if isinstance(value, str) and key in {"old_status", "new_status", "old_role", "new_role", "payment_method", "reason_code"} and not (value.isascii() and value.replace("_", "").isalnum()):
            raise ValueError(f"Audit detail code is invalid: {key}")
        safe_details[key] = str(value) if isinstance(value, Decimal) else value
    serialized = dumps(safe_details, sort_keys=True, separators=(",", ":")) if safe_details else None
    if serialized is not None and len(serialized) > 1000:
        raise ValueError("Audit details exceed database limit")

    session.execute(
        text(
            "INSERT INTO dbo.AuditEvents "
            "(ActorUserID, ActorRole, Action, EntityType, EntityID, ClinicID, "
            "Outcome, RequestID, Details) "
            "VALUES (:actor_user_id, :actor_role, :action, :entity_type, "
            ":entity_id, :clinic_id, :outcome, :request_id, :details)"
        ),
        {
            "actor_user_id": actor_user_id,
            "actor_role": actor_role,
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "clinic_id": clinic_id,
            "outcome": outcome,
            "request_id": request_id,
            "details": serialized,
        },
    )

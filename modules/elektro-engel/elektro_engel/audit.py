"""Payload-free, bounded in-memory audit events."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
import re
from uuid import UUID

MAX_AUDIT_EVENTS = 1_000
EVENT_OUTCOMES = {
    ("plan", "proposed"),
    ("tool_execution", "completed"),
    ("tool_execution", "denied_or_failed"),
}


@dataclass(frozen=True)
class AuditEvent:
    request_id: str
    event_type: str
    outcome: str
    tool_name: str | None = None
    occurred_at: str = ""


class InMemoryAuditLog:
    """Retain only bounded identifiers and outcomes; never persist payloads."""

    def __init__(self, max_events: int = MAX_AUDIT_EVENTS) -> None:
        if type(max_events) is not int or not 1 <= max_events <= MAX_AUDIT_EVENTS:
            raise ValueError("max_events must be between 1 and 1000")
        self._events: deque[AuditEvent] = deque(maxlen=max_events)

    def record(
        self,
        request_id: str,
        event_type: str,
        outcome: str,
        tool_name: str | None = None,
    ) -> None:
        if not isinstance(request_id, str) or str(UUID(request_id)) != request_id:
            raise ValueError("request_id must be a canonical UUID")
        if (event_type, outcome) not in EVENT_OUTCOMES:
            raise ValueError("audit event type or outcome is invalid")
        if tool_name is not None and (
            not isinstance(tool_name, str)
            or not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", tool_name)
        ):
            raise ValueError("tool_name is invalid")
        self._events.append(
            AuditEvent(
                request_id=request_id,
                event_type=event_type,
                outcome=outcome,
                tool_name=tool_name,
                occurred_at=datetime.now(timezone.utc).isoformat(),
            )
        )

    def events(self) -> tuple[AuditEvent, ...]:
        return tuple(self._events)

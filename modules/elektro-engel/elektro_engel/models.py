"""Immutable, platform-neutral task and planning models."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4

from .errors import RequestError

MAX_REQUEST_CHARS = 2_000
MAX_REQUEST_ID_CHARS = 64


@dataclass(frozen=True)
class TaskRequest:
    objective: str
    request_id: str = field(default_factory=lambda: str(uuid4()))

    def __post_init__(self) -> None:
        if not isinstance(self.objective, str) or not self.objective.strip():
            raise RequestError("objective must be a non-empty string")
        if len(self.objective) > MAX_REQUEST_CHARS:
            raise RequestError("objective exceeds the input limit")
        if not isinstance(self.request_id, str) or not self.request_id.strip():
            raise RequestError("request_id must be a non-empty string")
        if len(self.request_id) > MAX_REQUEST_ID_CHARS:
            raise RequestError("request_id exceeds the input limit")


@dataclass(frozen=True)
class PlanStep:
    sequence: int
    description: str
    requires_human_review: bool = True


@dataclass(frozen=True)
class TaskPlan:
    request_id: str
    steps: tuple[PlanStep, ...]
    status: str = "proposed"

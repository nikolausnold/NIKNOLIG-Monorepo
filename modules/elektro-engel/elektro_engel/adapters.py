"""Optional host integration ports; no application implementation is included."""

from __future__ import annotations

from typing import Protocol

from .models import TaskPlan, TaskRequest


class NiknoligAdapter(Protocol):
    """Optional port implemented by an app-owned NIKNOLIG integration."""

    def to_core_request(self, app_input: str) -> TaskRequest:
        """Translate app-local input into the platform-neutral request model."""

    def present_core_plan(self, plan: TaskPlan) -> None:
        """Present a proposed plan without implying approval or execution."""

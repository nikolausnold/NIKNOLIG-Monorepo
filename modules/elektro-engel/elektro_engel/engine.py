"""Core orchestration with bounded planning and explicit tool authorization."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .audit import InMemoryAuditLog
from .errors import ToolApprovalRequired, ToolExecutionError, ToolNotFoundError
from .models import TaskPlan, TaskRequest
from .planning import BoundedPlanner
from .tools import ToolApproval, ToolRegistry


class CoreEngine:
    """Coordinate review-only planning and explicitly approved local tools."""

    def __init__(
        self,
        *,
        planner: BoundedPlanner | None = None,
        tools: ToolRegistry | None = None,
        audit_log: InMemoryAuditLog | None = None,
    ) -> None:
        self.planner = planner or BoundedPlanner()
        self.tools = tools or ToolRegistry()
        self.audit_log = audit_log or InMemoryAuditLog()

    def plan(self, request: TaskRequest) -> TaskPlan:
        plan = self.planner.plan(request)
        self.audit_log.record(request.request_id, "plan", "proposed")
        return plan

    def execute(
        self,
        request: TaskRequest,
        tool_name: str,
        arguments: Mapping[str, Any],
        approval: ToolApproval,
    ) -> Any:
        try:
            result = self.tools.execute(tool_name, request, arguments, approval)
        except (ToolApprovalRequired, ToolNotFoundError, ToolExecutionError):
            self.audit_log.record(request.request_id, "tool_execution", "denied_or_failed", tool_name)
            raise
        self.audit_log.record(request.request_id, "tool_execution", "completed", tool_name)
        return result

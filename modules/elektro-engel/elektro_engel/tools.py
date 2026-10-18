"""Explicit allowlist and per-request approval gate for host-provided tools."""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from .errors import ToolApprovalRequired, ToolExecutionError, ToolNotFoundError
from .models import TaskRequest

Tool = Callable[[Mapping[str, Any]], Any]
TOOL_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
MAX_REGISTERED_TOOLS = 32


@dataclass(frozen=True)
class ToolApproval:
    request_id: str
    tool_name: str
    explicitly_granted: bool


class ToolRegistry:
    """Invoke only locally registered tools with matching explicit approval."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, name: str, tool: Tool) -> None:
        if not isinstance(name, str) or not TOOL_NAME_PATTERN.fullmatch(name):
            raise ValueError("tool name is invalid")
        if not callable(tool):
            raise TypeError("tool must be callable")
        if name in self._tools:
            raise ValueError("tool name is already registered")
        if len(self._tools) >= MAX_REGISTERED_TOOLS:
            raise ValueError("tool registry capacity reached")
        self._tools[name] = tool

    def execute(
        self,
        name: str,
        request: TaskRequest,
        arguments: Mapping[str, Any],
        approval: ToolApproval,
    ) -> Any:
        if not isinstance(name, str) or not TOOL_NAME_PATTERN.fullmatch(name):
            raise ToolNotFoundError("tool is not registered")
        tool = self._tools.get(name)
        if tool is None:
            raise ToolNotFoundError("tool is not registered")
        if (
            not isinstance(approval, ToolApproval)
            or approval.explicitly_granted is not True
            or approval.request_id != request.request_id
            or approval.tool_name != name
        ):
            raise ToolApprovalRequired("explicit approval for this request and tool is required")
        if not isinstance(arguments, Mapping):
            raise TypeError("tool arguments must be a mapping")
        try:
            return tool(arguments)
        except Exception as error:
            raise ToolExecutionError("approved tool execution failed") from None

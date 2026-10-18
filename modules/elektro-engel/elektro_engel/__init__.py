"""Platform-neutral, standard-library-only Elektro-Engel core."""

from .audit import AuditEvent, InMemoryAuditLog
from .context import ContextStore
from .engine import CoreEngine
from .errors import (
    ContextError,
    RequestError,
    ToolApprovalRequired,
    ToolExecutionError,
    ToolNotFoundError,
)
from .learning import LearningSandbox, RuleProposal
from .models import PlanStep, TaskPlan, TaskRequest
from .tools import ToolApproval, ToolRegistry

__all__ = [
    "AuditEvent",
    "ContextError",
    "ContextStore",
    "CoreEngine",
    "InMemoryAuditLog",
    "LearningSandbox",
    "PlanStep",
    "RequestError",
    "RuleProposal",
    "TaskPlan",
    "TaskRequest",
    "ToolApproval",
    "ToolApprovalRequired",
    "ToolExecutionError",
    "ToolNotFoundError",
    "ToolRegistry",
]

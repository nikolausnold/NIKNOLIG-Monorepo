"""Public errors for invalid requests and denied or failed operations."""


class RequestError(ValueError):
    """Raised when a task request is missing or exceeds its input limits."""


class ContextError(ValueError):
    """Raised when context violates the in-memory context policy."""


class ToolNotFoundError(LookupError):
    """Raised when a tool is not explicitly registered."""


class ToolApprovalRequired(PermissionError):
    """Raised when an exact, explicit approval is missing."""


class ToolExecutionError(RuntimeError):
    """Raised when an approved tool fails; details are deliberately withheld."""

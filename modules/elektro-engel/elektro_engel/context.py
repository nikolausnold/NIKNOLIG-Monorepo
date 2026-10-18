"""Small, explicitly populated, process-local context store."""

from __future__ import annotations

from .errors import ContextError

MAX_CONTEXT_KEY_CHARS = 64
MAX_CONTEXT_VALUE_CHARS = 1_000
ALLOWED_CATEGORY = "non_sensitive"


class ContextStore:
    """Keep explicitly classified non-sensitive context in memory only."""

    def __init__(self, max_entries: int = 32) -> None:
        if type(max_entries) is not int or not 1 <= max_entries <= 256:
            raise ContextError("max_entries must be between 1 and 256")
        self._max_entries = max_entries
        self._items: dict[str, str] = {}

    def put(self, key: str, value: str, *, category: str) -> None:
        if category != ALLOWED_CATEGORY:
            raise ContextError("only explicitly classified non-sensitive context is accepted")
        if not isinstance(key, str) or not key.strip() or len(key) > MAX_CONTEXT_KEY_CHARS:
            raise ContextError("context key is invalid")
        if not isinstance(value, str) or len(value) > MAX_CONTEXT_VALUE_CHARS:
            raise ContextError("context value is invalid")
        if key not in self._items and len(self._items) >= self._max_entries:
            raise ContextError("context capacity reached")
        self._items[key] = value

    def get(self, key: str) -> str | None:
        return self._items.get(key)

    def snapshot(self) -> dict[str, str]:
        return dict(self._items)

    def clear(self) -> None:
        self._items.clear()

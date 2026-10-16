import asyncio
import math
from collections.abc import Awaitable, Callable, Sequence


DependencyCheck = Callable[[], Awaitable[bool]]


class Readiness:
    """Check trusted, nonblocking, cancellation-cooperative dependencies."""

    def __init__(
        self,
        checks: Sequence[DependencyCheck] = (),
        timeout_seconds: float = 0.5,
    ) -> None:
        if (
            isinstance(timeout_seconds, bool)
            or not math.isfinite(timeout_seconds)
            or not 0 < timeout_seconds <= 5
        ):
            raise ValueError("Readiness timeout must be finite and in (0, 5].")
        self._checks = tuple(checks)
        self._timeout_seconds = timeout_seconds

    async def is_ready(self) -> bool:
        try:
            async with asyncio.timeout(self._timeout_seconds):
                for check in self._checks:
                    if await check() is not True:
                        return False
            return True
        except Exception:
            return False

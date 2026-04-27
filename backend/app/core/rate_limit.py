from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock


class InMemoryRateLimiter:
    """
    Best-effort in-memory rate limiter (per-process).

    Notes:
    - Suitable for single-instance deployments and development.
    - For multi-instance production, replace with a shared store (e.g., Redis) behind the same interface.
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._events: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, *, key: str, limit: int, window_seconds: int) -> bool:
        now = time.time()
        cutoff = now - float(window_seconds)
        with self._lock:
            q = self._events[key]
            while q and q[0] < cutoff:
                q.popleft()
            if len(q) >= int(limit):
                return False
            q.append(now)
            return True


otp_ip_limiter = InMemoryRateLimiter()


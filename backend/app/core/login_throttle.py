"""Shared, process-local account guard for every password login entrypoint.

The HTTPS reverse proxy must rate-limit by the real client address. Behind
that proxy, ``request.client.host`` is the proxy's loopback address, so an
application-wide address limit would let one attacker lock out every user.
"""

from collections import defaultdict, deque
from hashlib import sha256
from threading import Lock
from time import monotonic

from fastapi import HTTPException, Request

from backend.app.core.config import get_settings

WINDOW_SECONDS = 15 * 60
MAX_ACCOUNT_FAILURES = 8


class LoginThrottle:
    def __init__(self) -> None:
        self._failures: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    @staticmethod
    def _key(username: str) -> str:
        principal = sha256(username.strip().lower().encode("utf-8")).hexdigest()
        return f"account:{principal}"

    def _prune(self, key: str, now: float) -> None:
        events = self._failures[key]
        while events and events[0] <= now - WINDOW_SECONDS:
            events.popleft()
        if not events:
            self._failures.pop(key, None)

    def check(self, request: Request, username: str) -> None:
        if get_settings().app_mode != "production":
            return
        account_key = self._key(username)
        now = monotonic()
        with self._lock:
            self._prune(account_key, now)
            blocked = len(self._failures.get(account_key, ())) >= MAX_ACCOUNT_FAILURES
        if blocked:
            raise HTTPException(
                status_code=429,
                detail="Too many login attempts. Please try again later.",
                headers={"Retry-After": str(WINDOW_SECONDS)},
            )

    def failed(self, request: Request, username: str) -> None:
        if get_settings().app_mode != "production":
            return
        now = monotonic()
        account_key = self._key(username)
        with self._lock:
            self._prune(account_key, now)
            self._failures[account_key].append(now)

    def succeeded(self, request: Request, username: str) -> None:
        if get_settings().app_mode != "production":
            return
        account_key = self._key(username)
        with self._lock:
            self._failures.pop(account_key, None)


login_throttle = LoginThrottle()

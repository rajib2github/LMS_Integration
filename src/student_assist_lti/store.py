"""Demo storage contracts. Use a shared Redis/database implementation in production."""
import secrets
import time
from dataclasses import dataclass
from threading import Lock
from typing import Any


@dataclass
class OidcTransaction:
    nonce: str
    created_at: float


class MemoryTransactionStore:
    def __init__(self, ttl_seconds: int = 600):
        self.ttl_seconds = ttl_seconds
        self._items: dict[str, OidcTransaction] = {}
        self._lock = Lock()

    def create(self, state: str, nonce: str) -> None:
        with self._lock:
            self._items[state] = OidcTransaction(nonce, time.time())

    def consume(self, state: str) -> OidcTransaction | None:
        with self._lock:
            item = self._items.pop(state, None)
        if item and time.time() - item.created_at <= self.ttl_seconds:
            return item
        return None


class MemoryLaunchStore:
    """One-time opaque launch codes for the browser handoff in the demo."""
    def __init__(self, ttl_seconds: int = 60):
        self.ttl_seconds = ttl_seconds
        self._items: dict[str, tuple[float, dict[str, Any]]] = {}
        self._lock = Lock()

    def create(self, value: dict[str, Any]) -> str:
        code = secrets.token_urlsafe(32)
        with self._lock:
            self._items[code] = (time.time(), value)
        return code

    def consume(self, code: str) -> dict[str, Any] | None:
        with self._lock:
            item = self._items.pop(code, None)
        if item and time.time() - item[0] <= self.ttl_seconds:
            return item[1]
        return None

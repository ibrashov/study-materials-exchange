"""Week 11 (Talgat): in-memory sliding-window request limits.

Limits are per client IP and per rule. State lives in process memory, so it
resets on restart and is not shared between several worker processes; for a
multi-worker deployment use a shared store (e.g. Redis). Documented in
docs/week11/TALGAT_REQUEST_LIMIT.md.
"""
from collections import defaultdict, deque
from dataclasses import dataclass
import math
import threading
import time


@dataclass(frozen=True)
class Rule:
    name: str
    method: str | None      # None = any method
    path_prefix: str        # '' = any path
    limit: int
    window: int             # seconds


# First matching rule wins; the last rule is the global default.
RULES = (
    Rule('login', 'POST', '/api/auth/login', 10, 60),
    Rule('register', 'POST', '/api/auth/register', 5, 600),
    Rule('twofa', 'POST', '/api/auth/2fa', 10, 60),
    Rule('upload', 'POST', '/api/materials', 20, 600),
    Rule('download', 'GET', '/api/materials/', 60, 60),
    Rule('default', None, '', 120, 60),
)


def match_rule(method: str, path: str) -> Rule:
    for rule in RULES:
        if rule.method in (None, method) and path.startswith(rule.path_prefix):
            if rule.name == 'download' and not path.endswith('/download'):
                continue
            return rule
    return RULES[-1]


class RateLimiter:
    def __init__(self, clock=time.monotonic):
        self._hits: dict[tuple[str, str], deque] = defaultdict(deque)
        self._lock = threading.Lock()
        self._clock = clock

    def reset(self):
        with self._lock:
            self._hits.clear()

    def check(self, client: str, rule: Rule):
        """Return (allowed, retry_after_seconds)."""
        now = self._clock()
        key = (client, rule.name)
        with self._lock:
            hits = self._hits[key]
            while hits and hits[0] <= now - rule.window:
                hits.popleft()
            if len(hits) >= rule.limit:
                return False, max(1, math.ceil(hits[0] + rule.window - now))
            hits.append(now)
            if len(self._hits) > 10_000:   # bound memory: drop idle keys
                for k in [k for k, v in self._hits.items() if not v or v[-1] <= now - 600]:
                    del self._hits[k]
            return True, 0


limiter = RateLimiter()

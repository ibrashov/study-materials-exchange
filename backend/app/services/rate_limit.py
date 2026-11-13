"""In-memory sliding-window request limiter for the auth endpoints.

State lives in this process only: it resets on restart and is not shared between
several server workers. Good enough for one server; use Redis or a proxy for more.
"""
from collections import defaultdict, deque
from threading import Lock
import time
from fastapi import HTTPException, Request
from ..core.config import settings

class RateLimiter:
    def __init__(self, name):
        self.name = name
        self.hits = defaultdict(deque)
        self.lock = Lock()

    def check(self, key, limit, window):
        now = time.monotonic()
        with self.lock:
            queue = self.hits[key]
            while queue and now - queue[0] >= window:
                queue.popleft()
            if len(queue) >= limit:
                retry = max(1, int(window - (now - queue[0])) + 1)
                raise HTTPException(429, 'Too many requests. Try again later.', headers={'Retry-After': str(retry)})
            queue.append(now)
            if len(self.hits) > 10_000:  # drop idle keys so memory stays bounded
                for stale in [k for k, q in self.hits.items() if not q or now - q[-1] >= window]:
                    del self.hits[stale]

    def reset(self):
        with self.lock:
            self.hits.clear()

register_limiter = RateLimiter('register')
login_limiter = RateLimiter('login')

def client_ip(request: Request):
    return request.client.host if request.client else 'unknown'

def limit_register(request: Request):
    if settings.rate_limit_enabled:
        register_limiter.check(client_ip(request), settings.register_limit, settings.rate_limit_window)

def limit_login(request: Request):
    if settings.rate_limit_enabled:
        login_limiter.check(client_ip(request), settings.login_limit, settings.rate_limit_window)

def reset_all():
    register_limiter.reset()
    login_limiter.reset()

import time
from collections import deque
from dataclasses import dataclass

from fastapi import HTTPException, Request, Response, status

from app.core.config import get_settings


@dataclass(frozen=True)
class RateLimitRule:
    requests: int
    window_seconds: int


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._buckets: dict[str, deque[float]] = {}

    def reset(self) -> None:
        self._buckets.clear()

    def check(self, key: str, rule: RateLimitRule) -> tuple[bool, int, int]:
        now = time.time()
        bucket = self._buckets.setdefault(key, deque())
        window_start = now - rule.window_seconds

        while bucket and bucket[0] <= window_start:
            bucket.popleft()

        if len(bucket) >= rule.requests:
            retry_after = max(1, int(bucket[0] + rule.window_seconds - now))
            return False, 0, retry_after

        bucket.append(now)
        remaining = max(0, rule.requests - len(bucket))
        return True, remaining, rule.window_seconds


rate_limiter = InMemoryRateLimiter()


def get_rate_limit_rule(path: str) -> RateLimitRule | None:
    settings = get_settings()
    if path == "/health":
        return None
    if path == "/auth/login":
        return RateLimitRule(
            requests=settings.login_rate_limit_requests,
            window_seconds=settings.login_rate_limit_window_seconds,
        )
    return RateLimitRule(
        requests=settings.api_rate_limit_requests,
        window_seconds=settings.api_rate_limit_window_seconds,
    )


def get_client_identifier(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _apply_rate_limit(rule: RateLimitRule, request: Request, response: Response) -> None:
    client_id = get_client_identifier(request)
    bucket_key = f"{request.method}:{request.url.path}:{client_id}"
    allowed, remaining, window_value = rate_limiter.check(bucket_key, rule)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={
                "Retry-After": str(window_value),
                "X-RateLimit-Limit": str(rule.requests),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Window": str(rule.window_seconds),
            },
        )

    response.headers["X-RateLimit-Limit"] = str(rule.requests)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Window"] = str(window_value)


def login_rate_limit(request: Request, response: Response) -> None:
    settings = get_settings()
    _apply_rate_limit(
        RateLimitRule(
            requests=settings.login_rate_limit_requests,
            window_seconds=settings.login_rate_limit_window_seconds,
        ),
        request,
        response,
    )


def api_rate_limit(request: Request, response: Response) -> None:
    settings = get_settings()
    _apply_rate_limit(
        RateLimitRule(
            requests=settings.api_rate_limit_requests,
            window_seconds=settings.api_rate_limit_window_seconds,
        ),
        request,
        response,
    )

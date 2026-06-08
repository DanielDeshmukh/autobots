"""Retry decorator with exponential backoff."""
from __future__ import annotations

import functools
import logging
import time
from typing import Callable, TypeVar

T = TypeVar("T")

logger = logging.getLogger("autobots")

# Exceptions that warrant a retry (transient failures)
_RETRYABLE_ERRORS: tuple[type[Exception], ...] = (
    ConnectionError,
    TimeoutError,
    OSError,
)


def with_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    retryable_errors: tuple[type[Exception], ...] | None = None,
) -> Callable:
    """Decorator that retries a function on transient failures.

    Args:
        max_attempts: Total number of attempts (1 = no retry).
        base_delay: Initial delay in seconds between retries.
        retryable_errors: Tuple of exception types to retry on.
                          Defaults to common network/IO errors.
    """
    errors = retryable_errors or _RETRYABLE_ERRORS

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exc: Exception | None = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except errors as exc:
                    last_exc = exc
                    if attempt < max_attempts - 1:
                        delay = base_delay * (2 ** attempt)
                        logger.warning(
                            "Attempt %d/%d failed (%s): %s — retrying in %.1fs",
                            attempt + 1,
                            max_attempts,
                            type(exc).__name__,
                            exc,
                            delay,
                        )
                        time.sleep(delay)
            raise last_exc  # type: ignore[misc]

        return wrapper

    return decorator

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, TypeVar

import httpx

__all__ = ["RateLimit", "ResponseInfo", "last_response"]

T = TypeVar("T")


@dataclass(frozen=True)
class RateLimit:
    """The rate limit a response reported, from its ``RateLimit-*`` headers."""

    limit: int
    """Requests allowed in each window."""
    remaining: int
    """Requests left in the current window."""
    reset_seconds: int
    """Seconds until the window resets."""


# Compared and hashed by identity, since `httpx.Headers` can't be hashed.
@dataclass(frozen=True, eq=False)
class ResponseInfo:
    """The HTTP response a result came from. Get it with ``kirora.last_response()``."""

    status: int
    headers: httpx.Headers
    request_id: Optional[str]
    """The ``X-Request-Id`` header. Quote it to Kirora support."""
    idempotency_replay: bool
    """True when the API answered with its stored response to an earlier request with
    the same idempotency key, rather than acting again."""
    rate_limit: Optional[RateLimit]
    """None unless the response had valid ``RateLimit-*`` headers."""


class _ResponseDict(dict):  # type: ignore[type-arg]
    """A dict from the API that remembers the response it came from."""

    __slots__ = ("_last_response",)


class _ResponseList(list):  # type: ignore[type-arg]
    """A list from the API that remembers the response it came from."""

    __slots__ = ("_last_response",)


def with_response(value: Any, info: ResponseInfo) -> Any:
    """Returns ``value`` as a dict or list that carries ``info``, or as it is."""
    if isinstance(value, dict):
        result: Any = _ResponseDict(value)
    elif isinstance(value, list):
        result = _ResponseList(value)
    else:
        return value
    result._last_response = info
    return result


def last_response(result: Any) -> Optional[ResponseInfo]:
    """Returns the HTTP response a result came from: its status, headers, request id,
    rate limit and whether it was an idempotency replay. Returns None for a value that
    didn't come from the API, or a copy of one.

        contact = kirora.Contacts.get("ada@example.com", id_type="email")
        print(kirora.last_response(contact).request_id)
    """
    info = getattr(result, "_last_response", None)
    if isinstance(info, ResponseInfo):
        return info
    # A page keeps its response as `last_response`.
    info = getattr(result, "last_response", None)
    return info if isinstance(info, ResponseInfo) else None

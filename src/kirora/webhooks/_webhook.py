from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Mapping, Tuple, Union

from typing_extensions import Protocol

__all__ = [
    "DEFAULT_WEBHOOK_TOLERANCE_SECONDS",
    "IncomingHeaders",
    "RawBody",
    "VerifiedWebhook",
    "WebhookHeaders",
]

DEFAULT_WEBHOOK_TOLERANCE_SECONDS = 300
"""How far a webhook's timestamp may be from now, in seconds, before it's rejected as a
replay: 5 minutes."""

RawBody = Union[str, bytes, bytearray, memoryview]
"""A request body, as received: before any JSON parsing."""


class _HasItems(Protocol):
    def items(self) -> Iterable[Tuple[Any, Any]]: ...


IncomingHeaders = Union[Mapping[str, Any], _HasItems, Iterable[Tuple[str, Any]]]
"""Any mapping of headers, or anything with ``items()``, such as Flask's, Django's,
Starlette's or ``http.server``'s, or a list of name and value pairs."""


@dataclass(frozen=True)
class WebhookHeaders:
    """The headers Kirora sends with each webhook."""

    event: str
    """The event type, one of ``WEBHOOK_EVENTS``, or a newer one as a string."""
    event_id: str
    """The same on every delivery attempt of an event, so deduplicate on it."""
    attempt: int
    """Which delivery attempt this is, from 1."""
    timestamp: str
    """Seconds since the epoch. Pass it to ``verify_webhook_signature()`` as it is."""
    signature: str


@dataclass(frozen=True)
class VerifiedWebhook:
    """A webhook that passed ``assert_webhook()``."""

    headers: WebhookHeaders
    """The request's headers, whose ``event`` and ``event_id`` match the body's."""
    payload: Dict[str, Any]
    """The parsed body: the event, with ``eventId`` and ``eventType``."""

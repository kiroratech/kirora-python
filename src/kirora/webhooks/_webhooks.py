from __future__ import annotations

import hashlib
import hmac
import json
import math
import time
from typing import Any, Callable, Dict, Iterable, Optional, TypeVar

from .._validation import check_id, check_number, parse_uint
from ..exceptions import KiroraWebhookVerificationError
from ._webhook import (
    DEFAULT_WEBHOOK_TOLERANCE_SECONDS,
    IncomingHeaders,
    RawBody,
    VerifiedWebhook,
    WebhookHeaders,
)

__all__ = ["Webhooks"]

T = TypeVar("T")


class Webhooks:
    """Verifies the webhooks Kirora sends you. Check the raw request body, before any
    JSON parsing: ``Webhooks.verify()`` returns the verified event, or None for a webhook
    that fails, and ``Webhooks.assert_valid()`` raises a
    ``KiroraWebhookVerificationError`` saying why instead."""

    @staticmethod
    def verify(
        secret: str,
        raw_body: RawBody,
        headers: IncomingHeaders,
        *,
        tolerance_seconds: float = DEFAULT_WEBHOOK_TOLERANCE_SECONDS,
        now: Optional[float] = None,
    ) -> Optional[VerifiedWebhook]:
        """Checks a webhook as ``Webhooks.assert_valid()`` does, and returns its headers and parsed
        body, or None if it fails. An empty secret or an invalid option still raises."""
        return _unless_refused(
            lambda: Webhooks.assert_valid(
                secret, raw_body, headers, tolerance_seconds=tolerance_seconds, now=now
            )
        )

    @staticmethod
    def assert_valid(
        secret: str,
        raw_body: RawBody,
        headers: IncomingHeaders,
        *,
        tolerance_seconds: float = DEFAULT_WEBHOOK_TOLERANCE_SECONDS,
        now: Optional[float] = None,
    ) -> VerifiedWebhook:
        """Checks that a webhook came from Kirora, as ``Webhooks.assert_headers()`` and
        ``Webhooks.assert_signature()`` do, and that its event headers match the signed body.
        Returns the headers and the parsed body.

        Pass the raw request body, before any JSON parsing: ``request.get_data()`` in Flask,
        ``request.body`` in Django, ``await request.body()`` in Starlette and FastAPI. Raises
        a ``KiroraWebhookVerificationError`` saying why a webhook fails, with
        ``invalid_headers`` if the event or event id header differs from the body's.
        """
        read = Webhooks.assert_headers(headers)
        Webhooks.assert_signature(
            secret, raw_body, read.signature, read.timestamp, tolerance_seconds=tolerance_seconds, now=now
        )
        try:
            payload = json.loads(_body_bytes(raw_body))
        except ValueError:
            payload = None
        # The signature covers only the timestamp and body, so the headers could have been
        # changed on a replay.
        if (
            not isinstance(payload, dict)
            or payload.get("eventId") != read.event_id
            or payload.get("eventType") != read.event
        ):
            raise KiroraWebhookVerificationError(
                "invalid_headers", "The event or event id header doesn't match the signed body"
            )
        return VerifiedWebhook(headers=read, payload=payload)

    @staticmethod
    def verify_signature(
        secret: str,
        raw_body: RawBody,
        signature: str,
        timestamp: str,
        *,
        tolerance_seconds: float = DEFAULT_WEBHOOK_TOLERANCE_SECONDS,
        now: Optional[float] = None,
    ) -> bool:
        """Returns whether a webhook came from Kirora, checked as
        ``Webhooks.assert_signature()`` checks it. An empty secret or an invalid option still
        raises."""

        def check() -> bool:
            Webhooks.assert_signature(
                secret, raw_body, signature, timestamp, tolerance_seconds=tolerance_seconds, now=now
            )
            return True

        return _unless_refused(check) is True

    @staticmethod
    def assert_signature(
        secret: str,
        raw_body: RawBody,
        signature: str,
        timestamp: str,
        *,
        tolerance_seconds: float = DEFAULT_WEBHOOK_TOLERANCE_SECONDS,
        now: Optional[float] = None,
    ) -> None:
        """Checks that a webhook came from Kirora, and raises a
        ``KiroraWebhookVerificationError`` saying why if it didn't.

        Pass the raw request body, before any JSON parsing, and the ``signature`` and
        ``timestamp`` from ``Webhooks.read_headers()``. ``now`` is the time to check against,
        in seconds since the epoch, and defaults to now. An empty secret or an invalid option
        raises a ``ValueError`` instead.
        """
        check_id("secret", secret)
        check_number("tolerance_seconds", tolerance_seconds, minimum=0)
        current = time.time() if now is None else check_number("now", now, minimum=-math.inf)
        seconds = parse_uint(timestamp if isinstance(timestamp, str) else None, 15)
        if seconds is None:
            raise KiroraWebhookVerificationError(
                "invalid_timestamp", "The timestamp header is missing or not a number of seconds"
            )
        body = _body_bytes(raw_body)
        digest = hmac.new(secret.encode(), timestamp.encode() + b"." + body, hashlib.sha256).hexdigest()
        expected = f"sha256={digest}".encode()
        matched = False
        # Every candidate is compared, so the time taken doesn't reveal which one matched.
        for candidate in (signature or "").split(","):
            if hmac.compare_digest(expected, candidate.strip().encode()):
                matched = True
        if not matched:
            raise KiroraWebhookVerificationError(
                "signature_mismatch",
                "No signature matches the body: check the secret, and pass the raw body unparsed",
            )
        # Checked after the signature, so a webhook rejected as too old or too new is one
        # Kirora did sign.
        age = math.floor(current) - seconds
        if abs(age) > tolerance_seconds:
            raise KiroraWebhookVerificationError(
                "timestamp_outside_tolerance",
                f"The timestamp is {abs(age)}s {'old' if age > 0 else 'in the future'}, beyond the "
                f"{tolerance_seconds:g}s tolerance: a replay, or a clock out of sync",
            )

    @staticmethod
    def read_headers(headers: IncomingHeaders) -> Optional[WebhookHeaders]:
        """Reads Kirora's headers from a webhook request, as ``Webhooks.assert_headers()``
        does, but returns None if one is missing or malformed. The signature doesn't cover
        ``event`` and ``event_id``: use ``Webhooks.verify()``, or take ``eventType`` and
        ``eventId`` from the verified body."""
        return _unless_refused(lambda: Webhooks.assert_headers(headers))

    @staticmethod
    def assert_headers(headers: IncomingHeaders) -> WebhookHeaders:
        """Reads Kirora's headers from a webhook request, and raises a
        ``KiroraWebhookVerificationError`` saying why if one is missing or malformed.

        Takes any mapping of headers, such as Flask's, Django's or Starlette's
        ``request.headers``, or a list of name and value pairs; names are matched without
        case. Verify the request with ``Webhooks.assert_signature()`` before trusting them.
        """
        lookup: Dict[str, str] = {}
        # Starlette's, Werkzeug's and http.server's headers aren't Mappings, but have `items()`.
        given: Any = headers
        items: Iterable[Any] = given.items() if hasattr(given, "items") else given
        for name, value in items:
            if isinstance(value, (list, tuple)):
                value = value[0] if value else None
            if isinstance(value, bytes):
                value = value.decode("latin-1")
            key = name.decode("latin-1").lower() if isinstance(name, bytes) else str(name).lower()
            # The first of a repeated header wins.
            if value is not None and key not in lookup:
                lookup[key] = str(value)
        event = lookup.get("x-webhook-event")
        event_id = lookup.get("x-webhook-event-id")
        timestamp = lookup.get("x-webhook-timestamp")
        signature = lookup.get("x-webhook-signature")
        attempt = lookup.get("x-webhook-attempt", "1")
        if not timestamp:
            raise KiroraWebhookVerificationError("invalid_timestamp", "The timestamp header is missing")
        if not signature:
            raise KiroraWebhookVerificationError("invalid_headers", "The signature header is missing")
        if not event or not event_id:
            raise KiroraWebhookVerificationError("invalid_headers", "The event or event id header is missing")
        # Bounded, so a huge unsigned header is refused rather than make `int()` raise.
        attempts = parse_uint(attempt, 9)
        if attempts is None or attempts < 1 or attempt.startswith("0"):
            raise KiroraWebhookVerificationError(
                "invalid_headers", "The attempt header isn't a whole number from 1 to 999,999,999"
            )
        return WebhookHeaders(
            event=event, event_id=event_id, attempt=attempts, timestamp=timestamp, signature=signature
        )


def _body_bytes(raw_body: RawBody) -> bytes:
    """The request body as received, as bytes."""
    return raw_body.encode() if isinstance(raw_body, str) else bytes(raw_body)


def _unless_refused(check: Callable[[], T]) -> Optional[T]:
    """Returns None for a webhook that fails verification, and raises anything else."""
    try:
        return check()
    except KiroraWebhookVerificationError:
        return None

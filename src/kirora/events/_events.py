from __future__ import annotations

from typing import Optional, cast

from typing_extensions import TypeAlias

from .._base_client import CallOptions, IdempotentCallOptions
from .._resource import APIResource
from ..types import (
    TrackedEvent,
    TrackEventInput,
    TrackEventsBatchInput,
    TrackEventsBatchResult,
)

__all__ = ["Events"]


class Events(APIResource):
    """What your contacts do, which starts journeys and feeds segments."""

    TrackParams: TypeAlias = TrackEventInput
    TrackBatchParams: TypeAlias = TrackEventsBatchInput

    @classmethod
    def track(cls, params: TrackParams, options: Optional[IdempotentCallOptions] = None) -> TrackedEvent:
        """Records an event against a contact, which must already exist. Pass an
        ``idempotency_key`` derived from your own event id, or a retry of yours can record
        it twice. A workspace tracks at most 1,000 distinct names, so keep ids in
        ``properties``."""
        return cast("TrackedEvent", cls._data("POST", "/v1/events/track", options, body=params))

    @classmethod
    def track_batch(
        cls, params: TrackBatchParams, options: Optional[CallOptions] = None
    ) -> TrackEventsBatchResult:
        """Tracks up to 100 events, each as ``track()`` would. One refused doesn't stop
        the rest: each entry of ``results``, in the order sent, has the event or an
        ``error``. Give each entry an ``idempotencyKey`` so your own retries replay it
        rather than record it twice; the SDK gives one to each entry without, for its own
        retries."""
        return cast("TrackEventsBatchResult", cls._data("POST", "/v1/events/batch", options, body=params))

    @classmethod
    async def track_async(
        cls, params: TrackParams, options: Optional[IdempotentCallOptions] = None
    ) -> TrackedEvent:
        """Records an event against a contact, which must already exist. Pass an
        ``idempotency_key`` derived from your own event id, or a retry of yours can record
        it twice. A workspace tracks at most 1,000 distinct names, so keep ids in
        ``properties``.

        The async form of ``Events.track()``."""
        return cast("TrackedEvent", await cls._data_async("POST", "/v1/events/track", options, body=params))

    @classmethod
    async def track_batch_async(
        cls, params: TrackBatchParams, options: Optional[CallOptions] = None
    ) -> TrackEventsBatchResult:
        """Tracks up to 100 events, each as ``track()`` would. One refused doesn't stop
        the rest: each entry of ``results``, in the order sent, has the event or an
        ``error``. Give each entry an ``idempotencyKey`` so your own retries replay it
        rather than record it twice; the SDK gives one to each entry without, for its own
        retries.

        The async form of ``Events.track_batch()``."""
        return cast(
            "TrackEventsBatchResult", await cls._data_async("POST", "/v1/events/batch", options, body=params)
        )

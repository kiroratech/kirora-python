from __future__ import annotations

from typing import Optional, cast

from typing_extensions import TypeAlias

from .._base_client import IdempotentCallOptions
from .._resource import APIResource
from ..types import (
    CreateEmbedSessionInput,
    EmbedSession,
)

__all__ = ["EmbedSessions"]


class EmbedSessions(APIResource):
    """Partner keys only: sessions for embedding Kirora's builders in your app."""

    CreateParams: TypeAlias = CreateEmbedSessionInput

    @classmethod
    def create(cls, params: CreateParams, options: Optional[IdempotentCallOptions] = None) -> EmbedSession:
        """Creates a session for embedding Kirora's segment or email builder, for one
        tenant: call it on your server through ``Kirora(...).for_workspace()``, and give the
        token to the browser. Partner keys with ``allowedOrigins`` only. Reusing an
        ``idempotency_key`` within 24 hours returns the first session again, whose token
        may have expired. Tokens are valid for 15 minutes."""
        return cast("EmbedSession", cls._data("POST", "/v1/embed-sessions", options, body=params))

    @classmethod
    async def create_async(
        cls, params: CreateParams, options: Optional[IdempotentCallOptions] = None
    ) -> EmbedSession:
        """Creates a session for embedding Kirora's segment or email builder, for one
        tenant: call it on your server through ``Kirora(...).for_workspace()``, and give the
        token to the browser. Partner keys with ``allowedOrigins`` only. Reusing an
        ``idempotency_key`` within 24 hours returns the first session again, whose token
        may have expired. Tokens are valid for 15 minutes.

        The async form of ``EmbedSessions.create()``."""
        return cast("EmbedSession", await cls._data_async("POST", "/v1/embed-sessions", options, body=params))

from __future__ import annotations

from typing import Optional, cast

from typing_extensions import TypeAlias

from .._base_client import CallOptions
from .._pagination import AsyncPager, Page
from .._resource import APIResource, path
from ..types import (
    ListMessagesParams,
    OutboundMessage,
)

__all__ = ["Messages"]


class Messages(APIResource):
    """The log of every message sent, from any campaign, journey or transactional send."""

    ListParams: TypeAlias = ListMessagesParams

    @classmethod
    def list(
        cls, params: Optional[ListParams] = None, options: Optional[CallOptions] = None
    ) -> Page[OutboundMessage]:
        """Lists every message sent, queued, skipped or failed, newest first."""
        return cls._page("/v1/messages", options, query=params)

    @classmethod
    def get(cls, message_id: str, options: Optional[CallOptions] = None) -> OutboundMessage:
        """Returns one message, whatever its source and status."""
        return cast("OutboundMessage", cls._data("GET", path("/v1/messages/{}", message_id), options))

    @classmethod
    def list_async(
        cls, params: Optional[ListParams] = None, options: Optional[CallOptions] = None
    ) -> AsyncPager[OutboundMessage]:
        """Lists every message sent, queued, skipped or failed, newest first.

        The async form of ``Messages.list()``."""
        return cls._page_async("/v1/messages", options, query=params)

    @classmethod
    async def get_async(cls, message_id: str, options: Optional[CallOptions] = None) -> OutboundMessage:
        """Returns one message, whatever its source and status.

        The async form of ``Messages.get()``."""
        return cast(
            "OutboundMessage", await cls._data_async("GET", path("/v1/messages/{}", message_id), options)
        )

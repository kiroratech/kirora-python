"""The models of ``Messages``: plain dicts typed with ``TypedDict``s generated from the API spec."""

from ..types import (
    MessageStatus,
    OutboundMessage,
)

__all__ = [
    "OutboundMessage",
    "MessageStatus",
]

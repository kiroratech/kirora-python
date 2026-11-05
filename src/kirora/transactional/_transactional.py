from __future__ import annotations

from typing import Optional, cast

from typing_extensions import TypeAlias

from .._base_client import CallOptions, IdempotentCallOptions
from .._resource import APIResource, path
from ..types import (
    OutboundMessage,
    SendTransactionalInput,
    SendTransactionalMessagesBatchInput,
    SendTransactionalMessagesBatchResult,
    TransactionalSendResult,
)

__all__ = ["Transactional"]


class Transactional(APIResource):
    """One-off messages to one recipient, such as receipts, outside campaigns."""

    SendParams: TypeAlias = SendTransactionalInput
    SendBatchParams: TypeAlias = SendTransactionalMessagesBatchInput

    @classmethod
    def send(
        cls, params: SendParams, options: Optional[IdempotentCallOptions] = None
    ) -> TransactionalSendResult:
        """Sends a one-off message to one recipient, such as a receipt or a password
        reset. It ignores marketing preferences, but not suppressions. A send can succeed
        with a channel left unsent, such as push for a contact without a device: check
        the result's ``skippedChannels``."""
        return cast(
            "TransactionalSendResult", cls._data("POST", "/v1/transactional/messages", options, body=params)
        )

    @classmethod
    def send_batch(
        cls, params: SendBatchParams, options: Optional[CallOptions] = None
    ) -> SendTransactionalMessagesBatchResult:
        """Sends up to 100 messages, each as ``send()`` would. One refused doesn't stop
        the rest: each entry of ``results``, in the order sent, has its messages or an
        ``error``. Give each entry an ``idempotencyKey`` so your own retries replay it
        rather than send it twice."""
        return cast(
            "SendTransactionalMessagesBatchResult",
            cls._data("POST", "/v1/transactional/messages/batch", options, body=params),
        )

    @classmethod
    def cancel(cls, message_id: str, options: Optional[IdempotentCallOptions] = None) -> OutboundMessage:
        """Cancels a message scheduled with ``sendAt`` before it goes. Cancelling it
        again returns it as it is. Once it has started sending, it raises a
        ``KiroraError`` with code ``CONFLICT``."""
        return cast(
            "OutboundMessage",
            cls._data("POST", path("/v1/transactional/messages/{}/cancel", message_id), options),
        )

    @classmethod
    async def send_async(
        cls, params: SendParams, options: Optional[IdempotentCallOptions] = None
    ) -> TransactionalSendResult:
        """Sends a one-off message to one recipient, such as a receipt or a password
        reset. It ignores marketing preferences, but not suppressions. A send can succeed
        with a channel left unsent, such as push for a contact without a device: check
        the result's ``skippedChannels``.

        The async form of ``Transactional.send()``."""
        return cast(
            "TransactionalSendResult",
            await cls._data_async("POST", "/v1/transactional/messages", options, body=params),
        )

    @classmethod
    async def send_batch_async(
        cls, params: SendBatchParams, options: Optional[CallOptions] = None
    ) -> SendTransactionalMessagesBatchResult:
        """Sends up to 100 messages, each as ``send()`` would. One refused doesn't stop
        the rest: each entry of ``results``, in the order sent, has its messages or an
        ``error``. Give each entry an ``idempotencyKey`` so your own retries replay it
        rather than send it twice.

        The async form of ``Transactional.send_batch()``."""
        return cast(
            "SendTransactionalMessagesBatchResult",
            await cls._data_async("POST", "/v1/transactional/messages/batch", options, body=params),
        )

    @classmethod
    async def cancel_async(
        cls, message_id: str, options: Optional[IdempotentCallOptions] = None
    ) -> OutboundMessage:
        """Cancels a message scheduled with ``sendAt`` before it goes. Cancelling it
        again returns it as it is. Once it has started sending, it raises a
        ``KiroraError`` with code ``CONFLICT``.

        The async form of ``Transactional.cancel()``."""
        return cast(
            "OutboundMessage",
            await cls._data_async("POST", path("/v1/transactional/messages/{}/cancel", message_id), options),
        )

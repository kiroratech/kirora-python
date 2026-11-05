from __future__ import annotations

from typing import Optional, cast

from typing_extensions import TypeAlias

from .._base_client import CallOptions, IdempotentCallOptions
from .._pagination import AsyncPager, Page
from .._resource import APIResource
from ..types import (
    AddedSuppressions,
    AddSuppressionsInput,
    DeletedSuppressions,
    DeleteSuppressionsInput,
    ListSuppressionsParams,
    Suppression,
)

__all__ = ["Suppressions"]


class Suppressions(APIResource):
    """Email addresses Kirora won't send to, such as after a bounce."""

    ListParams: TypeAlias = ListSuppressionsParams
    AddParams: TypeAlias = AddSuppressionsInput
    DeleteParams: TypeAlias = DeleteSuppressionsInput

    @classmethod
    def list(
        cls, params: Optional[ListParams] = None, options: Optional[CallOptions] = None
    ) -> Page[Suppression]:
        """Lists the blocked email addresses, newest first. Filter by ``email`` to check
        one."""
        return cls._page("/v1/suppressions", options, query=params)

    @classmethod
    def add(cls, params: AddParams, options: Optional[IdempotentCallOptions] = None) -> AddedSuppressions:
        """Blocks up to 10,000 email addresses, with reason ``imported``. One already
        blocked keeps its reason, and entries that aren't addresses come back in
        ``invalid``."""
        return cast("AddedSuppressions", cls._data("POST", "/v1/suppressions", options, body=params))

    @classmethod
    def delete(
        cls, params: DeleteParams, options: Optional[IdempotentCallOptions] = None
    ) -> DeletedSuppressions:
        """Unblocks up to 100 email addresses. Only ``manual`` and ``imported`` blocks can
        be removed: bounces, complaints and unsubscribes come back in ``notRemovable``."""
        return cast("DeletedSuppressions", cls._data("POST", "/v1/suppressions/delete", options, body=params))

    @classmethod
    def list_async(
        cls, params: Optional[ListParams] = None, options: Optional[CallOptions] = None
    ) -> AsyncPager[Suppression]:
        """Lists the blocked email addresses, newest first. Filter by ``email`` to check
        one.

        The async form of ``Suppressions.list()``."""
        return cls._page_async("/v1/suppressions", options, query=params)

    @classmethod
    async def add_async(
        cls, params: AddParams, options: Optional[IdempotentCallOptions] = None
    ) -> AddedSuppressions:
        """Blocks up to 10,000 email addresses, with reason ``imported``. One already
        blocked keeps its reason, and entries that aren't addresses come back in
        ``invalid``.

        The async form of ``Suppressions.add()``."""
        return cast(
            "AddedSuppressions", await cls._data_async("POST", "/v1/suppressions", options, body=params)
        )

    @classmethod
    async def delete_async(
        cls, params: DeleteParams, options: Optional[IdempotentCallOptions] = None
    ) -> DeletedSuppressions:
        """Unblocks up to 100 email addresses. Only ``manual`` and ``imported`` blocks can
        be removed: bounces, complaints and unsubscribes come back in ``notRemovable``.

        The async form of ``Suppressions.delete()``."""
        return cast(
            "DeletedSuppressions",
            await cls._data_async("POST", "/v1/suppressions/delete", options, body=params),
        )

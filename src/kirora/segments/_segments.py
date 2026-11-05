from __future__ import annotations

from typing import Optional, cast

from typing_extensions import TypeAlias

from .._base_client import CallOptions, IdempotentCallOptions
from .._pagination import AsyncPager, Page
from .._resource import APIResource, path
from ..types import (
    ContactDetail,
    CreateSegmentInput,
    GetSegmentSizeHistoryParams,
    ListSegmentContactsParams,
    ListSegmentMembershipChangesParams,
    ListSegmentsParams,
    Segment,
    SegmentPreviewInput,
    SegmentPreviewResult,
    SegmentSizeHistory,
    SegmentUsage,
    UpdateSegmentInput,
)

__all__ = ["Segments"]


class Segments(APIResource):
    """Audiences defined by rules, which each send evaluates live. Their stored
    membership, behind ``memberCount`` and ``Contacts.list({"segmentId": ...})``, is
    re-evaluated about every 15 minutes."""

    ListParams: TypeAlias = ListSegmentsParams
    CreateParams: TypeAlias = CreateSegmentInput
    UpdateParams: TypeAlias = UpdateSegmentInput
    PreviewParams: TypeAlias = SegmentPreviewInput
    ListContactsParams: TypeAlias = ListSegmentContactsParams
    ListMembershipChangesParams: TypeAlias = ListSegmentMembershipChangesParams
    SizeHistoryParams: TypeAlias = GetSegmentSizeHistoryParams

    @classmethod
    def list(
        cls, params: Optional[ListParams] = None, options: Optional[CallOptions] = None
    ) -> Page[Segment]:
        """Lists the workspace's segments, newest first."""
        return cls._page("/v1/segments", options, query=params)

    @classmethod
    def get(cls, segment_id: str, options: Optional[CallOptions] = None) -> Segment:
        """Returns one segment, with its rules and ``memberCount``, its size as last
        evaluated."""
        return cast("Segment", cls._data("GET", path("/v1/segments/{}", segment_id), options))

    @classmethod
    def create(cls, params: CreateParams, options: Optional[IdempotentCallOptions] = None) -> Segment:
        """Creates a segment from rules. Check what the rules match first with
        ``preview()``. Names are unique in the workspace: a repeated one raises a
        ``KiroraError`` with code ``ALREADY_EXISTS``."""
        return cast("Segment", cls._data("POST", "/v1/segments", options, body=params))

    @classmethod
    def update(cls, segment_id: str, params: UpdateParams, options: Optional[CallOptions] = None) -> Segment:
        """Replaces a segment's rules, or renames it or changes its description. New
        rules apply from the next evaluation; campaigns already sent are unaffected."""
        return cast("Segment", cls._data("PATCH", path("/v1/segments/{}", segment_id), options, body=params))

    @classmethod
    def delete(cls, segment_id: str, options: Optional[CallOptions] = None) -> None:
        """Deletes a segment, keeping its contacts. While a campaign, journey or other
        segment uses it, it raises a ``KiroraError`` with code ``IN_USE``, naming them in
        ``details``; ``usage()`` lists them beforehand."""
        cls._remove(path("/v1/segments/{}", segment_id), options)

    @classmethod
    def preview(cls, params: PreviewParams, options: Optional[CallOptions] = None) -> SegmentPreviewResult:
        """Counts how many contacts unsaved rules would match, live up to 10,000, and how
        many of them email and push can reach. Nothing is saved."""
        return cast("SegmentPreviewResult", cls._data("POST", "/v1/segments/preview", options, body=params))

    @classmethod
    def list_contacts(
        cls,
        segment_id: str,
        params: Optional[ListContactsParams] = None,
        options: Optional[CallOptions] = None,
    ) -> Page[ContactDetail]:
        """Evaluates a segment now and lists the contacts it matches: who a send would
        reach. ``Contacts.list({"segmentId": ...})`` reads the stored membership instead, up
        to about 15 minutes behind, with the contact filters."""
        return cls._page(path("/v1/segments/{}/contacts", segment_id), options, query=params)

    @classmethod
    def list_membership_changes(
        cls, segment_id: str, params: ListMembershipChangesParams, options: Optional[CallOptions] = None
    ) -> Page[ContactDetail]:
        """Lists the contacts who joined or left the segment on ``day``, in the
        workspace's timezone, newest first. The first page's ``meta["count"]`` is that
        day's total."""
        return cls._page(path("/v1/segments/{}/membership-changes", segment_id), options, query=params)

    @classmethod
    def size_history(
        cls,
        segment_id: str,
        params: Optional[SizeHistoryParams] = None,
        options: Optional[CallOptions] = None,
    ) -> SegmentSizeHistory:
        """Returns the segment's size each day in the window, as the background count
        last found it that day."""
        return cast(
            "SegmentSizeHistory",
            cls._data("GET", path("/v1/segments/{}/size-history", segment_id), options, query=params),
        )

    @classmethod
    def usage(cls, segment_id: str, options: Optional[CallOptions] = None) -> SegmentUsage:
        """Returns what uses the segment: campaigns, journeys and other segments, up to
        50 of each. Check it before ``delete()``."""
        return cast("SegmentUsage", cls._data("GET", path("/v1/segments/{}/usage", segment_id), options))

    @classmethod
    def list_async(
        cls, params: Optional[ListParams] = None, options: Optional[CallOptions] = None
    ) -> AsyncPager[Segment]:
        """Lists the workspace's segments, newest first.

        The async form of ``Segments.list()``."""
        return cls._page_async("/v1/segments", options, query=params)

    @classmethod
    async def get_async(cls, segment_id: str, options: Optional[CallOptions] = None) -> Segment:
        """Returns one segment, with its rules and ``memberCount``, its size as last
        evaluated.

        The async form of ``Segments.get()``."""
        return cast("Segment", await cls._data_async("GET", path("/v1/segments/{}", segment_id), options))

    @classmethod
    async def create_async(
        cls, params: CreateParams, options: Optional[IdempotentCallOptions] = None
    ) -> Segment:
        """Creates a segment from rules. Check what the rules match first with
        ``preview()``. Names are unique in the workspace: a repeated one raises a
        ``KiroraError`` with code ``ALREADY_EXISTS``.

        The async form of ``Segments.create()``."""
        return cast("Segment", await cls._data_async("POST", "/v1/segments", options, body=params))

    @classmethod
    async def update_async(
        cls, segment_id: str, params: UpdateParams, options: Optional[CallOptions] = None
    ) -> Segment:
        """Replaces a segment's rules, or renames it or changes its description. New
        rules apply from the next evaluation; campaigns already sent are unaffected.

        The async form of ``Segments.update()``."""
        return cast(
            "Segment",
            await cls._data_async("PATCH", path("/v1/segments/{}", segment_id), options, body=params),
        )

    @classmethod
    async def delete_async(cls, segment_id: str, options: Optional[CallOptions] = None) -> None:
        """Deletes a segment, keeping its contacts. While a campaign, journey or other
        segment uses it, it raises a ``KiroraError`` with code ``IN_USE``, naming them in
        ``details``; ``usage()`` lists them beforehand.

        The async form of ``Segments.delete()``."""
        await cls._remove_async(path("/v1/segments/{}", segment_id), options)

    @classmethod
    async def preview_async(
        cls, params: PreviewParams, options: Optional[CallOptions] = None
    ) -> SegmentPreviewResult:
        """Counts how many contacts unsaved rules would match, live up to 10,000, and how
        many of them email and push can reach. Nothing is saved.

        The async form of ``Segments.preview()``."""
        return cast(
            "SegmentPreviewResult",
            await cls._data_async("POST", "/v1/segments/preview", options, body=params),
        )

    @classmethod
    def list_contacts_async(
        cls,
        segment_id: str,
        params: Optional[ListContactsParams] = None,
        options: Optional[CallOptions] = None,
    ) -> AsyncPager[ContactDetail]:
        """Evaluates a segment now and lists the contacts it matches: who a send would
        reach. ``Contacts.list({"segmentId": ...})`` reads the stored membership instead, up
        to about 15 minutes behind, with the contact filters.

        The async form of ``Segments.list_contacts()``."""
        return cls._page_async(path("/v1/segments/{}/contacts", segment_id), options, query=params)

    @classmethod
    def list_membership_changes_async(
        cls, segment_id: str, params: ListMembershipChangesParams, options: Optional[CallOptions] = None
    ) -> AsyncPager[ContactDetail]:
        """Lists the contacts who joined or left the segment on ``day``, in the
        workspace's timezone, newest first. The first page's ``meta["count"]`` is that
        day's total.

        The async form of ``Segments.list_membership_changes()``."""
        return cls._page_async(path("/v1/segments/{}/membership-changes", segment_id), options, query=params)

    @classmethod
    async def size_history_async(
        cls,
        segment_id: str,
        params: Optional[SizeHistoryParams] = None,
        options: Optional[CallOptions] = None,
    ) -> SegmentSizeHistory:
        """Returns the segment's size each day in the window, as the background count
        last found it that day.

        The async form of ``Segments.size_history()``."""
        return cast(
            "SegmentSizeHistory",
            await cls._data_async(
                "GET", path("/v1/segments/{}/size-history", segment_id), options, query=params
            ),
        )

    @classmethod
    async def usage_async(cls, segment_id: str, options: Optional[CallOptions] = None) -> SegmentUsage:
        """Returns what uses the segment: campaigns, journeys and other segments, up to
        50 of each. Check it before ``delete()``.

        The async form of ``Segments.usage()``."""
        return cast(
            "SegmentUsage", await cls._data_async("GET", path("/v1/segments/{}/usage", segment_id), options)
        )

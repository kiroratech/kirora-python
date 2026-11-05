from __future__ import annotations

from typing import Optional, cast

from typing_extensions import TypeAlias

from .._base_client import CallOptions, IdempotentCallOptions
from .._pagination import AsyncPager, Page
from .._resource import APIResource, path
from ..types import (
    Campaign,
    CampaignEligibility,
    CampaignListItem,
    CreateCampaignInput,
    ListCampaignsParams,
    ScheduleCampaignInput,
    TriggerCampaignInput,
    TriggeredCampaign,
)

__all__ = ["Campaigns"]


class Campaigns(APIResource):
    """Messages sent once to an audience, by email, push or both."""

    ListParams: TypeAlias = ListCampaignsParams
    CreateParams: TypeAlias = CreateCampaignInput
    TriggerParams: TypeAlias = TriggerCampaignInput
    ScheduleParams: TypeAlias = ScheduleCampaignInput

    @classmethod
    def list(
        cls, params: Optional[ListParams] = None, options: Optional[CallOptions] = None
    ) -> Page[CampaignListItem]:
        """Lists campaigns, newest first. Pass ``status`` to list only those in that
        state."""
        return cls._page("/v1/campaigns", options, query=params)

    @classmethod
    def get(cls, campaign_id: str, options: Optional[CallOptions] = None) -> Campaign:
        """Returns one campaign, with its content and audience."""
        return cast("Campaign", cls._data("GET", path("/v1/campaigns/{}", campaign_id), options))

    @classmethod
    def create(cls, params: CreateParams, options: Optional[IdempotentCallOptions] = None) -> Campaign:
        """Creates a campaign as a draft. Only ``name`` is required, so a draft can be
        saved unfinished; nothing is sent until ``send()`` or ``schedule()``."""
        return cast("Campaign", cls._data("POST", "/v1/campaigns", options, body=params))

    @classmethod
    def send(cls, campaign_id: str, options: Optional[IdempotentCallOptions] = None) -> Campaign:
        """Sends a campaign now. A campaign is sent at most once: sending one that has
        already gone returns it again. An unfinished draft raises a ``KiroraError`` with
        code ``DRAFT_INCOMPLETE``, listing each missing field in ``errors``."""
        return cast("Campaign", cls._data("POST", path("/v1/campaigns/{}/send", campaign_id), options))

    @classmethod
    def trigger(
        cls, campaign_id: str, params: TriggerParams, options: Optional[IdempotentCallOptions] = None
    ) -> TriggeredCampaign:
        """Sends a draft now, once, to up to 5,000 ``recipients`` instead of its saved
        audience, each with their own ``data``. Recipients that name no contact come back
        in ``notFound``."""
        return cast(
            "TriggeredCampaign",
            cls._data("POST", path("/v1/campaigns/{}/trigger", campaign_id), options, body=params),
        )

    @classmethod
    def schedule(
        cls, campaign_id: str, params: ScheduleParams, options: Optional[IdempotentCallOptions] = None
    ) -> Campaign:
        """Schedules a draft, or moves a scheduled campaign that hasn't started sending
        to a new time. Raises a ``KiroraError`` with code ``DRAFT_INCOMPLETE`` for an
        unfinished draft, or ``INVALID_SCHEDULE`` for a fixed time that has passed."""
        return cast(
            "Campaign",
            cls._data("POST", path("/v1/campaigns/{}/schedule", campaign_id), options, body=params),
        )

    @classmethod
    def eligibility(cls, campaign_id: str, options: Optional[CallOptions] = None) -> CampaignEligibility:
        """Reports what would stop a campaign sending, without sending it. Call it
        before ``send()`` to find out what to fix."""
        return cast(
            "CampaignEligibility",
            cls._data("GET", path("/v1/campaigns/{}/eligibility", campaign_id), options),
        )

    @classmethod
    def list_async(
        cls, params: Optional[ListParams] = None, options: Optional[CallOptions] = None
    ) -> AsyncPager[CampaignListItem]:
        """Lists campaigns, newest first. Pass ``status`` to list only those in that
        state.

        The async form of ``Campaigns.list()``."""
        return cls._page_async("/v1/campaigns", options, query=params)

    @classmethod
    async def get_async(cls, campaign_id: str, options: Optional[CallOptions] = None) -> Campaign:
        """Returns one campaign, with its content and audience.

        The async form of ``Campaigns.get()``."""
        return cast("Campaign", await cls._data_async("GET", path("/v1/campaigns/{}", campaign_id), options))

    @classmethod
    async def create_async(
        cls, params: CreateParams, options: Optional[IdempotentCallOptions] = None
    ) -> Campaign:
        """Creates a campaign as a draft. Only ``name`` is required, so a draft can be
        saved unfinished; nothing is sent until ``send()`` or ``schedule()``.

        The async form of ``Campaigns.create()``."""
        return cast("Campaign", await cls._data_async("POST", "/v1/campaigns", options, body=params))

    @classmethod
    async def send_async(cls, campaign_id: str, options: Optional[IdempotentCallOptions] = None) -> Campaign:
        """Sends a campaign now. A campaign is sent at most once: sending one that has
        already gone returns it again. An unfinished draft raises a ``KiroraError`` with
        code ``DRAFT_INCOMPLETE``, listing each missing field in ``errors``.

        The async form of ``Campaigns.send()``."""
        return cast(
            "Campaign", await cls._data_async("POST", path("/v1/campaigns/{}/send", campaign_id), options)
        )

    @classmethod
    async def trigger_async(
        cls, campaign_id: str, params: TriggerParams, options: Optional[IdempotentCallOptions] = None
    ) -> TriggeredCampaign:
        """Sends a draft now, once, to up to 5,000 ``recipients`` instead of its saved
        audience, each with their own ``data``. Recipients that name no contact come back
        in ``notFound``.

        The async form of ``Campaigns.trigger()``."""
        return cast(
            "TriggeredCampaign",
            await cls._data_async(
                "POST", path("/v1/campaigns/{}/trigger", campaign_id), options, body=params
            ),
        )

    @classmethod
    async def schedule_async(
        cls, campaign_id: str, params: ScheduleParams, options: Optional[IdempotentCallOptions] = None
    ) -> Campaign:
        """Schedules a draft, or moves a scheduled campaign that hasn't started sending
        to a new time. Raises a ``KiroraError`` with code ``DRAFT_INCOMPLETE`` for an
        unfinished draft, or ``INVALID_SCHEDULE`` for a fixed time that has passed.

        The async form of ``Campaigns.schedule()``."""
        return cast(
            "Campaign",
            await cls._data_async(
                "POST", path("/v1/campaigns/{}/schedule", campaign_id), options, body=params
            ),
        )

    @classmethod
    async def eligibility_async(
        cls, campaign_id: str, options: Optional[CallOptions] = None
    ) -> CampaignEligibility:
        """Reports what would stop a campaign sending, without sending it. Call it
        before ``send()`` to find out what to fix.

        The async form of ``Campaigns.eligibility()``."""
        return cast(
            "CampaignEligibility",
            await cls._data_async("GET", path("/v1/campaigns/{}/eligibility", campaign_id), options),
        )

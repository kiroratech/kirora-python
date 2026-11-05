"""The models of ``Campaigns``: plain dicts typed with ``TypedDict``s generated from the API spec."""

from ..types import (
    Campaign,
    CampaignEligibility,
    CampaignListItem,
    CampaignStatus,
    TriggeredCampaign,
)

__all__ = [
    "Campaign",
    "CampaignListItem",
    "CampaignEligibility",
    "CampaignStatus",
    "TriggeredCampaign",
]

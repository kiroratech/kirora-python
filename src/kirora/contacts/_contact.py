"""The models of ``Contacts``: plain dicts typed with ``TypedDict``s generated from the API spec."""

from ..types import (
    Contact,
    ContactDataExport,
    ContactDetail,
    ContactListMembership,
    ContactListMeta,
    ContactSegment,
    ContactTopic,
    DeleteContactsResult,
    IdentifyContactsBatchResult,
    PushInstallation,
)

__all__ = [
    "Contact",
    "ContactDetail",
    "ContactListMeta",
    "ContactDataExport",
    "ContactListMembership",
    "ContactSegment",
    "ContactTopic",
    "PushInstallation",
    "IdentifyContactsBatchResult",
    "DeleteContactsResult",
]

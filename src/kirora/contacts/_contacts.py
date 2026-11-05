from __future__ import annotations

from typing import List, Optional, cast

from typing_extensions import Literal, TypeAlias

from .._base_client import CallOptions, IdempotentCallOptions
from .._pagination import AsyncPager, Page
from .._resource import APIResource, path, with_id_type
from ..types import (
    ContactDataExport,
    ContactDetail,
    ContactListMembership,
    ContactSegment,
    ContactTopic,
    DeleteContactsInput,
    DeleteContactsResult,
    IdentifyContactInput,
    IdentifyContactsBatchInput,
    IdentifyContactsBatchResult,
    ListContactListsParams,
    ListContactSegmentsParams,
    ListContactsParams,
    ListPushInstallationsParams,
    MergeContactInput,
    PushInstallation,
    RegisterPushInstallationInput,
    SetContactTopicInput,
    UpdateContactInput,
)

__all__ = ["Contacts"]


class Contacts(APIResource):
    """The people you send to."""

    IdType: TypeAlias = Literal["id", "externalId", "email"]
    """What a contact id names: Kirora's id (the default), your ``externalId``, or the
    contact's email address."""
    ListParams: TypeAlias = ListContactsParams
    UpdateParams: TypeAlias = UpdateContactInput
    IdentifyParams: TypeAlias = IdentifyContactInput
    IdentifyBatchParams: TypeAlias = IdentifyContactsBatchInput
    DeleteBatchParams: TypeAlias = DeleteContactsInput
    MergeParams: TypeAlias = MergeContactInput
    ListListsParams: TypeAlias = ListContactListsParams
    ListSegmentsParams: TypeAlias = ListContactSegmentsParams
    SetTopicParams: TypeAlias = SetContactTopicInput
    ListInstallationsParams: TypeAlias = ListPushInstallationsParams
    RegisterInstallationParams: TypeAlias = RegisterPushInstallationInput

    @classmethod
    def list(
        cls, params: Optional[ListParams] = None, options: Optional[CallOptions] = None
    ) -> Page[ContactDetail]:
        """Lists contacts, newest first. The first page's ``meta["count"]`` counts every
        match, up to 10,000. Iterate the page for every contact."""
        return cls._page("/v1/contacts", options, query=params)

    @classmethod
    def get(
        cls, contact_id: str, options: Optional[CallOptions] = None, *, id_type: Optional[IdType] = None
    ) -> ContactDetail:
        """Returns one contact, by Kirora's id, or by your ``externalId`` or email address
        with ``id_type``."""
        return cast(
            "ContactDetail",
            cls._data("GET", path("/v1/contacts/{}", contact_id), options, query=with_id_type(id_type)),
        )

    @classmethod
    def update(
        cls,
        contact_id: str,
        params: UpdateParams,
        options: Optional[CallOptions] = None,
        *,
        id_type: Optional[IdType] = None,
    ) -> ContactDetail:
        """Updates a contact. Fields left out are unchanged, ``attributes`` merge key by
        key, and a key set to None is removed. Granting consent needs
        ``consent.statement``. An update that changes the ``externalId`` or email the
        contact is looked up by isn't retried after a network error or a 5xx."""
        return cast(
            "ContactDetail",
            cls._data(
                "PATCH",
                path("/v1/contacts/{}", contact_id),
                options,
                query=with_id_type(id_type),
                body=params,
            ),
        )

    @classmethod
    def delete(
        cls, contact_id: str, options: Optional[CallOptions] = None, *, id_type: Optional[IdType] = None
    ) -> None:
        """Deletes a contact and its data, for a right-to-erasure request. It can't be
        undone. While a message to the contact is being sent, it raises a ``KiroraError``
        with code ``CONTACT_SEND_IN_PROGRESS``; retry shortly."""
        cls._remove(path("/v1/contacts/{}", contact_id), options, query=with_id_type(id_type))

    @classmethod
    def identify(
        cls, params: IdentifyParams, options: Optional[IdempotentCallOptions] = None
    ) -> ContactDetail:
        """Creates or updates a contact, matched by ``externalId``, then ``email``, then
        ``phone``; give at least one. Consent flags left out keep their value, and
        granting consent needs ``consent.statement``. Identifiers that name two different
        contacts raise a ``KiroraError`` with code ``CONFLICT``."""
        return cast("ContactDetail", cls._data("POST", "/v1/contacts/identify", options, body=params))

    @classmethod
    def identify_batch(
        cls, params: IdentifyBatchParams, options: Optional[IdempotentCallOptions] = None
    ) -> IdentifyContactsBatchResult:
        """Identifies up to 100 contacts, each as ``identify()`` would. One refused
        doesn't stop the rest: each entry of ``results``, in the order sent, has the
        contact or an ``error``."""
        return cast(
            "IdentifyContactsBatchResult", cls._data("POST", "/v1/contacts/batch", options, body=params)
        )

    @classmethod
    def delete_batch(
        cls, params: DeleteBatchParams, options: Optional[IdempotentCallOptions] = None
    ) -> DeleteContactsResult:
        """Deletes up to 100 contacts, each as ``delete()`` would, with an ``outcome`` for
        each. Retry those that are ``send_in_progress`` shortly."""
        return cast("DeleteContactsResult", cls._data("POST", "/v1/contacts/delete", options, body=params))

    @classmethod
    def merge(
        cls,
        contact_id: str,
        params: MergeParams,
        options: Optional[IdempotentCallOptions] = None,
        *,
        id_type: Optional[IdType] = None,
    ) -> ContactDetail:
        """Merges this contact, a duplicate, into the one ``keep`` names, then deletes
        it. Returns the kept contact. It can't be undone."""
        return cast(
            "ContactDetail",
            cls._data(
                "POST",
                path("/v1/contacts/{}/merge", contact_id),
                options,
                query=with_id_type(id_type),
                body=params,
            ),
        )

    @classmethod
    def export(
        cls, contact_id: str, options: Optional[CallOptions] = None, *, id_type: Optional[IdType] = None
    ) -> ContactDataExport:
        """Returns everything held about one contact, for a right-of-access request."""
        return cast(
            "ContactDataExport",
            cls._data(
                "GET", path("/v1/contacts/{}/export", contact_id), options, query=with_id_type(id_type)
            ),
        )

    @classmethod
    def list_lists(
        cls,
        contact_id: str,
        params: Optional[ListListsParams] = None,
        options: Optional[CallOptions] = None,
        *,
        id_type: Optional[IdType] = None,
    ) -> Page[ContactListMembership]:
        """Lists the lists a contact is in, with when they joined each."""
        return cls._page(
            path("/v1/contacts/{}/lists", contact_id), options, query=with_id_type(id_type, params)
        )

    @classmethod
    def list_segments(
        cls,
        contact_id: str,
        params: Optional[ListSegmentsParams] = None,
        options: Optional[CallOptions] = None,
        *,
        id_type: Optional[IdType] = None,
    ) -> Page[ContactSegment]:
        """Lists the segments a contact is in, from the stored membership, which is up
        to about 15 minutes behind."""
        return cls._page(
            path("/v1/contacts/{}/segments", contact_id), options, query=with_id_type(id_type, params)
        )

    @classmethod
    def list_topics(
        cls, contact_id: str, options: Optional[CallOptions] = None, *, id_type: Optional[IdType] = None
    ) -> List[ContactTopic]:
        """Returns every topic, with whether it reaches this contact: all of them at
        once, not a page."""
        return cast(
            "List[ContactTopic]",
            cls._data(
                "GET", path("/v1/contacts/{}/topics", contact_id), options, query=with_id_type(id_type)
            ),
        )

    @classmethod
    def set_topic(
        cls,
        contact_id: str,
        topic_id: str,
        params: SetTopicParams,
        options: Optional[CallOptions] = None,
        *,
        id_type: Optional[IdType] = None,
    ) -> ContactTopic:
        """Joins a contact to a topic or takes them out of it, on every channel or on
        each one named. Joining needs ``statement``, how the contact agreed."""
        return cast(
            "ContactTopic",
            cls._data(
                "PUT",
                path("/v1/contacts/{}/topics/{}", contact_id, topic_id),
                options,
                query=with_id_type(id_type),
                body=params,
            ),
        )

    @classmethod
    def list_installations(
        cls,
        contact_id: str,
        params: Optional[ListInstallationsParams] = None,
        options: Optional[CallOptions] = None,
        *,
        id_type: Optional[IdType] = None,
    ) -> Page[PushInstallation]:
        """Lists the devices and browsers registered for push to a contact, newest
        first, inactive ones included."""
        return cls._page(
            path("/v1/contacts/{}/installations", contact_id), options, query=with_id_type(id_type, params)
        )

    @classmethod
    def register_installation(
        cls,
        contact_id: str,
        params: RegisterInstallationParams,
        options: Optional[IdempotentCallOptions] = None,
        *,
        id_type: Optional[IdType] = None,
    ) -> PushInstallation:
        """Registers a device or browser for push to a contact. Registering the same
        token again updates the installation."""
        return cast(
            "PushInstallation",
            cls._data(
                "POST",
                path("/v1/contacts/{}/installations", contact_id),
                options,
                query=with_id_type(id_type),
                body=params,
            ),
        )

    @classmethod
    def delete_installation(
        cls,
        contact_id: str,
        external_installation_id: str,
        options: Optional[CallOptions] = None,
        *,
        id_type: Optional[IdType] = None,
    ) -> None:
        """Stops push to a contact's device, such as on sign-out. The installation is
        kept, inactive, and registering it again turns it back on."""
        cls._remove(
            path("/v1/contacts/{}/installations/{}", contact_id, external_installation_id),
            options,
            query=with_id_type(id_type),
        )

    @classmethod
    def list_async(
        cls, params: Optional[ListParams] = None, options: Optional[CallOptions] = None
    ) -> AsyncPager[ContactDetail]:
        """Lists contacts, newest first. The first page's ``meta["count"]`` counts every
        match, up to 10,000. Iterate the page for every contact.

        The async form of ``Contacts.list()``."""
        return cls._page_async("/v1/contacts", options, query=params)

    @classmethod
    async def get_async(
        cls, contact_id: str, options: Optional[CallOptions] = None, *, id_type: Optional[IdType] = None
    ) -> ContactDetail:
        """Returns one contact, by Kirora's id, or by your ``externalId`` or email address
        with ``id_type``.

        The async form of ``Contacts.get()``."""
        return cast(
            "ContactDetail",
            await cls._data_async(
                "GET", path("/v1/contacts/{}", contact_id), options, query=with_id_type(id_type)
            ),
        )

    @classmethod
    async def update_async(
        cls,
        contact_id: str,
        params: UpdateParams,
        options: Optional[CallOptions] = None,
        *,
        id_type: Optional[IdType] = None,
    ) -> ContactDetail:
        """Updates a contact. Fields left out are unchanged, ``attributes`` merge key by
        key, and a key set to None is removed. Granting consent needs
        ``consent.statement``. An update that changes the ``externalId`` or email the
        contact is looked up by isn't retried after a network error or a 5xx.

        The async form of ``Contacts.update()``."""
        return cast(
            "ContactDetail",
            await cls._data_async(
                "PATCH",
                path("/v1/contacts/{}", contact_id),
                options,
                query=with_id_type(id_type),
                body=params,
            ),
        )

    @classmethod
    async def delete_async(
        cls, contact_id: str, options: Optional[CallOptions] = None, *, id_type: Optional[IdType] = None
    ) -> None:
        """Deletes a contact and its data, for a right-to-erasure request. It can't be
        undone. While a message to the contact is being sent, it raises a ``KiroraError``
        with code ``CONTACT_SEND_IN_PROGRESS``; retry shortly.

        The async form of ``Contacts.delete()``."""
        await cls._remove_async(path("/v1/contacts/{}", contact_id), options, query=with_id_type(id_type))

    @classmethod
    async def identify_async(
        cls, params: IdentifyParams, options: Optional[IdempotentCallOptions] = None
    ) -> ContactDetail:
        """Creates or updates a contact, matched by ``externalId``, then ``email``, then
        ``phone``; give at least one. Consent flags left out keep their value, and
        granting consent needs ``consent.statement``. Identifiers that name two different
        contacts raise a ``KiroraError`` with code ``CONFLICT``.

        The async form of ``Contacts.identify()``."""
        return cast(
            "ContactDetail", await cls._data_async("POST", "/v1/contacts/identify", options, body=params)
        )

    @classmethod
    async def identify_batch_async(
        cls, params: IdentifyBatchParams, options: Optional[IdempotentCallOptions] = None
    ) -> IdentifyContactsBatchResult:
        """Identifies up to 100 contacts, each as ``identify()`` would. One refused
        doesn't stop the rest: each entry of ``results``, in the order sent, has the
        contact or an ``error``.

        The async form of ``Contacts.identify_batch()``."""
        return cast(
            "IdentifyContactsBatchResult",
            await cls._data_async("POST", "/v1/contacts/batch", options, body=params),
        )

    @classmethod
    async def delete_batch_async(
        cls, params: DeleteBatchParams, options: Optional[IdempotentCallOptions] = None
    ) -> DeleteContactsResult:
        """Deletes up to 100 contacts, each as ``delete()`` would, with an ``outcome`` for
        each. Retry those that are ``send_in_progress`` shortly.

        The async form of ``Contacts.delete_batch()``."""
        return cast(
            "DeleteContactsResult", await cls._data_async("POST", "/v1/contacts/delete", options, body=params)
        )

    @classmethod
    async def merge_async(
        cls,
        contact_id: str,
        params: MergeParams,
        options: Optional[IdempotentCallOptions] = None,
        *,
        id_type: Optional[IdType] = None,
    ) -> ContactDetail:
        """Merges this contact, a duplicate, into the one ``keep`` names, then deletes
        it. Returns the kept contact. It can't be undone.

        The async form of ``Contacts.merge()``."""
        return cast(
            "ContactDetail",
            await cls._data_async(
                "POST",
                path("/v1/contacts/{}/merge", contact_id),
                options,
                query=with_id_type(id_type),
                body=params,
            ),
        )

    @classmethod
    async def export_async(
        cls, contact_id: str, options: Optional[CallOptions] = None, *, id_type: Optional[IdType] = None
    ) -> ContactDataExport:
        """Returns everything held about one contact, for a right-of-access request.

        The async form of ``Contacts.export()``."""
        return cast(
            "ContactDataExport",
            await cls._data_async(
                "GET", path("/v1/contacts/{}/export", contact_id), options, query=with_id_type(id_type)
            ),
        )

    @classmethod
    def list_lists_async(
        cls,
        contact_id: str,
        params: Optional[ListListsParams] = None,
        options: Optional[CallOptions] = None,
        *,
        id_type: Optional[IdType] = None,
    ) -> AsyncPager[ContactListMembership]:
        """Lists the lists a contact is in, with when they joined each.

        The async form of ``Contacts.list_lists()``."""
        return cls._page_async(
            path("/v1/contacts/{}/lists", contact_id), options, query=with_id_type(id_type, params)
        )

    @classmethod
    def list_segments_async(
        cls,
        contact_id: str,
        params: Optional[ListSegmentsParams] = None,
        options: Optional[CallOptions] = None,
        *,
        id_type: Optional[IdType] = None,
    ) -> AsyncPager[ContactSegment]:
        """Lists the segments a contact is in, from the stored membership, which is up
        to about 15 minutes behind.

        The async form of ``Contacts.list_segments()``."""
        return cls._page_async(
            path("/v1/contacts/{}/segments", contact_id), options, query=with_id_type(id_type, params)
        )

    @classmethod
    async def list_topics_async(
        cls, contact_id: str, options: Optional[CallOptions] = None, *, id_type: Optional[IdType] = None
    ) -> List[ContactTopic]:
        """Returns every topic, with whether it reaches this contact: all of them at
        once, not a page.

        The async form of ``Contacts.list_topics()``."""
        return cast(
            "List[ContactTopic]",
            await cls._data_async(
                "GET", path("/v1/contacts/{}/topics", contact_id), options, query=with_id_type(id_type)
            ),
        )

    @classmethod
    async def set_topic_async(
        cls,
        contact_id: str,
        topic_id: str,
        params: SetTopicParams,
        options: Optional[CallOptions] = None,
        *,
        id_type: Optional[IdType] = None,
    ) -> ContactTopic:
        """Joins a contact to a topic or takes them out of it, on every channel or on
        each one named. Joining needs ``statement``, how the contact agreed.

        The async form of ``Contacts.set_topic()``."""
        return cast(
            "ContactTopic",
            await cls._data_async(
                "PUT",
                path("/v1/contacts/{}/topics/{}", contact_id, topic_id),
                options,
                query=with_id_type(id_type),
                body=params,
            ),
        )

    @classmethod
    def list_installations_async(
        cls,
        contact_id: str,
        params: Optional[ListInstallationsParams] = None,
        options: Optional[CallOptions] = None,
        *,
        id_type: Optional[IdType] = None,
    ) -> AsyncPager[PushInstallation]:
        """Lists the devices and browsers registered for push to a contact, newest
        first, inactive ones included.

        The async form of ``Contacts.list_installations()``."""
        return cls._page_async(
            path("/v1/contacts/{}/installations", contact_id), options, query=with_id_type(id_type, params)
        )

    @classmethod
    async def register_installation_async(
        cls,
        contact_id: str,
        params: RegisterInstallationParams,
        options: Optional[IdempotentCallOptions] = None,
        *,
        id_type: Optional[IdType] = None,
    ) -> PushInstallation:
        """Registers a device or browser for push to a contact. Registering the same
        token again updates the installation.

        The async form of ``Contacts.register_installation()``."""
        return cast(
            "PushInstallation",
            await cls._data_async(
                "POST",
                path("/v1/contacts/{}/installations", contact_id),
                options,
                query=with_id_type(id_type),
                body=params,
            ),
        )

    @classmethod
    async def delete_installation_async(
        cls,
        contact_id: str,
        external_installation_id: str,
        options: Optional[CallOptions] = None,
        *,
        id_type: Optional[IdType] = None,
    ) -> None:
        """Stops push to a contact's device, such as on sign-out. The installation is
        kept, inactive, and registering it again turns it back on.

        The async form of ``Contacts.delete_installation()``."""
        await cls._remove_async(
            path("/v1/contacts/{}/installations/{}", contact_id, external_installation_id),
            options,
            query=with_id_type(id_type),
        )

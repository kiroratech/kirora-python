from __future__ import annotations

from typing import Optional, cast

from typing_extensions import TypeAlias

from .._base_client import CallOptions, IdempotentCallOptions
from .._pagination import AsyncPager, Page
from .._resource import APIResource, path
from ..types import (
    AddedListContacts,
    CreateListInput,
    DeletedListContacts,
    List,
    ListContactsInput,
    ListListsParams,
    UpdateListInput,
)

__all__ = ["Lists"]


class Lists(APIResource):
    """Static lists of contacts, whose members you add and remove yourself."""

    ListParams: TypeAlias = ListListsParams
    CreateParams: TypeAlias = CreateListInput
    UpdateParams: TypeAlias = UpdateListInput
    AddContactsParams: TypeAlias = ListContactsInput
    DeleteContactsParams: TypeAlias = ListContactsInput

    @classmethod
    def list(cls, params: Optional[ListParams] = None, options: Optional[CallOptions] = None) -> Page[List]:
        """Lists the workspace's lists."""
        return cls._page("/v1/lists", options, query=params)

    @classmethod
    def get(cls, list_id: str, options: Optional[CallOptions] = None) -> List:
        """Returns one list. Read its members with ``Contacts.list({"listId": ...})``."""
        return cast("List", cls._data("GET", path("/v1/lists/{}", list_id), options))

    @classmethod
    def create(cls, params: CreateParams, options: Optional[IdempotentCallOptions] = None) -> List:
        """Creates a list. Names are unique in the workspace, ignoring case: a repeated
        one raises a ``KiroraError`` with code ``ALREADY_EXISTS``."""
        return cast("List", cls._data("POST", "/v1/lists", options, body=params))

    @classmethod
    def update(cls, list_id: str, params: UpdateParams, options: Optional[CallOptions] = None) -> List:
        """Renames a list or changes its description. Change its members with
        ``add_contacts()`` and ``delete_contacts()``."""
        return cast("List", cls._data("PATCH", path("/v1/lists/{}", list_id), options, body=params))

    @classmethod
    def delete(cls, list_id: str, options: Optional[CallOptions] = None) -> None:
        """Deletes a list, keeping its contacts. While a campaign, form, journey or
        segment uses it, it raises a ``KiroraError`` with code ``IN_USE``, naming them in
        ``details``."""
        cls._remove(path("/v1/lists/{}", list_id), options)

    @classmethod
    def add_contacts(
        cls, list_id: str, params: AddContactsParams, options: Optional[IdempotentCallOptions] = None
    ) -> AddedListContacts:
        """Adds up to 500 contacts to a list, skipping those already in it. Identifiers
        that name no contact come back in ``notFound``. Each contact added starts any
        journey triggered by joining the list."""
        return cast(
            "AddedListContacts",
            cls._data("POST", path("/v1/lists/{}/contacts", list_id), options, body=params),
        )

    @classmethod
    def delete_contacts(
        cls, list_id: str, params: DeleteContactsParams, options: Optional[IdempotentCallOptions] = None
    ) -> DeletedListContacts:
        """Takes up to 500 contacts out of a list, keeping the contacts. Identifiers that
        name no contact come back in ``notFound``."""
        return cast(
            "DeletedListContacts",
            cls._data("POST", path("/v1/lists/{}/contacts/delete", list_id), options, body=params),
        )

    @classmethod
    def list_async(
        cls, params: Optional[ListParams] = None, options: Optional[CallOptions] = None
    ) -> AsyncPager[List]:
        """Lists the workspace's lists.

        The async form of ``Lists.list()``."""
        return cls._page_async("/v1/lists", options, query=params)

    @classmethod
    async def get_async(cls, list_id: str, options: Optional[CallOptions] = None) -> List:
        """Returns one list. Read its members with ``Contacts.list({"listId": ...})``.

        The async form of ``Lists.get()``."""
        return cast("List", await cls._data_async("GET", path("/v1/lists/{}", list_id), options))

    @classmethod
    async def create_async(
        cls, params: CreateParams, options: Optional[IdempotentCallOptions] = None
    ) -> List:
        """Creates a list. Names are unique in the workspace, ignoring case: a repeated
        one raises a ``KiroraError`` with code ``ALREADY_EXISTS``.

        The async form of ``Lists.create()``."""
        return cast("List", await cls._data_async("POST", "/v1/lists", options, body=params))

    @classmethod
    async def update_async(
        cls, list_id: str, params: UpdateParams, options: Optional[CallOptions] = None
    ) -> List:
        """Renames a list or changes its description. Change its members with
        ``add_contacts()`` and ``delete_contacts()``.

        The async form of ``Lists.update()``."""
        return cast(
            "List", await cls._data_async("PATCH", path("/v1/lists/{}", list_id), options, body=params)
        )

    @classmethod
    async def delete_async(cls, list_id: str, options: Optional[CallOptions] = None) -> None:
        """Deletes a list, keeping its contacts. While a campaign, form, journey or
        segment uses it, it raises a ``KiroraError`` with code ``IN_USE``, naming them in
        ``details``.

        The async form of ``Lists.delete()``."""
        await cls._remove_async(path("/v1/lists/{}", list_id), options)

    @classmethod
    async def add_contacts_async(
        cls, list_id: str, params: AddContactsParams, options: Optional[IdempotentCallOptions] = None
    ) -> AddedListContacts:
        """Adds up to 500 contacts to a list, skipping those already in it. Identifiers
        that name no contact come back in ``notFound``. Each contact added starts any
        journey triggered by joining the list.

        The async form of ``Lists.add_contacts()``."""
        return cast(
            "AddedListContacts",
            await cls._data_async("POST", path("/v1/lists/{}/contacts", list_id), options, body=params),
        )

    @classmethod
    async def delete_contacts_async(
        cls, list_id: str, params: DeleteContactsParams, options: Optional[IdempotentCallOptions] = None
    ) -> DeletedListContacts:
        """Takes up to 500 contacts out of a list, keeping the contacts. Identifiers that
        name no contact come back in ``notFound``.

        The async form of ``Lists.delete_contacts()``."""
        return cast(
            "DeletedListContacts",
            await cls._data_async(
                "POST", path("/v1/lists/{}/contacts/delete", list_id), options, body=params
            ),
        )

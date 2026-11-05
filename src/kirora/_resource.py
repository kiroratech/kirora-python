from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, Mapping, Optional, Type, TypeVar, cast
from urllib.parse import quote

from ._base_client import check_options
from ._pagination import AsyncPager, Page
from .async_request import AsyncRequest, list_pages_async
from .request import Request, list_pages

if TYPE_CHECKING:
    from ._client import Kirora

R = TypeVar("R", bound="APIResource")


class APIResource:
    """A resource, whose methods are class methods, as ``kirora.Contacts.identify()``.
    They act with the client the module settings describe, such as ``kirora.api_key``.
    ``Kirora(...).contacts`` is the same class, bound to that client instead."""

    _client: ClassVar[Optional[Kirora]] = None

    @classmethod
    def _bind(cls: Type[R], client: Kirora) -> Type[R]:
        bound = type(cls.__name__, (cls,), {"_client": client, "__doc__": cls.__doc__})
        bound.__module__ = cls.__module__
        bound.__qualname__ = cls.__qualname__
        return cast(Type[R], bound)

    @classmethod
    def _kirora(cls) -> Kirora:
        if cls._client is not None:
            return cls._client
        from ._client import default_client

        return default_client()

    @classmethod
    def _data(
        cls,
        method: str,
        path: str,
        options: Optional[Mapping[str, Any]],
        *,
        query: Optional[Mapping[str, Any]] = None,
        body: Any = None,
    ) -> Any:
        return Request(cls._kirora(), method, path, call_options(options, query, body), "data").perform()

    @classmethod
    async def _data_async(
        cls,
        method: str,
        path: str,
        options: Optional[Mapping[str, Any]],
        *,
        query: Optional[Mapping[str, Any]] = None,
        body: Any = None,
    ) -> Any:
        return await AsyncRequest(
            cls._kirora(), method, path, call_options(options, query, body), "data"
        ).perform()

    @classmethod
    def _remove(
        cls, path: str, options: Optional[Mapping[str, Any]], *, query: Optional[Mapping[str, Any]] = None
    ) -> None:
        Request(cls._kirora(), "DELETE", path, call_options(options, query), "any").perform()

    @classmethod
    async def _remove_async(
        cls, path: str, options: Optional[Mapping[str, Any]], *, query: Optional[Mapping[str, Any]] = None
    ) -> None:
        await AsyncRequest(cls._kirora(), "DELETE", path, call_options(options, query), "any").perform()

    @classmethod
    def _page(
        cls, path: str, options: Optional[Mapping[str, Any]], *, query: Optional[Mapping[str, Any]] = None
    ) -> Page[Any]:
        return list_pages(cls._kirora(), path, call_options(options, query))

    @classmethod
    def _page_async(
        cls, path: str, options: Optional[Mapping[str, Any]], *, query: Optional[Mapping[str, Any]] = None
    ) -> AsyncPager[Any]:
        return list_pages_async(cls._kirora(), path, call_options(options, query))


def call_options(
    options: Optional[Mapping[str, Any]], query: Optional[Mapping[str, Any]], body: Any = None
) -> Mapping[str, Any]:
    """The options of one call, checked, with its query and body."""
    given = dict(options or {})
    check_options(given)
    return {**given, "query": query, "body": body}


def path(template: str, *ids: str) -> str:
    """Fills ``template``'s ``{}`` with ``ids``, each percent-encoded as one segment."""
    for value in ids:
        if not isinstance(value, str):
            raise TypeError(f"ids must be strings, not {type(value).__name__}")
    return template.format(*(quote(value, safe="") for value in ids))


def with_id_type(id_type: Optional[str], params: Optional[Mapping[str, Any]] = None) -> Mapping[str, Any]:
    """A query of the ``idType`` a contact id is given as, and any ``params``."""
    return {**(params or {}), "idType": id_type}

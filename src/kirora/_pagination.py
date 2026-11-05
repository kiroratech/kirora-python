from __future__ import annotations

from typing import (
    Any,
    AsyncContextManager,
    AsyncIterator,
    Awaitable,
    Callable,
    Dict,
    Generator,
    Generic,
    Iterator,
    List,
    Optional,
    Set,
    TypeVar,
)

import anyio

from ._response import ResponseInfo
from .exceptions import KiroraResponseError

__all__ = ["Page", "AsyncPage", "AsyncPager"]

T = TypeVar("T")


class _PageBase(Generic[T]):
    def __init__(self, payload: Dict[str, Any], last_response: ResponseInfo) -> None:
        self.data: List[T] = payload["data"]
        """The items on this page."""
        self.meta: Dict[str, Any] = payload["meta"]
        """The page's ``meta``. Some lists add to it, as ``contacts.list()`` adds
        ``count`` on its first page."""
        self.last_response = last_response
        """The HTTP response this page came from."""

    @property
    def next_cursor(self) -> Optional[str]:
        """The cursor of the next page, or None on the last page. Pass it back as
        ``cursor``, with the same filters, for the next."""
        cursor: Optional[str] = self.meta["pagination"]["nextCursor"]
        return cursor

    def has_next_page(self) -> bool:
        return self.next_cursor is not None

    def _check_cursor(self, followed: Set[str]) -> str:
        cursor = self.next_cursor
        assert cursor is not None
        if cursor in followed:
            raise KiroraResponseError(
                f"Cursor {cursor} came round again, so the list would never end",
                status=self.last_response.status,
                request_id=self.last_response.request_id,
            )
        followed.add(cursor)
        return cursor

    def __repr__(self) -> str:
        return f"{type(self).__name__}(data=<{len(self.data)} items>, next_cursor={self.next_cursor!r})"


class Page(_PageBase[T]):
    """One page of a list, from a ``list()`` method.

    Iterate the page itself for every item, fetching later pages as you go; use
    ``page.data`` for this page's items only::

        for contact in kirora.Contacts.list({"query": "ada"}):
            print(contact["id"])

    Each iteration starts again from this page.
    """

    def __init__(
        self,
        payload: Dict[str, Any],
        last_response: ResponseInfo,
        fetch: Callable[[str], Page[T]],
    ) -> None:
        super().__init__(payload, last_response)
        self._fetch = fetch

    def next_page(self) -> Optional[Page[T]]:
        """Fetches the next page, or returns None on the last page."""
        cursor = self.next_cursor
        return None if cursor is None else self._fetch(cursor)

    def iter_pages(self) -> Iterator[Page[T]]:
        """Yields this page, then each later page. Raises ``KiroraResponseError`` if the
        API returns a cursor it already returned, since the list would never end."""
        page: Page[T] = self
        followed: Set[str] = set()
        while True:
            yield page
            if page.next_cursor is None:
                return
            page = self._fetch(page._check_cursor(followed))

    def __iter__(self) -> Iterator[T]:
        for page in self.iter_pages():
            yield from page.data


# What an async list fetches a page with: its cursor (None for the first) and the
# connection to send it on, and how to open one for a walk over the pages.
AsyncFetch = Callable[[Optional[str], Any], Awaitable["AsyncPage[T]"]]
Connect = Callable[[], AsyncContextManager[Any]]


class AsyncPage(_PageBase[T]):
    """One page of a list, from an async ``list()`` method. ``async for`` over the page
    yields every item, fetching later pages as you go; ``page.data`` is this page's.
    A walk over the pages shares one connection."""

    def __init__(
        self, payload: Dict[str, Any], last_response: ResponseInfo, fetch: AsyncFetch[T], connect: Connect
    ) -> None:
        super().__init__(payload, last_response)
        self._fetch = fetch
        self._connect = connect

    async def next_page(self) -> Optional[AsyncPage[T]]:
        """Fetches the next page, or returns None on the last page."""
        cursor = self.next_cursor
        if cursor is None:
            return None
        async with self._connect() as http:
            return await self._fetch(cursor, http)

    async def iter_pages(self) -> AsyncIterator[AsyncPage[T]]:
        """Yields this page, then each later page. Raises ``KiroraResponseError`` if the
        API returns a cursor it already returned, since the list would never end."""
        async with self._connect() as http:
            async for page in self._walk(http):
                yield page

    async def __aiter__(self) -> AsyncIterator[T]:
        async for page in self.iter_pages():
            for item in page.data:
                yield item

    async def _walk(self, http: Any) -> AsyncIterator[AsyncPage[T]]:
        page: AsyncPage[T] = self
        followed: Set[str] = set()
        while True:
            yield page
            if page.next_cursor is None:
                return
            page = await self._fetch(page._check_cursor(followed), http)


class AsyncPager(Generic[T]):
    """What an async ``list()`` method returns. Await it for the first page, or iterate
    it with ``async for`` for every item, fetching later pages as you go::

        page = await kirora.Contacts.list_async({"query": "ada"})
        async for contact in kirora.Contacts.list_async({"query": "ada"}):
            print(contact["id"])

    Nothing is fetched until you do either. Awaiting and then iterating reuses the first
    page; each iteration fetches the later pages again, on one connection.
    """

    def __init__(self, fetch: AsyncFetch[T], connect: Connect) -> None:
        self._fetch = fetch
        self._connect = connect
        self._first: Optional[AsyncPage[T]] = None
        # Tasks awaiting at once share one request.
        self._lock = anyio.Lock()

    async def _first_page(self, http: Any) -> AsyncPage[T]:
        if self._first is None:
            async with self._lock:
                if self._first is None:
                    self._first = await self._fetch(None, http)
        return self._first

    async def _await_first(self) -> AsyncPage[T]:
        if self._first is not None:
            return self._first
        async with self._connect() as http:
            return await self._first_page(http)

    def __await__(self) -> Generator[Any, None, AsyncPage[T]]:
        return self._await_first().__await__()

    async def __aiter__(self) -> AsyncIterator[T]:
        async with self._connect() as http:
            first = await self._first_page(http)
            async for page in first._walk(http):
                for item in page.data:
                    yield item

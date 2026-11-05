"""Sends a call to the API and its retries, for the ``_async`` methods."""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any, AsyncIterator, Mapping, Optional

import anyio
import httpx

from ._base_client import Shape
from ._pagination import AsyncPage, AsyncPager
from .exceptions import KiroraException

if TYPE_CHECKING:
    from ._client import Kirora

__all__ = ["AsyncRequest"]

# How a call waits between attempts; anyio's works under asyncio and trio.
_async_sleep = anyio.sleep


class AsyncRequest:
    """One call, as ``Request`` makes it, awaited. Without an ``async_http_client`` on
    the client, each call opens its own ``httpx.AsyncClient``, which works in any event
    loop; pass one to share connections between calls."""

    def __init__(
        self, client: Kirora, method: str, path: str, options: Mapping[str, Any], shape: Shape
    ) -> None:
        self._attempts = client._attempts(method, path, options, shape)
        self._connections = client._connections

    async def perform(self, http: Optional[httpx.AsyncClient] = None) -> Any:
        """Performs the call with ``http``, or else the client's connections."""
        if http is not None:
            return await self._perform(http)
        async with self._connections.use_async() as opened:
            return await self._perform(opened)

    @asynccontextmanager
    async def open(self) -> AsyncIterator[httpx.Response]:
        """Performs a ``"raw"`` call and yields its unread response, closing it, and any
        client opened for it, when the block ends."""
        async with self._connections.use_async() as http:
            response: httpx.Response = await self._perform(http)
            try:
                yield response
            finally:
                await response.aclose()

    async def _perform(self, http: httpx.AsyncClient) -> Any:
        attempts = self._attempts
        while True:
            try:
                return await self._send(http)
            except KiroraException as error:
                wait = attempts.after(error)
            if wait is None:
                return None
            await _async_sleep(wait)

    async def _send(self, http: httpx.AsyncClient) -> Any:
        attempts = self._attempts
        # The deadline cancels the attempt when it passes, whatever it's waiting for.
        deadline = time.monotonic() + attempts.timeout
        try:
            with anyio.fail_after(attempts.timeout):
                response = await http.send(attempts.request_for(http), stream=True, follow_redirects=False)
        except (httpx.RequestError, TimeoutError) as error:
            raise attempts.failed(error) from error
        try:
            # The caller reads the body, which the deadline doesn't cover.
            if attempts.hand_over(response):
                return response
            body = bytearray()
            try:
                with anyio.fail_after(max(deadline - time.monotonic(), 0)):
                    async for chunk in response.aiter_bytes():
                        attempts.add(body, chunk, response)
            except (httpx.RequestError, TimeoutError) as error:
                raise attempts.read_failed(response, error) from error
        except BaseException:
            await response.aclose()
            raise
        await response.aclose()
        return attempts.finish(response, body)


def list_pages_async(client: Kirora, path: str, options: Mapping[str, Any]) -> AsyncPager[Any]:
    """A list that fetches nothing until it's awaited or iterated. Its options are
    checked now, so a mistake shows at the call, as with a sync list. A walk over its
    pages shares one connection."""
    page_options = client._page_options(options)
    client._attempts("GET", path, page_options(None), "page")
    connections = client._connections

    async def fetch(cursor: Optional[str], http: httpx.AsyncClient) -> AsyncPage[Any]:
        request = AsyncRequest(client, "GET", path, page_options(cursor), "page")
        payload, info = await request.perform(http)
        return AsyncPage(payload, info, fetch, connections.use_async)

    return AsyncPager(fetch, connections.use_async)

from __future__ import annotations

import functools
import ssl
import threading
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

import httpx

__all__ = ["Connections"]


class Connections:
    """The httpx clients one or more ``Kirora`` clients send with: the ones you passed, or
    ones opened for you. A client from ``for_workspace()`` shares its parent's, and the
    module settings' clients share one."""

    def __init__(
        self,
        http_client: Optional[httpx.Client] = None,
        async_http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self._given_sync = http_client
        self._opened_sync: Optional[httpx.Client] = None
        self._lock = threading.Lock()
        self.async_client = async_http_client

    def sync(self) -> httpx.Client:
        """The sync client: the one given, or one opened on first use, and again after
        ``close()``."""
        if self._given_sync is not None:
            return self._given_sync
        with self._lock:
            if self._opened_sync is None:
                self._opened_sync = httpx.Client()
            return self._opened_sync

    @asynccontextmanager
    async def use_async(self) -> AsyncIterator[httpx.AsyncClient]:
        """The async client given, or one opened for the block, which works in any event
        loop. Opened ones share a TLS context, which is slow to build."""
        if self.async_client is not None:
            yield self.async_client
            return
        async with httpx.AsyncClient(verify=_ssl_context()) as opened:
            yield opened

    def close(self) -> None:
        """Closes the sync client opened for you. Clients you passed are yours to close."""
        with self._lock:
            opened, self._opened_sync = self._opened_sync, None
        if opened is not None:
            opened.close()


@functools.cache
def _ssl_context() -> ssl.SSLContext:
    return httpx.create_ssl_context()

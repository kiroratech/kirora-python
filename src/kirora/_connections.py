from __future__ import annotations

import functools
import ssl
import sys
import threading
import weakref
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Optional

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
        self._opened_async: weakref.WeakKeyDictionary[Any, httpx.AsyncClient] = weakref.WeakKeyDictionary()

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
        """The async client given, or else the one for the running event loop."""
        if self.async_client is not None:
            yield self.async_client
            return
        reused = self._for_running_loop()
        if reused is not None:
            yield reused
            return
        async with httpx.AsyncClient(verify=_ssl_context()) as opened:
            yield opened

    def close(self) -> None:
        """Closes the sync client opened for you. Clients you passed are yours to close."""
        with self._lock:
            opened, self._opened_sync = self._opened_sync, None
        if opened is not None:
            opened.close()

    async def aclose(self) -> None:
        """Closes the async client opened for the running event loop."""
        loop = _running_loop()
        if loop is None:
            return
        with self._lock:
            opened = self._opened_async.pop(loop, None)
        if opened is not None:
            await opened.aclose()

    def _for_running_loop(self) -> Optional[httpx.AsyncClient]:
        loop = _running_loop()
        if loop is None:
            return None
        with self._lock:
            self._forget_closed_loops()
            try:
                opened = self._opened_async.get(loop)
            except TypeError:
                return None
            if opened is None or opened.is_closed:
                opened = httpx.AsyncClient(verify=_ssl_context())
                self._opened_async[loop] = opened
            return opened

    def _forget_closed_loops(self) -> None:
        """Drops the clients of closed asyncio loops, which would otherwise never be freed."""
        for loop in list(self._opened_async):
            is_closed = getattr(loop, "is_closed", None)
            if is_closed is not None and is_closed():
                del self._opened_async[loop]


def _running_loop() -> Any:
    """The running asyncio loop, or the running Trio run's root task, or None."""
    asyncio = sys.modules.get("asyncio")
    if asyncio is not None:
        try:
            return asyncio.get_running_loop()
        except RuntimeError:
            pass
    trio = sys.modules.get("trio")
    if trio is None:
        return None
    try:
        return trio.lowlevel.current_root_task()
    except RuntimeError:
        return None


@functools.cache
def _ssl_context() -> ssl.SSLContext:
    return httpx.create_ssl_context()

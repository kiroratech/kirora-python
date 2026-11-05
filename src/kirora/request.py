"""Sends a call to the API and its retries, for the sync methods."""

from __future__ import annotations

import time
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Iterator, Mapping, Optional

import httpx

from ._base_client import Shape
from ._pagination import Page
from .exceptions import KiroraException

if TYPE_CHECKING:
    from ._client import Kirora

__all__ = ["Request"]

# How a call waits between attempts.
_sleep = time.sleep


class DeadlineExceeded(httpx.TimeoutException):
    """An attempt that took longer than its timeout, found as its response arrived."""


def check_deadline(deadline: float) -> None:
    if time.monotonic() > deadline:
        raise DeadlineExceeded("the attempt took longer than the timeout")


class Request:
    """One call: a request to ``path``, sent again as its endpoint allows when an attempt
    fails. ``shape`` says what the call returns: the whole body (``"any"``), its
    ``data`` (``"data"``), a page (``"page"``), or the unread response (``"raw"``)."""

    def __init__(
        self, client: Kirora, method: str, path: str, options: Mapping[str, Any], shape: Shape
    ) -> None:
        self._attempts = client._attempts(method, path, options, shape)
        self._http = client._connections.sync()

    def perform(self) -> Any:
        attempts = self._attempts
        while True:
            try:
                return self._send()
            except KiroraException as error:
                wait = attempts.after(error)
            if wait is None:
                return None
            _sleep(wait)

    @contextmanager
    def open(self) -> Iterator[httpx.Response]:
        """Performs a ``"raw"`` call and yields its unread response, closing it when the
        block ends."""
        response: httpx.Response = self.perform()
        try:
            yield response
        finally:
            response.close()

    def _send(self) -> Any:
        attempts = self._attempts
        # httpx limits each network wait to the timeout; the deadline limits the attempt.
        # A blocking wait can't be interrupted, so the deadline is checked as each part
        # arrives: an attempt past it fails rather than return.
        deadline = time.monotonic() + attempts.timeout
        try:
            response = self._http.send(attempts.request_for(self._http), stream=True, follow_redirects=False)
        except httpx.RequestError as error:
            raise attempts.failed(error) from error
        try:
            body = bytearray()
            try:
                check_deadline(deadline)
                # The caller reads the body, which the deadline doesn't cover.
                if attempts.hand_over(response):
                    return response
                for chunk in response.iter_bytes():
                    attempts.add(body, chunk, response)
                    check_deadline(deadline)
            except httpx.RequestError as error:
                raise attempts.read_failed(response, error) from error
        except BaseException:
            response.close()
            raise
        response.close()
        return attempts.finish(response, body)


def list_pages(client: Kirora, path: str, options: Mapping[str, Any]) -> Page[Any]:
    """Fetches the first page of a list, which fetches the later ones as it's iterated."""
    page_options = client._page_options(options)

    def fetch(cursor: Optional[str]) -> Page[Any]:
        payload, info = Request(client, "GET", path, page_options(cursor), "page").perform()
        return Page(payload, info, fetch)

    return fetch(None)

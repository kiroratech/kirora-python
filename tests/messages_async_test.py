"""``kirora.Messages`` async methods: each method reaches its endpoint and returns its result."""

from __future__ import annotations

import pytest

import kirora

from .conftest import Server, ok, page
from .resources_test import operation_of

pytestmark = pytest.mark.asyncio


class TestMessagesAsync:
    async def test_list(self) -> None:
        server = Server(page([]))
        server.install()
        await kirora.Messages.list_async({"opened": True})
        assert operation_of(server.last) == "listMessages"

    async def test_get(self) -> None:
        server = Server(ok({}))
        server.install()
        await kirora.Messages.get_async("m")
        assert operation_of(server.last) == "getMessage"

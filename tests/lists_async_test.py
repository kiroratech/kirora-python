"""``kirora.Lists`` async methods: each method reaches its endpoint and returns its result."""

from __future__ import annotations

import httpx
import pytest

import kirora

from .conftest import Server, ok, page
from .resources_test import operation_of

pytestmark = pytest.mark.asyncio


class TestListsAsync:
    async def test_list(self) -> None:
        server = Server(page([]))
        server.install()
        await kirora.Lists.list_async()
        assert operation_of(server.last) == "listLists"

    async def test_get(self) -> None:
        server = Server(ok({}))
        server.install()
        await kirora.Lists.get_async("l")
        assert operation_of(server.last) == "getList"

    async def test_create(self) -> None:
        server = Server(ok({}, 201))
        server.install()
        await kirora.Lists.create_async({"name": "n"})
        assert operation_of(server.last) == "createList"

    async def test_update(self) -> None:
        server = Server(ok({}))
        server.install()
        await kirora.Lists.update_async("l", {})
        assert operation_of(server.last) == "updateList"

    async def test_delete(self) -> None:
        server = Server(httpx.Response(204))
        server.install()
        await kirora.Lists.delete_async("l")
        assert operation_of(server.last) == "deleteList"

    async def test_add_contacts(self) -> None:
        server = Server(ok({}))
        server.install()
        await kirora.Lists.add_contacts_async("l", {})  # type: ignore[arg-type]
        assert operation_of(server.last) == "addListContacts"

    async def test_delete_contacts(self) -> None:
        server = Server(ok({}))
        server.install()
        await kirora.Lists.delete_contacts_async("l", {})  # type: ignore[arg-type]
        assert operation_of(server.last) == "deleteListContacts"

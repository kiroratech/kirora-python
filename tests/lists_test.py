"""``kirora.Lists``: each method reaches its endpoint and returns its result."""

from __future__ import annotations

import httpx

import kirora

from .conftest import Server, ok, page
from .resources_test import operation_of


class TestLists:
    def test_list(self) -> None:
        server = Server(page([]))
        server.install()
        kirora.Lists.list()
        assert operation_of(server.last) == "listLists"

    def test_get(self) -> None:
        server = Server(ok({}))
        server.install()
        kirora.Lists.get("l")
        assert operation_of(server.last) == "getList"

    def test_create(self) -> None:
        server = Server(ok({}, 201))
        server.install()
        kirora.Lists.create({"name": "n"})
        assert operation_of(server.last) == "createList"

    def test_update(self) -> None:
        server = Server(ok({}))
        server.install()
        kirora.Lists.update("l", {})
        assert operation_of(server.last) == "updateList"

    def test_delete(self) -> None:
        server = Server(httpx.Response(204))
        server.install()
        kirora.Lists.delete("l")
        assert operation_of(server.last) == "deleteList"

    def test_add_contacts(self) -> None:
        server = Server(ok({}))
        server.install()
        kirora.Lists.add_contacts("l", {})  # type: ignore[arg-type]
        assert operation_of(server.last) == "addListContacts"

    def test_delete_contacts(self) -> None:
        server = Server(ok({}))
        server.install()
        kirora.Lists.delete_contacts("l", {})  # type: ignore[arg-type]
        assert operation_of(server.last) == "deleteListContacts"

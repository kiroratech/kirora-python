"""``kirora.Suppressions`` async methods: each method reaches its endpoint and returns its result."""

from __future__ import annotations

import pytest

import kirora

from .conftest import Server, ok, page
from .resources_test import operation_of

pytestmark = pytest.mark.asyncio


class TestSuppressionsAsync:
    async def test_list(self) -> None:
        server = Server(page([]))
        server.install()
        await kirora.Suppressions.list_async()
        assert operation_of(server.last) == "listSuppressions"

    async def test_add(self) -> None:
        server = Server(ok({}))
        server.install()
        await kirora.Suppressions.add_async({"emails": []})
        assert operation_of(server.last) == "addSuppressions"

    async def test_delete(self) -> None:
        server = Server(ok({}))
        server.install()
        await kirora.Suppressions.delete_async({"emails": []})
        assert operation_of(server.last) == "deleteSuppressions"

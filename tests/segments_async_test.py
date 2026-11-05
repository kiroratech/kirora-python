"""``kirora.Segments`` async methods: each method reaches its endpoint and returns its result."""

from __future__ import annotations

import httpx
import pytest

import kirora

from .conftest import Server, ok, page
from .resources_test import operation_of

pytestmark = pytest.mark.asyncio


class TestSegmentsAsync:
    async def test_list(self) -> None:
        server = Server(page([{"id": "s"}], "c2"), page([{"id": "t"}]))
        server.install()
        assert [s["id"] async for s in kirora.Segments.list_async()] == ["s", "t"]
        assert operation_of(server.last) == "listSegments"

    async def test_create(self) -> None:
        server = Server(ok({"id": "s"}, 201))
        server.install()
        await kirora.Segments.create_async({"name": "n", "rules": {"all": []}})
        assert operation_of(server.last) == "createSegment"

    async def test_preview(self) -> None:
        server = Server(ok({"count": 1}))
        server.install()
        assert (await kirora.Segments.preview_async({"rules": {"all": []}}))["count"] == 1
        assert operation_of(server.last) == "previewSegment"

    async def test_list_membership_changes(self) -> None:
        server = Server(page([]))
        server.install()
        first = await kirora.Segments.list_membership_changes_async(
            "s", {"change": "joined", "day": "2026-11-01"}
        )
        assert first.data == []
        assert operation_of(server.last) == "listSegmentMembershipChanges"

    async def test_delete(self) -> None:
        server = Server(httpx.Response(204))
        server.install()
        assert await kirora.Segments.delete_async("s") is None
        assert operation_of(server.last) == "deleteSegment"

    async def test_a_contacts_segments(self) -> None:
        server = Server(page([{"id": "s"}]))
        server.install()
        first = await kirora.Contacts.list_segments_async("c")
        assert first.data == [{"id": "s"}]
        assert operation_of(server.last) == "listContactSegments"

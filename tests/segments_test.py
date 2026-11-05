"""``kirora.Segments``: each method reaches its endpoint and returns its result."""

from __future__ import annotations

import datetime as dt

import httpx

import kirora

from .conftest import Server, ok, page
from .resources_test import operation_of


class TestSegments:
    def test_list(self) -> None:
        server = Server(page([{"id": "s"}]))
        server.install()
        assert [s["id"] for s in kirora.Segments.list({"query": "vip"})] == ["s"]
        assert operation_of(server.last) == "listSegments"
        assert server.last.url.params["query"] == "vip"

    def test_get(self) -> None:
        server = Server(ok({"id": "s", "memberCount": 3}))
        server.install()
        assert kirora.Segments.get("s")["memberCount"] == 3
        assert operation_of(server.last) == "getSegment"

    def test_create_sends_the_rules_with_a_key(self) -> None:
        server = Server(ok({"id": "s"}, 201))
        server.install()
        rules: kirora.SegmentRulesInput = {
            "all": [{"type": "attribute", "field": "plan", "operator": "equals", "value": "pro"}]
        }
        kirora.Segments.create({"name": "Pro plan", "rules": rules})
        assert operation_of(server.last) == "createSegment"
        assert server.body() == {"name": "Pro plan", "rules": rules}

    def test_update(self) -> None:
        server = Server(ok({"id": "s"}))
        server.install()
        kirora.Segments.update("s", {"name": "Renamed"})
        assert operation_of(server.last) == "updateSegment"

    def test_delete(self) -> None:
        server = Server(httpx.Response(204))
        server.install()
        assert kirora.Segments.delete("s") is None
        assert operation_of(server.last) == "deleteSegment"

    def test_preview(self) -> None:
        server = Server(ok({"count": 12, "countExact": True, "reach": {"email": 10, "push": 4}}))
        server.install()
        preview = kirora.Segments.preview({"rules": {"all": []}})
        assert preview["reach"]["email"] == 10
        assert operation_of(server.last) == "previewSegment"

    def test_list_contacts(self) -> None:
        server = Server(page([{"id": "c"}]))
        server.install()
        assert [c["id"] for c in kirora.Segments.list_contacts("s")] == ["c"]
        assert operation_of(server.last) == "listSegmentContacts"

    def test_list_membership_changes_sends_the_change_and_the_day(self) -> None:
        server = Server(page([{"id": "c"}], None, count=1))
        server.install()
        first = kirora.Segments.list_membership_changes("s", {"change": "left", "day": dt.date(2026, 11, 1)})
        assert first.meta["count"] == 1
        assert operation_of(server.last) == "listSegmentMembershipChanges"
        assert server.last.url.params["change"] == "left"
        assert server.last.url.params["day"] == "2026-11-01"

    def test_size_history_sends_its_window(self) -> None:
        server = Server(ok({"segmentId": "s", "points": []}))
        server.install()
        kirora.Segments.size_history(
            "s", {"from": dt.date(2026, 10, 1), "to": dt.datetime(2026, 11, 1, tzinfo=dt.timezone.utc)}
        )
        assert operation_of(server.last) == "getSegmentSizeHistory"
        assert server.last.url.params["from"] == "2026-10-01"
        assert server.last.url.params["to"] == "2026-11-01T00:00:00Z"

    def test_usage(self) -> None:
        server = Server(ok({"campaigns": [], "segments": [], "hasMore": False}))
        server.install()
        assert kirora.Segments.usage("s")["hasMore"] is False
        assert operation_of(server.last) == "getSegmentUsage"

    def test_a_contacts_segments(self) -> None:
        server = Server(page([{"id": "s", "name": "VIP"}]))
        server.install()
        segments = list(kirora.Contacts.list_segments("ada@example.com", id_type="email"))
        assert segments == [{"id": "s", "name": "VIP"}]
        assert operation_of(server.last) == "listContactSegments"
        assert server.last.url.raw_path == b"/v1/contacts/ada%40example.com/segments?idType=email"

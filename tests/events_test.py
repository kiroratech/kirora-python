"""``kirora.Events``: each method reaches its endpoint and returns its result."""

from __future__ import annotations

import kirora

from .conftest import Server, ok
from .resources_test import operation_of


class TestEvents:
    def test_track(self) -> None:
        server = Server(ok({}, 201))
        server.install()
        kirora.Events.track({"email": "a@b.co", "name": "x"})
        assert operation_of(server.last) == "trackEvent"

    def test_track_batch(self) -> None:
        server = Server(ok({}))
        server.install()
        kirora.Events.track_batch({"events": []})
        assert operation_of(server.last) == "trackEventsBatch"

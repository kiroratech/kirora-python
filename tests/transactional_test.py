"""``kirora.Transactional``: each method reaches its endpoint and returns its result."""

from __future__ import annotations

import kirora

from .conftest import Server, ok
from .resources_test import operation_of


class TestTransactional:
    def test_send(self) -> None:
        server = Server(ok({}, 202))
        server.install()
        kirora.Transactional.send({})  # type: ignore[typeddict-item]
        assert operation_of(server.last) == "sendTransactionalMessage"

    def test_send_batch(self) -> None:
        server = Server(ok({}, 202))
        server.install()
        kirora.Transactional.send_batch({"messages": []})
        assert operation_of(server.last) == "sendTransactionalMessagesBatch"

    def test_cancel(self) -> None:
        server = Server(ok({}))
        server.install()
        kirora.Transactional.cancel("m")  # type: ignore[typeddict-item]  # type: ignore[typeddict-item]  # type: ignore[typeddict-item]
        assert operation_of(server.last) == "cancelScheduledTransactionalMessage"

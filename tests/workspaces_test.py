"""``kirora.Workspaces``: each method reaches its endpoint and returns its result."""

from __future__ import annotations

import kirora

from .conftest import Server, ok, page
from .resources_test import operation_of


class TestWorkspaces:
    def test_list(self) -> None:
        server = Server(page([]))
        server.install()
        kirora.Workspaces.list()
        assert operation_of(server.last) == "listWorkspaces"

    def test_create(self) -> None:
        server = Server(ok({}, 201))
        server.install()
        kirora.Workspaces.create({})  # type: ignore[typeddict-item]
        assert operation_of(server.last) == "createWorkspace"

    def test_get(self) -> None:
        server = Server(ok({}))
        server.install()
        kirora.Workspaces.get("w")
        assert operation_of(server.last) == "getWorkspace"

    def test_update(self) -> None:
        server = Server(ok({}))
        server.install()
        kirora.Workspaces.update("w", {})
        assert operation_of(server.last) == "updateWorkspace"

    def test_delete(self) -> None:
        server = Server(ok({}))
        server.install()
        kirora.Workspaces.delete("w")
        assert operation_of(server.last) == "deleteWorkspace"

    def test_suspend(self) -> None:
        server = Server(ok({}))
        server.install()
        kirora.Workspaces.suspend("w")
        assert operation_of(server.last) == "suspendWorkspace"

    def test_resume(self) -> None:
        server = Server(ok({}))
        server.install()
        kirora.Workspaces.resume("w")
        assert operation_of(server.last) == "resumeWorkspace"

    def test_cancel_deletion(self) -> None:
        server = Server(ok({}))
        server.install()
        kirora.Workspaces.cancel_deletion("w")
        assert operation_of(server.last) == "cancelWorkspaceDeletion"

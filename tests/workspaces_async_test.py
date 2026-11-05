"""``kirora.Workspaces`` async methods: each method reaches its endpoint and returns its result."""

from __future__ import annotations

import pytest

import kirora

from .conftest import Server, ok, page
from .resources_test import operation_of

pytestmark = pytest.mark.asyncio


class TestWorkspacesAsync:
    async def test_list(self) -> None:
        server = Server(page([]))
        server.install()
        await kirora.Workspaces.list_async()
        assert operation_of(server.last) == "listWorkspaces"

    async def test_create(self) -> None:
        server = Server(ok({}, 201))
        server.install()
        await kirora.Workspaces.create_async({})  # type: ignore[typeddict-item]
        assert operation_of(server.last) == "createWorkspace"

    async def test_get(self) -> None:
        server = Server(ok({}))
        server.install()
        await kirora.Workspaces.get_async("w")
        assert operation_of(server.last) == "getWorkspace"

    async def test_update(self) -> None:
        server = Server(ok({}))
        server.install()
        await kirora.Workspaces.update_async("w", {})
        assert operation_of(server.last) == "updateWorkspace"

    async def test_delete(self) -> None:
        server = Server(ok({}))
        server.install()
        await kirora.Workspaces.delete_async("w")
        assert operation_of(server.last) == "deleteWorkspace"

    async def test_suspend(self) -> None:
        server = Server(ok({}))
        server.install()
        await kirora.Workspaces.suspend_async("w")
        assert operation_of(server.last) == "suspendWorkspace"

    async def test_resume(self) -> None:
        server = Server(ok({}))
        server.install()
        await kirora.Workspaces.resume_async("w")
        assert operation_of(server.last) == "resumeWorkspace"

    async def test_cancel_deletion(self) -> None:
        server = Server(ok({}))
        server.install()
        await kirora.Workspaces.cancel_deletion_async("w")
        assert operation_of(server.last) == "cancelWorkspaceDeletion"

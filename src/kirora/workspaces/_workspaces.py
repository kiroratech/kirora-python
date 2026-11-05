from __future__ import annotations

from typing import Optional, cast

from typing_extensions import TypeAlias

from .._base_client import CallOptions, IdempotentCallOptions
from .._pagination import AsyncPager, Page
from .._resource import APIResource, path
from ..types import (
    CreateWorkspaceInput,
    ListWorkspacesParams,
    UpdateWorkspaceInput,
    Workspace,
)

__all__ = ["Workspaces"]


class Workspaces(APIResource):
    """Partner keys only: your tenants' workspaces, named by your own external ids."""

    ListParams: TypeAlias = ListWorkspacesParams
    CreateParams: TypeAlias = CreateWorkspaceInput
    UpdateParams: TypeAlias = UpdateWorkspaceInput

    @classmethod
    def list(
        cls, params: Optional[ListParams] = None, options: Optional[CallOptions] = None
    ) -> Page[Workspace]:
        """Lists your tenants' workspaces, newest first."""
        return cls._page("/v1/workspaces", options, query=params)

    @classmethod
    def create(cls, params: CreateParams, options: Optional[IdempotentCallOptions] = None) -> Workspace:
        """Creates a workspace for one of your tenants; act in it with
        ``Kirora(...).for_workspace()``. A repeated ``externalId`` raises a ``KiroraError``
        with code ``ALREADY_EXISTS``."""
        return cast("Workspace", cls._data("POST", "/v1/workspaces", options, body=params))

    @classmethod
    def get(cls, external_id: str, options: Optional[CallOptions] = None) -> Workspace:
        """Returns a tenant's workspace."""
        return cast("Workspace", cls._data("GET", path("/v1/workspaces/{}", external_id), options))

    @classmethod
    def update(
        cls, external_id: str, params: UpdateParams, options: Optional[CallOptions] = None
    ) -> Workspace:
        """Changes a tenant workspace's name, country or timezone."""
        return cast(
            "Workspace", cls._data("PATCH", path("/v1/workspaces/{}", external_id), options, body=params)
        )

    @classmethod
    def delete(cls, external_id: str, options: Optional[CallOptions] = None) -> Workspace:
        """Deletes a tenant's workspace and everything in it after a grace period, and
        stops its sends at once. Returns the workspace, whose ``deletesAt`` says when;
        ``cancel_deletion()`` stops it before then."""
        return cast("Workspace", cls._data("DELETE", path("/v1/workspaces/{}", external_id), options))

    @classmethod
    def suspend(cls, external_id: str, options: Optional[IdempotentCallOptions] = None) -> Workspace:
        """Stops every send in a tenant's workspace until ``resume()``. Messages already
        queued are skipped, not held."""
        return cast("Workspace", cls._data("POST", path("/v1/workspaces/{}/suspend", external_id), options))

    @classmethod
    def resume(cls, external_id: str, options: Optional[IdempotentCallOptions] = None) -> Workspace:
        """Lifts a tenant workspace's suspension. Messages skipped meanwhile aren't
        sent."""
        return cast("Workspace", cls._data("POST", path("/v1/workspaces/{}/resume", external_id), options))

    @classmethod
    def cancel_deletion(cls, external_id: str, options: Optional[IdempotentCallOptions] = None) -> Workspace:
        """Cancels a tenant workspace's pending deletion. Messages skipped meanwhile
        aren't sent."""
        return cast(
            "Workspace", cls._data("POST", path("/v1/workspaces/{}/cancel-deletion", external_id), options)
        )

    @classmethod
    def list_async(
        cls, params: Optional[ListParams] = None, options: Optional[CallOptions] = None
    ) -> AsyncPager[Workspace]:
        """Lists your tenants' workspaces, newest first.

        The async form of ``Workspaces.list()``."""
        return cls._page_async("/v1/workspaces", options, query=params)

    @classmethod
    async def create_async(
        cls, params: CreateParams, options: Optional[IdempotentCallOptions] = None
    ) -> Workspace:
        """Creates a workspace for one of your tenants; act in it with
        ``Kirora(...).for_workspace()``. A repeated ``externalId`` raises a ``KiroraError``
        with code ``ALREADY_EXISTS``.

        The async form of ``Workspaces.create()``."""
        return cast("Workspace", await cls._data_async("POST", "/v1/workspaces", options, body=params))

    @classmethod
    async def get_async(cls, external_id: str, options: Optional[CallOptions] = None) -> Workspace:
        """Returns a tenant's workspace.

        The async form of ``Workspaces.get()``."""
        return cast(
            "Workspace", await cls._data_async("GET", path("/v1/workspaces/{}", external_id), options)
        )

    @classmethod
    async def update_async(
        cls, external_id: str, params: UpdateParams, options: Optional[CallOptions] = None
    ) -> Workspace:
        """Changes a tenant workspace's name, country or timezone.

        The async form of ``Workspaces.update()``."""
        return cast(
            "Workspace",
            await cls._data_async("PATCH", path("/v1/workspaces/{}", external_id), options, body=params),
        )

    @classmethod
    async def delete_async(cls, external_id: str, options: Optional[CallOptions] = None) -> Workspace:
        """Deletes a tenant's workspace and everything in it after a grace period, and
        stops its sends at once. Returns the workspace, whose ``deletesAt`` says when;
        ``cancel_deletion()`` stops it before then.

        The async form of ``Workspaces.delete()``."""
        return cast(
            "Workspace", await cls._data_async("DELETE", path("/v1/workspaces/{}", external_id), options)
        )

    @classmethod
    async def suspend_async(
        cls, external_id: str, options: Optional[IdempotentCallOptions] = None
    ) -> Workspace:
        """Stops every send in a tenant's workspace until ``resume()``. Messages already
        queued are skipped, not held.

        The async form of ``Workspaces.suspend()``."""
        return cast(
            "Workspace",
            await cls._data_async("POST", path("/v1/workspaces/{}/suspend", external_id), options),
        )

    @classmethod
    async def resume_async(
        cls, external_id: str, options: Optional[IdempotentCallOptions] = None
    ) -> Workspace:
        """Lifts a tenant workspace's suspension. Messages skipped meanwhile aren't
        sent.

        The async form of ``Workspaces.resume()``."""
        return cast(
            "Workspace", await cls._data_async("POST", path("/v1/workspaces/{}/resume", external_id), options)
        )

    @classmethod
    async def cancel_deletion_async(
        cls, external_id: str, options: Optional[IdempotentCallOptions] = None
    ) -> Workspace:
        """Cancels a tenant workspace's pending deletion. Messages skipped meanwhile
        aren't sent.

        The async form of ``Workspaces.cancel_deletion()``."""
        return cast(
            "Workspace",
            await cls._data_async("POST", path("/v1/workspaces/{}/cancel-deletion", external_id), options),
        )

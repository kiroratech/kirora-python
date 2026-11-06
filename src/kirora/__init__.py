"""The Kirora SDK for Python: contacts, events, segments, campaigns and transactional
messages.

import kirora

kirora.api_key = "sk_..."  # Or set KIRORA_API_KEY.
contact = kirora.Contacts.identify({"externalId": "user-123", "email": "ada@example.com"})
"""

from typing import Optional

import httpx

from . import (
    campaigns,
    contacts,
    embed_sessions,
    events,
    lists,
    messages,
    segments,
    suppressions,
    transactional,
    types,
    workspaces,
)
from ._base_client import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_MAX_RETRY_DELAY,
    DEFAULT_TIMEOUT,
    AppInfo,
    CallOptions,
    IdempotentCallOptions,
    RequestOptions,
)
from ._client import Kirora, default_client
from ._error_codes import ERROR_CODES
from ._logs import configure_from_env as _configure_logging_from_env
from ._pagination import AsyncPage, AsyncPager, Page
from ._response import RateLimit, ResponseInfo, last_response
from ._webhook_events import WEBHOOK_EVENTS
from .async_request import AsyncRequest
from .campaigns import *  # noqa: F403
from .contacts import *  # noqa: F403
from .embed_sessions import *  # noqa: F403
from .events import *  # noqa: F403
from .exceptions import (
    AuthenticationError,
    BadRequestError,
    ConflictError,
    KiroraConnectionError,
    KiroraError,
    KiroraException,
    KiroraResponseError,
    KiroraTimeoutError,
    KiroraWebhookVerificationError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    ServerError,
    WebhookVerificationFailure,
)
from .lists import *  # noqa: F403
from .messages import *  # noqa: F403
from .request import Request
from .segments import *  # noqa: F403
from .suppressions import *  # noqa: F403
from .transactional import *  # noqa: F403
from .user_tokens import UserTokens
from .version import __version__, get_version
from .webhooks import DEFAULT_WEBHOOK_TOLERANCE_SECONDS, VerifiedWebhook, WebhookHeaders, Webhooks
from .workspaces import *  # noqa: F403

# Settings for the resource classes, as ``kirora.Contacts.identify()``, read on each call.
# A ``Kirora`` client has its own instead.

api_key: Optional[str] = None
"""Your API key. When None, ``KIRORA_API_KEY`` is used."""
base_url: Optional[str] = None
"""The API host, without ``/v1``. When None, ``KIRORA_BASE_URL``, then
``https://api.kirora.io``."""
timeout: float = DEFAULT_TIMEOUT
"""How long each attempt may take, in seconds, including reading the response."""
max_retries: int = DEFAULT_MAX_RETRIES
"""Attempts after the first, from 0 to 10."""
max_retry_delay: float = DEFAULT_MAX_RETRY_DELAY
"""The longest single wait between attempts, in seconds."""
app_info: Optional[AppInfo] = None
"""Your app, added to the ``User-Agent``: ``{"name": "my-app", "version": "1.2.0"}``."""
default_http_client: Optional[httpx.Client] = None
"""An ``httpx.Client`` for the sync methods, such as one with a proxy. When None, the SDK
opens one and keeps it."""
default_async_http_client: Optional[httpx.AsyncClient] = None
"""An ``httpx.AsyncClient`` for the ``_async`` methods. When None, the SDK opens one per
event loop."""


_configure_logging_from_env()


def me(options: Optional[CallOptions] = None) -> "types.ApiCaller":
    """Returns the API key making the request and the workspace it acts in: a connection
    test. A revoked, expired or unknown key raises an ``AuthenticationError``."""
    return default_client().me(options)


async def me_async(options: Optional[CallOptions] = None) -> "types.ApiCaller":
    """The async form of ``me()``."""
    return await default_client().me_async(options)


def for_workspace(external_id: str) -> Kirora:
    """Returns a client that acts in the tenant workspace with this external id, with the
    module settings. Partner keys only."""
    return default_client().for_workspace(external_id)


__all__ = [
    # Settings
    "api_key",
    "base_url",
    "timeout",
    "max_retries",
    "max_retry_delay",
    "app_info",
    "default_http_client",
    "default_async_http_client",
    "__version__",
    "get_version",
    # Resources, with the rest added below with their models
    "Webhooks",
    "UserTokens",
    # Clients and requests
    "Kirora",
    "default_client",
    "me",
    "me_async",
    "for_workspace",
    "Request",
    "AsyncRequest",
    "AppInfo",
    "CallOptions",
    "IdempotentCallOptions",
    "RequestOptions",
    "Page",
    "AsyncPage",
    "AsyncPager",
    "ResponseInfo",
    "RateLimit",
    "last_response",
    # Webhooks
    "DEFAULT_WEBHOOK_TOLERANCE_SECONDS",
    "VerifiedWebhook",
    "WebhookHeaders",
    "WEBHOOK_EVENTS",
    # Errors
    "ERROR_CODES",
    "KiroraException",
    "KiroraError",
    "BadRequestError",
    "AuthenticationError",
    "PermissionDeniedError",
    "NotFoundError",
    "ConflictError",
    "RateLimitError",
    "ServerError",
    "KiroraConnectionError",
    "KiroraTimeoutError",
    "KiroraResponseError",
    "KiroraWebhookVerificationError",
    "WebhookVerificationFailure",
    # Types
    "types",
]
# Each resource's models, as ``kirora.ContactDetail``.
__all__ += campaigns.__all__
__all__ += contacts.__all__
__all__ += embed_sessions.__all__
__all__ += events.__all__
__all__ += lists.__all__
__all__ += messages.__all__
__all__ += segments.__all__
__all__ += suppressions.__all__
__all__ += transactional.__all__
__all__ += workspaces.__all__

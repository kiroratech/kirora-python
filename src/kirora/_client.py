from __future__ import annotations

import json
import os
import re
import threading
import uuid
from contextlib import asynccontextmanager, contextmanager
from types import TracebackType
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncIterator,
    Callable,
    Dict,
    Generic,
    Iterator,
    List,
    Mapping,
    Optional,
    Tuple,
    Type,
    TypeVar,
    cast,
    overload,
)
from urllib.parse import parse_qsl, unquote

import httpx
from typing_extensions import Self, Unpack

from ._base_client import (
    _USER_AGENT,
    DEFAULT_BASE_URL,
    DEFAULT_MAX_RETRIES,
    DEFAULT_MAX_RETRY_DELAY,
    DEFAULT_TIMEOUT,
    REQUEST_OPTIONS,
    AppInfo,
    Attempts,
    CallOptions,
    Prepared,
    RequestOptions,
    Shape,
    _app_product,
    _check_base_url,
    _check_retries,
    _check_timeout,
    _json_default,
    _query_value,
    _split_headers,
    check_options,
)
from ._connections import Connections
from ._pagination import AsyncPager, Page
from ._resource import APIResource, call_options
from ._retry import (
    changes_contact_lookup,
    is_safe_to_retry,
    not_found_is_done,
    operation_for,
    with_entry_keys,
)
from ._validation import check_id, check_number
from .async_request import AsyncRequest, list_pages_async
from .campaigns import Campaigns
from .contacts import Contacts
from .embed_sessions import EmbedSessions
from .events import Events
from .lists import Lists
from .messages import Messages
from .request import Request, list_pages
from .segments import Segments
from .suppressions import Suppressions
from .transactional import Transactional
from .workspaces import Workspaces

if TYPE_CHECKING:
    from .types import ApiCaller

__all__ = ["Kirora", "default_client"]

R = TypeVar("R", bound=APIResource)


class _Bound(Generic[R]):
    """A resource class, bound to the client it's read from on first use."""

    def __init__(self, resource: Type[R]) -> None:
        self._resource = resource
        self._name = ""

    def __set_name__(self, owner: type, name: str) -> None:
        self._name = name

    @overload
    def __get__(self, client: None, owner: Any) -> Type[R]: ...
    @overload
    def __get__(self, client: Kirora, owner: Any) -> Type[R]: ...
    def __get__(self, client: Optional[Kirora], owner: Any = None) -> Type[R]:
        if client is None:
            return self._resource
        bound = self._resource._bind(client)
        # Cached on the client, which reads it from there from now on.
        client.__dict__[self._name] = bound
        return bound


class Kirora:
    """A client of the Kirora API, with its own key and settings, for when the module
    settings (``kirora.api_key`` and the rest) aren't enough: a partner key acting in
    several tenant workspaces, or an app holding more than one key. Each attribute is a
    resource class bound to this client, so ``client.contacts.identify()`` takes what
    ``kirora.Contacts.identify()`` does. It holds your API key, so keep it on your server.
    It's safe to share between threads.

    Args:
        api_key: Your API key. If it's None or empty, ``KIRORA_API_KEY`` is used; a
            ``ValueError`` is raised if neither is set. Spaces and quotes around the key
            are ignored, as from a pasted ``.env`` value.
        base_url: The API host, without ``/v1``. Defaults to ``KIRORA_BASE_URL``, then
            ``https://api.kirora.io``.
        timeout: How long each attempt may take, in seconds, including reading the
            response; one that takes longer raises ``KiroraTimeoutError``. A call that
            retries can take longer in total.
        max_retries: Attempts after the first, from 0 to 10.
        max_retry_delay: The longest single wait between attempts, in seconds. When the
            API asks for a longer wait with ``Retry-After``, the call fails instead.
        workspace: Partner keys only: the external id of the tenant workspace to act in.
            See ``for_workspace()``.
        app_info: Your app, added to the ``User-Agent``: ``{"name": "my-app",
            "version": "1.2.0"}``.
        headers: Headers to send with every request. Those the SDK sets itself, such as
            ``Authorization``, take precedence.
        http_client: An ``httpx.Client`` for the sync methods, such as one with a proxy.
            The SDK doesn't close a client you pass. Redirects are never followed.
        async_http_client: An ``httpx.AsyncClient`` for the ``_async`` methods, shared
            by every call. Without one, each async call opens its own, which works in any
            event loop but doesn't reuse connections.
    """

    contacts = _Bound(Contacts)
    """The people you send to."""
    lists = _Bound(Lists)
    """Static lists of contacts, whose members you add and remove yourself."""
    segments = _Bound(Segments)
    """Audiences defined by rules, evaluated live at each send."""
    campaigns = _Bound(Campaigns)
    """Messages sent once to an audience, by email, push or both."""
    transactional = _Bound(Transactional)
    """One-off messages to one recipient, such as receipts, outside campaigns."""
    events = _Bound(Events)
    """What your contacts do, which starts journeys and feeds segments."""
    messages = _Bound(Messages)
    """The log of every message sent, from any campaign, journey or transactional send."""
    suppressions = _Bound(Suppressions)
    """Email addresses Kirora won't send to, such as after a bounce."""
    workspaces = _Bound(Workspaces)
    """Partner keys only: your tenants' workspaces."""
    embed_sessions = _Bound(EmbedSessions)
    """Partner keys only: sessions for embedding Kirora's builders in your app."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        max_retry_delay: float = DEFAULT_MAX_RETRY_DELAY,
        workspace: Optional[str] = None,
        app_info: Optional[AppInfo] = None,
        headers: Optional[Mapping[str, str]] = None,
        http_client: Optional[httpx.Client] = None,
        async_http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        key = (api_key or os.environ.get("KIRORA_API_KEY") or "").strip().strip("\"'").strip()
        if not key or key in ("undefined", "null", "None"):
            raise ValueError(
                "api_key is required: set kirora.api_key or KIRORA_API_KEY, or pass it to Kirora()"
            )
        from_env = base_url is None and bool(os.environ.get("KIRORA_BASE_URL"))
        url = base_url if base_url is not None else (os.environ.get("KIRORA_BASE_URL") or DEFAULT_BASE_URL)
        _check_base_url("KIRORA_BASE_URL" if from_env else "base_url", url)
        own_key, own_workspace, own_headers = _split_headers(headers, None, workspace)
        if own_key is not None:
            raise ValueError(
                "headers can't set Idempotency-Key for every call: pass idempotency_key per call"
            )
        self._api_key = key
        self._base_url = url.rstrip("/")
        self._timeout = _check_timeout(timeout)
        self._max_retries = _check_retries(max_retries)
        self._max_retry_delay = float(check_number("max_retry_delay", max_retry_delay, minimum=0))
        self._workspace = own_workspace
        self._headers = own_headers
        self._app_info: Optional[AppInfo] = dict(app_info) if app_info else None  # type: ignore[assignment]
        self._user_agent = f"{_USER_AGENT} {_app_product(app_info)}" if app_info else _USER_AGENT
        self._connections = Connections(http_client, async_http_client)
        # Only the client that made its connections closes them.
        self._owns_connections = True

    def me(self, options: Optional[CallOptions] = None) -> ApiCaller:
        """Returns the API key making the request and the workspace it acts in. Any valid
        key can call it, so it makes a connection test: a revoked, expired or unknown key
        raises an ``AuthenticationError``."""
        return cast(
            "ApiCaller", Request(self, "GET", "/v1/me", call_options(options, None), "data").perform()
        )

    async def me_async(self, options: Optional[CallOptions] = None) -> ApiCaller:
        """The async form of ``me()``."""
        request = AsyncRequest(self, "GET", "/v1/me", call_options(options, None), "data")
        return cast("ApiCaller", await request.perform())

    def for_workspace(self, external_id: str) -> Kirora:
        """Returns a client that acts in the tenant workspace with this external id,
        sharing this client's connections. Partner keys only. Raises a ``TypeError`` for an
        id that isn't a string, such as None, and a ``ValueError`` for an empty one, rather
        than act in the key's own workspace."""
        # The constructor's `workspace` is optional, so None there is the key's own
        # workspace. Here it would be a tenant id that went missing, such as from config.
        check_id("external_id", external_id)
        child = Kirora(self._api_key, **{**self._settings(), "workspace": external_id})
        child._share(self._connections)
        return child

    # --- Requests without a resource method -------------------------------------------

    def request(self, method: str, path: str, **options: Unpack[RequestOptions]) -> Any:
        """Sends a request to ``path``, which starts with ``/v1``, and returns the whole
        JSON body, or None for a 204 or a ``HEAD``. Raises a ``KiroraError`` for an API
        error, a ``KiroraConnectionError`` without a complete response, and a
        ``KiroraResponseError`` for a body that isn't JSON."""
        return self._request(method, path, options, "any").perform()

    async def request_async(self, method: str, path: str, **options: Unpack[RequestOptions]) -> Any:
        """The async form of ``request()``."""
        return await self._request_async(method, path, options, "any").perform()

    def request_data(self, method: str, path: str, **options: Unpack[RequestOptions]) -> Any:
        """Sends a request as ``request()`` does, and returns the body's ``data``."""
        return self._request(method, path, options, "data").perform()

    async def request_data_async(self, method: str, path: str, **options: Unpack[RequestOptions]) -> Any:
        """The async form of ``request_data()``."""
        return await self._request_async(method, path, options, "data").perform()

    def request_list(self, path: str, **options: Unpack[RequestOptions]) -> Page[Any]:
        """Fetches the first page of a paginated endpoint, sending ``query`` with every
        page. Iterate the page for every item."""
        check_options(options, REQUEST_OPTIONS)
        return list_pages(self, path, options)

    def request_list_async(self, path: str, **options: Unpack[RequestOptions]) -> AsyncPager[Any]:
        """Lists a paginated endpoint. Await it for the first page, or ``async for`` over
        it for every item."""
        check_options(options, REQUEST_OPTIONS)
        return list_pages_async(self, path, options)

    @contextmanager
    def request_raw(
        self, method: str, path: str, **options: Unpack[RequestOptions]
    ) -> Iterator[httpx.Response]:
        """Sends a request as ``request()`` does, and yields the successful response
        without reading its body, for one that isn't JSON or is too large to buffer, such
        as a CSV export. The response is closed when the block ends::

            with client.request_raw("GET", "/v1/messages/exports/ID/download") as response:
                for chunk in response.iter_bytes():
                    ...
        """
        with self._request(method, path, options, "raw").open() as response:
            yield response

    @asynccontextmanager
    async def request_raw_async(
        self, method: str, path: str, **options: Unpack[RequestOptions]
    ) -> AsyncIterator[httpx.Response]:
        """The async form of ``request_raw()``; use ``async with``."""
        async with self._request_async(method, path, options, "raw").open() as response:
            yield response

    def close(self) -> None:
        """Closes the connections this client opened; a later call opens new ones.
        Clients you passed, and a parent's connections, aren't closed."""
        if self._owns_connections:
            self._connections.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> None:
        self.close()

    def __repr__(self) -> str:
        return f"Kirora(base_url={self._base_url!r}, workspace={self._workspace!r})"

    # --- Internals -------------------------------------------------------------------

    def _share(self, connections: Connections) -> None:
        """Sends with ``connections``, which another client owns and closes."""
        self._connections = connections
        self._owns_connections = False

    def _request(self, method: str, path: str, options: Mapping[str, Any], shape: Shape) -> Request:
        check_options(options, REQUEST_OPTIONS)
        return Request(self, method, path, options, shape)

    def _request_async(
        self, method: str, path: str, options: Mapping[str, Any], shape: Shape
    ) -> AsyncRequest:
        check_options(options, REQUEST_OPTIONS)
        return AsyncRequest(self, method, path, options, shape)

    def _attempts(self, method: str, path: str, options: Mapping[str, Any], shape: Shape) -> Attempts:
        timeout = options.get("timeout")
        max_retries = options.get("max_retries")
        return Attempts(
            self._prepare(method, path, options),
            shape,
            timeout=self._timeout if timeout is None else _check_timeout(timeout),
            max_retries=self._max_retries if max_retries is None else _check_retries(max_retries),
            max_retry_delay=self._max_retry_delay,
        )

    def _settings(self) -> Dict[str, Any]:
        """The settings a copy of this client is made with."""
        return {
            "base_url": self._base_url,
            "timeout": self._timeout,
            "max_retries": self._max_retries,
            "max_retry_delay": self._max_retry_delay,
            "workspace": self._workspace,
            "app_info": self._app_info,
            "headers": dict(self._headers),
        }

    def _page_options(self, options: Mapping[str, Any]) -> Callable[[Optional[str]], Dict[str, Any]]:
        """The options to fetch each page of a list with, given its cursor. Copied, so
        changing them between pages can't change what a later page asks for, such as the
        workspace its cursor belongs to."""
        filters = dict(options.get("query") or {})
        fixed: Dict[str, Any] = {k: v for k, v in options.items() if k != "query"}
        if fixed.get("headers") is not None:
            fixed["headers"] = dict(fixed["headers"])
        return lambda cursor: {**fixed, "query": filters if cursor is None else {**filters, "cursor": cursor}}

    def _prepare(self, method: str, path: str, options: Mapping[str, Any]) -> Prepared:
        method = method.upper()
        if not path.startswith("/"):
            raise ValueError(f'{method} {path}: the path must start with "/"')
        if re.search(r"[#\\\t\n\r]", path):
            raise ValueError(f'{method} {path}: the path can\'t have a "#", "\\", tab or newline')
        pathname, _, path_query = path.partition("?")
        segments = pathname.split("/")
        # A `.` or `..` segment, or its encoded form such as `%2e%2e`, would send the
        # request to a different endpoint than the one checked.
        if any(unquote(segment) in ("", ".", "..") for segment in segments[1:]):
            raise ValueError(f'{method} {path}: an id in the path can\'t be empty, "." or ".."')
        own_key, call_workspace, call_headers = _split_headers(
            options.get("headers"), options.get("idempotency_key"), options.get("workspace")
        )
        endpoint = operation_for(method, segments)

        # A query in the path is sent, and counts as `query`, which wins over it.
        query = {k: v for k, v in (options.get("query") or {}).items() if v is not None}
        params: List[Tuple[str, str]] = [
            (k, v) for k, v in parse_qsl(path_query, keep_blank_values=True) if k not in query
        ]
        params.extend((k, _query_value(v)) for k, v in query.items())
        url = httpx.URL(self._base_url + pathname, params=params)

        headers = {
            **self._headers,
            **call_headers,
            "authorization": f"Bearer {self._api_key}",
            "accept": "application/json",
            "user-agent": self._user_agent,
        }
        content: Optional[bytes] = None
        body: Any = None
        if "body" in options and options["body"] is not None:
            headers["content-type"] = "application/json"
            body = with_entry_keys(options["body"], endpoint.entries if endpoint else None)
            content = json.dumps(body, default=_json_default, ensure_ascii=False).encode()
        # The spec says which endpoints take a key. One newer than this SDK is sent the
        # caller's, and trusted to take it.
        if endpoint is None or (endpoint.accepts_key and own_key is not None):
            key = own_key
        elif endpoint.accepts_key:
            key = str(uuid.uuid4())
        elif own_key is None:
            key = None
        else:
            raise ValueError(f"{method} {path} doesn't take an idempotency key")
        if key is not None:
            headers["idempotency-key"] = key
        workspace = call_workspace if call_workspace is not None else self._workspace
        if workspace is not None:
            headers["kirora-workspace"] = workspace
        return Prepared(
            operation=f"{method} {path}",
            method=method,
            url=url,
            headers=headers,
            content=content,
            repeatable=is_safe_to_retry(
                method,
                endpoint,
                key,
                options.get("repeatable"),
                changes_contact_lookup(endpoint, segments, params, body),
            ),
            not_found_is_done=not_found_is_done(method, endpoint),
        )


# The module settings, as `kirora.api_key`, with their defaults. `default_client()` makes
# its client from them, and tests restore them.
DEFAULT_SETTINGS: Dict[str, Any] = {
    "api_key": None,
    "base_url": None,
    "timeout": DEFAULT_TIMEOUT,
    "max_retries": DEFAULT_MAX_RETRIES,
    "max_retry_delay": DEFAULT_MAX_RETRY_DELAY,
    "app_info": None,
    "default_http_client": None,
    "default_async_http_client": None,
}

_default: Optional[Tuple[Tuple[Any, ...], Kirora]] = None
_default_lock = threading.Lock()
# The connections of the module settings' clients, whatever else changes.
_shared = Connections()


def default_client() -> Kirora:
    """The client the module settings describe, such as ``kirora.api_key``, which the
    resource classes use. Made again when a setting changes, or the environment variable
    a setting falls back to; the clients share their connections."""
    global _default
    import kirora

    settings = {name: getattr(kirora, name) for name in DEFAULT_SETTINGS}
    # Copied, so a change made to it in place counts as a change.
    settings["app_info"] = dict(settings["app_info"]) if settings["app_info"] else None
    key = (settings, os.environ.get("KIRORA_API_KEY"), os.environ.get("KIRORA_BASE_URL"))
    current = _default
    if current is not None and current[0] == key:
        return current[1]
    with _default_lock:
        if _default is not None and _default[0] == key:
            return _default[1]
        kwargs = dict(settings)  # The key keeps `settings` as it is.
        http, async_http = kwargs.pop("default_http_client"), kwargs.pop("default_async_http_client")
        client = Kirora(**kwargs)
        client._share(_shared if http is None and async_http is None else Connections(http, async_http))
        _default = (key, client)
        return client

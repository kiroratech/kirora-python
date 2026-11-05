from __future__ import annotations

import datetime as _dt
import email.utils
import json
import random
import re
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, Mapping, Optional, Tuple, Union, cast

import httpx
from typing_extensions import Literal, NotRequired, Required, TypedDict

from ._response import RateLimit, ResponseInfo, with_response
from ._retry import (
    may_have_run,
    should_retry,
)
from ._validation import check_id, check_number, parse_uint
from .exceptions import (
    KiroraConnectionError,
    KiroraError,
    KiroraException,
    KiroraResponseError,
    KiroraTimeoutError,
    error_class,
)
from .version import __version__

if TYPE_CHECKING:
    from .types import FieldError

__all__ = ["AppInfo", "RequestOptions", "CallOptions", "IdempotentCallOptions"]

DEFAULT_BASE_URL = "https://api.kirora.io"
DEFAULT_TIMEOUT = 30.0
DEFAULT_MAX_RETRIES = 3
DEFAULT_MAX_RETRY_DELAY = 30.0
MAX_RETRIES = 10
MAX_RESPONSE_BYTES = 64 * 1024 * 1024
_TOKEN = re.compile(r"^[\w.-]+$", re.ASCII)
_USER_AGENT = f"kirora-python/{__version__} python/{'.'.join(map(str, sys.version_info[:3]))}"

Shape = Literal["any", "data", "page", "raw"]
QueryValue = Union[str, int, float, bool, _dt.datetime, _dt.date, None]


class AppInfo(TypedDict, total=False):
    """Your app, added to the ``User-Agent`` header. ``name`` and ``version`` can't
    contain spaces or slashes."""

    name: Required[str]
    version: NotRequired[str]


class CallOptions(TypedDict, total=False):
    """Options every resource method takes as keyword arguments."""

    workspace: str
    """Partner keys only: overrides the client's workspace for this call."""
    timeout: float
    """Overrides the client's ``timeout`` for this call, in seconds."""
    max_retries: int
    """Overrides the client's ``max_retries`` for this call."""
    headers: Mapping[str, str]
    """Headers to send, over the client's ``headers``."""


class IdempotentCallOptions(CallOptions, total=False):
    """``CallOptions`` for a method that creates, sends or records something."""

    idempotency_key: str
    """Makes your own retries safe as well as the SDK's. Reuse it only for the same
    operation and body: the API refuses a key reused with a different body
    (``IDEMPOTENCY_KEY_REUSED``)."""


class RequestOptions(IdempotentCallOptions, total=False):
    """Options for ``Kirora.request()`` and its variants."""

    query: Mapping[str, QueryValue]
    """Query parameters. Those that are None are left out."""
    body: Any
    """Sent as JSON."""
    repeatable: bool
    """Whether the call is safe to repeat after a network error or a 5xx. Defaults to
    what the API spec says of the endpoint; an endpoint newer than this SDK is safe to
    repeat if it's a ``GET``, ``HEAD``, ``PUT`` or ``DELETE``. A call with a key is safe
    whatever this says. A 429, or a connection that was never made, is retried either
    way."""


# A TypedDict's annotations include those it inherits. Whether a resource method takes
# `idempotency_key` is its endpoint's, which `_prepare()` checks.
CALL_OPTIONS = frozenset(IdempotentCallOptions.__annotations__)
REQUEST_OPTIONS = frozenset(RequestOptions.__annotations__)


def check_options(options: Mapping[str, Any], allowed: frozenset = CALL_OPTIONS) -> None:  # type: ignore[type-arg]
    unknown = sorted(set(options) - allowed)
    if unknown:
        raise TypeError(f"unexpected keyword argument {unknown[0]!r}")


@dataclass
class Prepared:
    operation: str
    method: str
    url: httpx.URL
    headers: Dict[str, str]
    content: Optional[bytes]
    repeatable: bool
    not_found_is_done: bool


class Attempts:
    """One call's attempts: what to send, and after each failure, whether to try again."""

    def __init__(
        self, prepared: Prepared, shape: Shape, *, timeout: float, max_retries: int, max_retry_delay: float
    ) -> None:
        self.prepared = prepared
        self.shape: Shape = shape
        self.timeout = timeout
        self.max_retries = max_retries
        self.max_retry_delay = max_retry_delay
        # A delete that 404s after an attempt that may have reached the server: that
        # attempt may have done it. Not for a raw call, which is promised a response.
        self.not_found_is_done = prepared.not_found_is_done and shape != "raw"
        self.attempt = 1
        self.may_have_run = False

    def after(self, error: KiroraException) -> Optional[float]:
        """Returns how long to wait before trying again, or None if an earlier attempt
        already did the call's work, which the call then returns. Raises ``error`` when the
        call should stop."""
        if (
            self.not_found_is_done
            and self.may_have_run
            and isinstance(error, KiroraError)
            and error.status == 404
        ):
            return None
        self.may_have_run = self.may_have_run or may_have_run(error)
        if self.attempt > self.max_retries or not should_retry(error, self.prepared.repeatable):
            raise error
        wait = self._backoff(error)
        if wait is None:
            raise error
        self.attempt += 1
        return wait

    def _backoff(self, error: BaseException) -> Optional[float]:
        retry_after = error.retry_after if isinstance(error, KiroraError) else None
        if retry_after is None:
            jittered: float = 2 ** (self.attempt - 1) * (0.75 + random.random() * 0.5)  # noqa: S311
            return min(jittered, self.max_retry_delay)
        # Retrying sooner than the API asked would only be refused again.
        if retry_after > self.max_retry_delay:
            return None
        return min(retry_after * (1 + random.random() * 0.25), self.max_retry_delay)  # noqa: S311

    def request_for(self, http: Any) -> httpx.Request:
        """The request for one attempt, built by ``http``, a sync or async httpx client."""
        prepared = self.prepared
        return cast(
            httpx.Request,
            http.build_request(
                prepared.method,
                prepared.url,
                headers=prepared.headers,
                content=prepared.content,
                timeout=httpx.Timeout(self.timeout),
            ),
        )

    def failed(self, error: Exception) -> KiroraConnectionError:
        """The error for an attempt that got no complete response."""
        # A connection that was never made, or never taken from the pool, means the API
        # never saw the request.
        unsent = isinstance(error, (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout))
        # TimeoutError is the async client's deadline, from `anyio.fail_after()`.
        if isinstance(error, (httpx.TimeoutException, TimeoutError)):
            return KiroraTimeoutError(self.prepared.operation, self.timeout, error, unsent=unsent)
        return KiroraConnectionError(self.prepared.operation, error, unsent=unsent)

    def read_failed(self, response: httpx.Response, error: Exception) -> KiroraException:
        """The error for a body that couldn't be read in full, including one cut off at
        the deadline. An error status still says what went wrong, and whether to retry,
        from its status and headers; the code and message its body held are lost."""
        return self.failed(error) if response.is_success else _to_api_error(response, None)

    def hand_over(self, response: httpx.Response) -> bool:
        """Whether to give the caller ``response`` unread, from ``request_raw()``. Raises
        for a redirect, and for a body too large to read."""
        prepared = self.prepared
        if 300 <= response.status_code < 400 and response.status_code != 304:
            location = response.headers.get("location")
            raise KiroraResponseError(
                f"{prepared.operation} was redirected{f' to {location}' if location else ''}, "
                "which isn't followed: check base_url",
                status=response.status_code,
                request_id=response.headers.get("x-request-id"),
            )
        if self.shape == "raw" and response.is_success:
            return True
        length = parse_uint(response.headers.get("content-length"), 20)
        if length is not None and length > MAX_RESPONSE_BYTES:
            raise _too_large(prepared, response)
        return False

    def add(self, body: bytearray, chunk: bytes, response: httpx.Response) -> None:
        body += chunk
        if len(body) > MAX_RESPONSE_BYTES:
            raise _too_large(self.prepared, response)

    def finish(self, response: httpx.Response, body: bytearray) -> Any:
        """The call's result, from a response read in full."""
        parsed = _parse(self.prepared, response, body, self.shape)
        # A page is built by the caller, which knows how to fetch the next.
        if parsed is None or self.shape == "page":
            return parsed
        payload, info = parsed
        return with_response(payload, info)


def _too_large(prepared: Prepared, response: httpx.Response) -> KiroraException:
    error = KiroraResponseError(
        f"{prepared.operation} returned {response.status_code} with a body larger than "
        f"{MAX_RESPONSE_BYTES // 1024 // 1024} MiB",
        status=response.status_code,
        request_id=response.headers.get("x-request-id"),
    )
    # The status still says what went wrong, and whether to retry.
    if response.is_success:
        return error
    api_error = _to_api_error(response, None)
    api_error.__cause__ = error
    return api_error


def _parse(prepared: Prepared, response: httpx.Response, body: bytearray, shape: Shape) -> Any:
    if not response.is_success:
        raise _to_api_error(response, _parse_json(body))
    request_id = response.headers.get("x-request-id")

    def invalid(problem: str) -> KiroraResponseError:
        return KiroraResponseError(
            f"{prepared.operation} returned {response.status_code} {problem}",
            status=response.status_code,
            request_id=request_id,
        )

    no_body = response.status_code == 204 or prepared.method == "HEAD" or not body or body.isspace()
    if no_body and shape == "any":
        return None
    try:
        payload = json.loads(body)
    except ValueError as cause:
        raise invalid("with a body that is not JSON") from cause
    if shape == "data":
        if not isinstance(payload, dict) or not isinstance(payload.get("data"), (dict, list)):
            raise invalid("without an object or array in a `data` envelope")
        payload = payload["data"]
    if shape == "page" and not _is_page(payload):
        raise invalid("without a page of `data` and `meta.pagination`")
    info = ResponseInfo(
        status=response.status_code,
        headers=response.headers,
        request_id=request_id,
        idempotency_replay=response.headers.get("idempotency-replay") == "true",
        rate_limit=_parse_rate_limit(response.headers),
    )
    return payload, info


_CODES_BY_STATUS = {
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    413: "PAYLOAD_TOO_LARGE",
    415: "UNSUPPORTED_MEDIA_TYPE",
    429: "RATE_LIMITED",
    503: "SERVICE_UNAVAILABLE",
}


def _to_api_error(response: httpx.Response, payload: Any) -> KiroraError:
    error = payload.get("error") if isinstance(payload, dict) else None
    if not isinstance(error, dict):
        error = {}

    def string(value: Any) -> Optional[str]:
        return value if isinstance(value, str) and value else None

    status = response.status_code
    errors = error.get("errors")
    return error_class(status)(
        code=string(error.get("code"))
        or _CODES_BY_STATUS.get(status)
        or ("BAD_REQUEST" if status < 500 else "INTERNAL_ERROR"),
        message=string(error.get("message")) or f"HTTP {status}",
        status=status,
        errors=[
            cast("FieldError", e)
            for e in (errors if isinstance(errors, list) else [])
            if isinstance(e, dict) and isinstance(e.get("field"), str) and isinstance(e.get("message"), str)
        ],
        details=error.get("details"),
        request_id=response.headers.get("x-request-id") or string(error.get("requestId")),
        retry_after=_parse_retry_after(response.headers.get("retry-after")),
        rate_limit=_parse_rate_limit(response.headers),
    )


def _parse_json(body: bytearray) -> Any:
    try:
        return json.loads(body)
    except ValueError:
        return None


_MONTH = "(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
_TIME = r"\d{2}:\d{2}:\d{2}"
# The three HTTP date formats a recipient must accept: IMF-fixdate, then the obsolete
# RFC 850 and asctime. asctime has no zone, but is always GMT.
_HTTP_DATES = [
    (re.compile(rf"^(Mon|Tue|Wed|Thu|Fri|Sat|Sun), \d{{2}} {_MONTH} \d{{4}} {_TIME} GMT$"), None),
    (
        re.compile(
            r"^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday), "
            rf"\d{{2}}-{_MONTH}-\d{{2}} {_TIME} GMT$"
        ),
        "%A, %d-%b-%y %H:%M:%S GMT",
    ),
    (re.compile(rf"^(Mon|Tue|Wed|Thu|Fri|Sat|Sun) {_MONTH} [ \d]\d {_TIME} \d{{4}}$"), None),
]


def _parse_retry_after(header: Optional[str]) -> Optional[float]:
    if header is None:
        return None
    value = header.strip()
    if re.fullmatch(r"\d+(\.\d+)?", value, re.ASCII):
        return float(value)
    for pattern, strptime in _HTTP_DATES:
        if not pattern.match(value):
            continue
        try:
            if strptime is not None:
                when = _dt.datetime.strptime(value, strptime).replace(tzinfo=_dt.timezone.utc)
            else:
                parsed = email.utils.parsedate_to_datetime(value)
                when = parsed if parsed.tzinfo else parsed.replace(tzinfo=_dt.timezone.utc)
        except (TypeError, ValueError):
            return None
        return max(0.0, (when - _dt.datetime.now(_dt.timezone.utc)).total_seconds())
    return None


def _parse_rate_limit(headers: httpx.Headers) -> Optional[RateLimit]:
    limit, remaining, reset = (
        parse_uint((headers.get(name) or "").strip(), 18)
        for name in ("ratelimit-limit", "ratelimit-remaining", "ratelimit-reset")
    )
    if limit is None or remaining is None or reset is None:
        return None
    return RateLimit(limit=limit, remaining=remaining, reset_seconds=reset)


def _is_page(value: Any) -> bool:
    if not isinstance(value, dict) or not isinstance(value.get("data"), list):
        return False
    meta = value.get("meta")
    pagination = meta.get("pagination") if isinstance(meta, dict) else None
    return (
        isinstance(pagination, dict)
        and isinstance(pagination.get("limit"), int)
        and not isinstance(pagination.get("limit"), bool)
        and (pagination.get("nextCursor") is None or isinstance(pagination.get("nextCursor"), str))
        and "nextCursor" in pagination
    )


def _query_value(value: QueryValue) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (_dt.datetime, _dt.date)):
        return _iso(value)
    return str(value)


def _iso(value: Union[_dt.datetime, _dt.date]) -> str:
    if isinstance(value, _dt.datetime):
        if value.tzinfo is None:
            raise ValueError(
                f"{value!r} has no timezone: pass an aware datetime, such as with tzinfo=timezone.utc"
            )
        text = value.isoformat()
        return text[:-6] + "Z" if text.endswith("+00:00") else text
    return value.isoformat()


def _json_default(value: Any) -> Any:
    if isinstance(value, (_dt.datetime, _dt.date)):
        return _iso(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _check_base_url(name: str, base_url: str) -> None:
    try:
        url = httpx.URL(base_url)
    except (httpx.InvalidURL, TypeError):
        url = None
    if url is None or not url.host or url.scheme not in ("http", "https"):
        raise ValueError(f"{name} must be an absolute http or https URL, not {base_url!r}")
    if "?" in base_url or "#" in base_url:
        raise ValueError(f"{name} can't have a query or fragment: {base_url!r}")


def _check_timeout(value: Any) -> float:
    return float(check_number("timeout", value, minimum=0, above=True))


def _check_retries(value: Any) -> int:
    return int(check_number("max_retries", value, minimum=0, maximum=MAX_RETRIES, integer=True))


def _split_headers(
    given: Optional[Mapping[str, str]],
    idempotency_key: Optional[str],
    workspace: Optional[str],
) -> Tuple[Optional[str], Optional[str], Dict[str, str]]:
    """Lower-cases ``given``'s names and takes out ``Idempotency-Key`` and
    ``Kirora-Workspace``, which are the options of the same name: an option given
    explicitly wins over its header."""
    headers = {name.lower(): value for name, value in (given or {}).items()}
    header_key = headers.pop("idempotency-key", None)
    header_workspace = headers.pop("kirora-workspace", None)
    key = idempotency_key if idempotency_key is not None else header_key
    in_workspace = workspace if workspace is not None else header_workspace
    if key is not None:
        check_id("idempotency_key", key)
    # An empty `Kirora-Workspace` would act in the key's own workspace instead.
    if in_workspace is not None:
        check_id("workspace", in_workspace)
    return key, in_workspace, headers


def _app_product(app_info: Mapping[str, Any]) -> str:
    name = app_info.get("name")
    version = app_info.get("version")
    _check_token("app_info name", name)
    if version is None:
        return str(name)
    _check_token("app_info version", version)
    return f"{name}/{version}"


def _check_token(name: str, value: Any) -> None:
    if not isinstance(value, str) or not _TOKEN.fullmatch(value):
        raise ValueError(f"{name} must be letters, digits and .-_ with no spaces or slashes, not {value!r}")

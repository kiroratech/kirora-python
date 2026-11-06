"""Kirora exceptions.

Every error the SDK raises subclasses ``KiroraException``. An error response from the
API is a ``KiroraError``, or the subclass for its status, such as ``NotFoundError``;
branch on its ``code`` for the specific reason. Invalid arguments, such as an empty id,
raise ``ValueError`` or ``TypeError`` instead, before anything is sent.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Type

from typing_extensions import Literal

from ._error_codes import ERROR_CODES

if TYPE_CHECKING:
    from ._response import RateLimit, ResponseInfo
    from .types import FieldError

__all__ = [
    "KiroraException",
    "KiroraError",
    "BadRequestError",
    "AuthenticationError",
    "PermissionDeniedError",
    "NotFoundError",
    "ConflictError",
    "RateLimitError",
    "ServerError",
    "error_class",
    "KiroraConnectionError",
    "KiroraTimeoutError",
    "KiroraResponseError",
    "KiroraWebhookVerificationError",
    "WebhookVerificationFailure",
]

_KNOWN_CODES = frozenset(ERROR_CODES)
_NOT_RETRYABLE_5XX = frozenset({501, 505})


class KiroraException(Exception):
    """The base of every error the SDK raises, so one ``except`` can catch them all."""

    def __reduce__(self) -> Tuple[Any, ...]:
        return (_restore, (type(self), self.args, self.__dict__))


def _restore(cls: Type[KiroraException], args: Tuple[Any, ...], state: Dict[str, Any]) -> KiroraException:
    """Rebuilds an unpickled error without calling its ``__init__``."""
    error = cls.__new__(cls)
    error.args = args
    error.__dict__.update(state)
    return error


class KiroraError(KiroraException):
    """An error response from the API. Branch on its ``code``.

    Attributes:
        code: What went wrong, for code to branch on, such as ``"NOT_FOUND"``. A code
            added to the API after this version of the SDK still comes through, as a
            string; ``is_known_code()`` tells you which.
        status: The HTTP status.
        message: The API's explanation, for people rather than code.
        errors: On ``VALIDATION_ERROR`` and ``DRAFT_INCOMPLETE``, each field the request
            got wrong. Otherwise empty.
        details: What else the error carries, depending on ``code``.
        request_id: The ``X-Request-Id`` header. Quote it to Kirora support.
        retry_after: How long the API asked you to wait before trying again, in
            seconds, from ``Retry-After``.
        rate_limit: The rate limit the response reported, if it had valid
            ``RateLimit-*`` headers.
        last_response: The HTTP response the error came from.
    """

    def __init__(
        self,
        *,
        code: str,
        message: str,
        status: int,
        errors: Optional[List[FieldError]] = None,
        details: Any = None,
        request_id: Optional[str] = None,
        retry_after: Optional[float] = None,
        rate_limit: Optional[RateLimit] = None,
        last_response: Optional[ResponseInfo] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.errors: List[FieldError] = list(errors or [])
        self.details = details
        self.request_id = request_id
        self.retry_after = retry_after
        self.rate_limit = rate_limit
        self.last_response = last_response

    def __str__(self) -> str:
        suffix = f" (request {self.request_id})" if self.request_id else ""
        return f"{self.code}: {self.message}{suffix}"

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(code={self.code!r}, status={self.status}, "
            f"message={self.message!r}, request_id={self.request_id!r})"
        )

    def is_known_code(self) -> bool:
        """Whether ``code`` is one of ``ERROR_CODES``, the codes this SDK knows."""
        return self.code in _KNOWN_CODES

    @property
    def is_retryable(self) -> bool:
        """Whether the same request might succeed later: a 429, a 5xx other than 501
        and 505, or ``IDEMPOTENCY_KEY_IN_USE``. A write repeated without an idempotency
        key can still be applied twice.
        """
        return (
            self.status == 429
            or (self.status >= 500 and self.status not in _NOT_RETRYABLE_5XX)
            or self.code == "IDEMPOTENCY_KEY_IN_USE"
        )


class BadRequestError(KiroraError):
    """400: the request is malformed or invalid, as with ``VALIDATION_ERROR``."""


class AuthenticationError(KiroraError):
    """401: the API key is missing, revoked, expired or unknown."""


class PermissionDeniedError(KiroraError):
    """403: the key can't do this, such as without a scope it needs."""


class NotFoundError(KiroraError):
    """404: nothing has that id, in this workspace."""


class ConflictError(KiroraError):
    """409: the request conflicts with the current state, such as ``ALREADY_EXISTS``."""


class RateLimitError(KiroraError):
    """429: too many requests. ``retry_after`` says how long the API asked you to wait."""


class ServerError(KiroraError):
    """5xx: the API failed, or is unavailable. Safe requests are retried first."""


_ERRORS_BY_STATUS = {
    400: BadRequestError,
    401: AuthenticationError,
    403: PermissionDeniedError,
    404: NotFoundError,
    409: ConflictError,
    429: RateLimitError,
}


def error_class(status: int) -> type[KiroraError]:
    """The ``KiroraError`` subclass for an error status."""
    if status >= 500:
        return ServerError
    return _ERRORS_BY_STATUS.get(status, KiroraError)


class KiroraConnectionError(KiroraException):
    """A request that got no complete response, such as after a network error, or a
    connection that dropped while the body was read. ``__cause__`` holds the underlying
    error.

    Attributes:
        request_sent: False if the request never reached the API, so it's safe to send
            again.
    """

    def __init__(self, operation: str, cause: BaseException, *, unsent: bool = False) -> None:
        super().__init__(f"{operation} failed: {str(cause) or type(cause).__name__}")
        self.__cause__ = cause
        self.request_sent = not unsent


class KiroraTimeoutError(KiroraConnectionError):
    """An attempt that took longer than the client's ``timeout``."""

    def __init__(self, operation: str, timeout: float, cause: BaseException, *, unsent: bool = False) -> None:
        super().__init__(operation, cause, unsent=unsent)
        self.args = (f"{operation} timed out after {timeout:g}s",)


class KiroraResponseError(KiroraException):
    """A response the SDK can't use, such as an HTML page from a proxy with a 200
    status, or a redirect.
    """

    def __init__(self, message: str, *, status: int, request_id: Optional[str] = None) -> None:
        super().__init__(message)
        self.status = status
        self.request_id = request_id


WebhookVerificationFailure = Literal[
    "invalid_timestamp", "signature_mismatch", "timestamp_outside_tolerance", "invalid_headers"
]
"""Why a webhook failed verification.

``signature_mismatch`` usually means the wrong secret, or a body that was parsed before
it was verified. ``timestamp_outside_tolerance`` means a replay, or a server clock out of
sync. ``invalid_headers`` means the signature, event or event id header is missing or
differs from the body's, or the attempt header isn't a whole number from 1.
"""


class KiroraWebhookVerificationError(KiroraException):
    """Raised by ``Webhooks.assert_valid()``, ``Webhooks.assert_signature()`` and
    ``Webhooks.assert_headers()`` for a webhook that fails verification.
    """

    def __init__(self, reason: WebhookVerificationFailure, message: str) -> None:
        super().__init__(message)
        self.reason: WebhookVerificationFailure = reason

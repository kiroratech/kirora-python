"""How a call may be retried, from the spec's ``x-retry``:

- ``read`` changes nothing.
- ``converges`` leaves the same end state however often it's repeated.
- ``state`` moves a resource to a state, which a repeat can't do twice.
- ``done`` finishes or removes something, which a repeat finds already done.
- ``entries`` is a batch whose entries each carry an idempotency key.
- ``key`` and ``unsafe`` can do their work twice, so need an idempotency key.
- ``unique`` creates something unique, which a repeat after success is refused.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.parse import unquote

from ._operations import OPERATIONS, Operation
from .exceptions import KiroraConnectionError, KiroraError

_SAFE_WITHOUT_KEY = frozenset({"read", "converges", "state", "done", "entries"})


def _by_shape() -> Dict[Tuple[str, int], List[Tuple[List[str], Operation]]]:
    templates: Dict[Tuple[str, int], List[Tuple[List[str], Operation]]] = {}
    for key, operation in OPERATIONS.items():
        method, path = key.split(" ", 1)
        segments = path.split("/")
        templates.setdefault((method, len(segments)), []).append((segments, operation))
    return templates


# Each method's path templates, by their number of segments.
_TEMPLATES = _by_shape()


def operation_for(method: str, segments: Sequence[str]) -> Optional[Operation]:
    """Finds the operation whose path template matches ``segments``, the path split on
    ``/``. Of several matches, the one with the most literal segments wins, as
    ``/v1/templates/gallery`` is a closer match than ``/v1/templates/{id}``.
    """
    best = -1
    found: Optional[Operation] = None
    for template, operation in _TEMPLATES.get((method, len(segments)), []):
        literals = 0
        for index, segment in enumerate(template):
            if segment.startswith("{"):
                continue
            if segment != segments[index]:
                literals = -1
                break
            literals += 1
        if literals > best:
            best = literals
            found = operation
    return found


def is_safe_to_retry(
    method: str,
    operation: Optional[Operation],
    key: Optional[str],
    repeatable: Optional[bool],
    unsafe: bool,
) -> bool:
    """Whether a call can be repeated without doing its work twice. ``key`` is the one
    sent, which only an endpoint that takes keys, or one missing from the spec this SDK
    was built from, is given. ``unsafe`` is for a call whose arguments make a repeat
    unsafe on an endpoint that would otherwise allow it.
    """
    if key is not None:
        return True
    if repeatable is not None:
        return repeatable
    if operation is None:
        return method in ("GET", "HEAD", "PUT", "DELETE") and not unsafe
    return operation.retry in _SAFE_WITHOUT_KEY and not unsafe


def changes_contact_lookup(
    operation: Optional[Operation],
    segments: Sequence[str],
    query: Sequence[Tuple[str, str]],
    body: Any,
) -> bool:
    """Whether a call to ``updateContact`` changes the email or ``externalId`` the
    contact is looked up by, so that a retry after the first attempt succeeded would look
    it up by its old value. The API matches an email trimmed and without case.
    """
    if operation is None or operation.id != "updateContact" or not isinstance(body, dict):
        return False
    sent = body
    contact_id = unquote(segments[-1])

    def changes(value: Any, same: Any) -> bool:
        return value is None or (isinstance(value, str) and not same(value))

    def email(value: str) -> str:
        return value.strip().lower()

    # Every `idType` given, in case the API reads another than the first.
    for name, id_type in query:
        if name != "idType":
            continue
        if (
            id_type == "email"
            and "email" in sent
            and changes(sent["email"], lambda v: email(v) == email(contact_id))
        ):
            return True
        if (
            id_type == "externalId"
            and "externalId" in sent
            and changes(sent["externalId"], lambda v: v == contact_id)
        ):
            return True
    return False


def not_found_is_done(method: str, operation: Optional[Operation]) -> bool:
    """Whether a 404 is success: after an attempt that may have reached the server,
    which may have done the delete.
    """
    return method == "DELETE" and operation is not None and operation.retry in ("done", "converges")


def with_entry_keys(body: Any, entries: Optional[str]) -> Any:
    """Gives each entry of the body's ``entries`` array without an idempotency key a new
    one, so a retried batch can't repeat an entry. Returns any other body as it is.
    """
    if entries is None or not isinstance(body, dict) or not isinstance(body.get(entries), list):
        return body
    return {
        **body,
        entries: [
            {**entry, "idempotencyKey": str(uuid.uuid4())}
            if isinstance(entry, dict) and entry.get("idempotencyKey") is None
            else entry
            for entry in body[entries]
        ],
    }


def should_retry(error: BaseException, safe: bool) -> bool:
    """Whether ``error`` is worth another attempt of a call that is or isn't ``safe`` to
    repeat.
    """
    # The API did nothing with the request, so even one unsafe to repeat can be sent again.
    if never_reached(error):
        return True
    if not safe:
        return False
    if isinstance(error, KiroraConnectionError):
        return True
    return isinstance(error, KiroraError) and error.is_retryable


def never_reached(error: BaseException) -> bool:
    """Whether ``error`` shows the API never acted on the request."""
    if isinstance(error, KiroraError):
        return error.status == 429
    # Set only for a connection that was never made, including one that timed out
    # connecting or waiting for a pooled connection: a timeout once sent may have run.
    return isinstance(error, KiroraConnectionError) and error._unsent


def may_have_run(error: BaseException) -> bool:
    """Whether the attempt that failed with ``error`` may have done its work. A 503
    without the API's request id came from a load balancer that didn't pass the request
    on.
    """
    if isinstance(error, KiroraError) and error.status == 503 and not error.request_id:
        return False
    return not never_reached(error)

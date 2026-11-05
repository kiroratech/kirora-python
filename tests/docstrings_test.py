"""The calls the SDK's docstrings show exist, so IDE help doesn't teach a stale API."""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Iterator, Tuple

import kirora

SRC = Path(kirora.__file__).parent
# A call such as ``kirora.Contacts.list(`` or ``Webhooks.verify(`` in a docstring.
CALL = re.compile(r"\b(kirora(?:\.[A-Za-z_]\w*)+|[A-Z]\w*\.[a-z_]\w*)\(")


def docstrings() -> Iterator[Tuple[str, str]]:
    for path in sorted(SRC.rglob("*.py")):
        if path.name in ("types.py", "_operations.py"):
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                text = ast.get_docstring(node)
                if text:
                    yield f"{path.relative_to(SRC)}:{getattr(node, 'lineno', 1)}", text


def resolve(dotted: str) -> object:
    parts = dotted.split(".")
    target: object = kirora if parts[0] == "kirora" else getattr(kirora, parts[0])
    for part in parts[1:]:
        target = getattr(target, part)
    return target


def test_every_call_a_docstring_shows_exists() -> None:
    missing = []
    checked = 0
    for where, text in docstrings():
        for call in CALL.findall(text):
            if call.split(".")[0] not in dir(kirora) and not call.startswith("kirora."):
                continue  # Not a name the SDK exports, such as ``Exception.__init__``.
            checked += 1
            try:
                resolve(call)
            except AttributeError:
                missing.append(f"{where}: {call}()")
    assert checked > 20
    assert missing == []


def test_docstring_examples_pass_filters_as_params_not_keywords() -> None:
    # Filters are a `params` dict, as ``list({"query": "ada"})``, not ``list(query="ada")``.
    stale = [
        f"{where}: {match}"
        for where, text in docstrings()
        for match in re.findall(r"\.list(?:_async)?\(\w+=[^)]*\)", text)
    ]
    assert stale == []

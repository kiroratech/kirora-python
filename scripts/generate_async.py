"""Writes each resource's ``_async`` methods from its sync ones. Needs ruff.

python scripts/generate_async.py
python scripts/generate_async.py --check
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path
from typing import List, Optional, Union

from codegen import PACKAGE, ROOT, fail, read, ruff_format, write

Function = Union[ast.FunctionDef, ast.AsyncFunctionDef]

AWAITED = {"_data": "_data_async", "_remove": "_remove_async"}
NOT_AWAITED = {"_page": "_page_async"}


def is_resource(node: ast.ClassDef) -> bool:
    return any(isinstance(base, ast.Name) and base.id == "APIResource" for base in node.bases)


def is_classmethod(node: Function) -> bool:
    return any(isinstance(d, ast.Name) and d.id == "classmethod" for d in node.decorator_list)


def start_line(node: Function) -> int:
    return min([node.lineno] + [d.lineno for d in node.decorator_list])


def returns_page(lines: List[str], node: Function) -> bool:
    return node.returns is not None and segment(lines, node.returns).startswith("Page[")


def segment(lines: List[str], node: ast.expr) -> str:
    assert node.end_lineno is not None and node.end_col_offset is not None
    if node.lineno == node.end_lineno:
        return lines[node.lineno - 1][node.col_offset : node.end_col_offset]
    parts = [lines[node.lineno - 1][node.col_offset :]]
    parts += lines[node.lineno : node.end_lineno - 1]
    parts.append(lines[node.end_lineno - 1][: node.end_col_offset])
    return "\n".join(parts)


def docstring_node(node: Function) -> Optional[ast.Constant]:
    first = node.body[0] if node.body else None
    if (
        isinstance(first, ast.Expr)
        and isinstance(first.value, ast.Constant)
        and isinstance(first.value.value, str)
    ):
        return first.value
    return None


def async_method(lines: List[str], cls: str, node: ast.FunctionDef) -> str:
    """The ``_async`` form of the sync method ``node``."""
    doc = docstring_node(node)
    if doc is None or doc.end_lineno is None or doc.end_col_offset is None:
        fail(f"{cls}.{node.name} needs a docstring, which its async form extends")
    first, last = start_line(node), node.end_lineno
    assert last is not None
    method = list(lines[first - 1 : last])
    row = doc.end_lineno - first
    close = doc.end_col_offset - 3
    indent = " " * doc.col_offset
    text = method[row]
    method[row] = f"{text[:close]}\n\n{indent}The async form of ``{cls}.{node.name}()``.{text[close:]}"
    source = "\n".join(method)
    page = returns_page(lines, node)
    definition = f"def {node.name}_async(" if page else f"async def {node.name}_async("
    source, count = re.subn(rf"\bdef {re.escape(node.name)}\(", definition, source, count=1)
    if count != 1:
        fail(f"couldn't find the definition of {cls}.{node.name}")
    if page:
        source = re.sub(r"->(\s*)Page\[", r"->\1AsyncPager[", source, count=1)
    for sync, name in AWAITED.items():
        source = source.replace(f"cls.{sync}(", f"await cls.{name}(")
    for sync, name in NOT_AWAITED.items():
        source = source.replace(f"cls.{sync}(", f"cls.{name}(")
    return source


def generate(path: Path) -> Optional[str]:
    """The module at ``path`` with its async methods rewritten, or None if it has none."""
    original = read(path)
    tree = ast.parse(original)
    lines = original.split("\n")
    classes = [node for node in tree.body if isinstance(node, ast.ClassDef) and is_resource(node)]
    if not classes:
        return None
    for cls in reversed(classes):
        methods = [
            node
            for node in cls.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and is_classmethod(node)
        ]
        sync = [
            node
            for node in methods
            if isinstance(node, ast.FunctionDef)
            and not node.name.startswith("_")
            and not node.name.endswith("_async")
        ]
        existing = [node for node in methods if node.name.endswith("_async")]
        if not sync:
            continue
        last_sync = max(node.end_lineno or 0 for node in sync)
        if any(start_line(node) < last_sync for node in existing):
            fail(f"{path.relative_to(ROOT)}: {cls.name}'s _async methods must follow its sync ones")
        after = [node for node in cls.body if node.lineno > last_sync]
        if any(node not in existing for node in after):
            fail(f"{path.relative_to(ROOT)}: {cls.name} has something other than _async methods after them")
        generated = "\n\n".join(async_method(lines, cls.name, node) for node in sync)
        assert cls.end_lineno is not None
        lines[last_sync : cls.end_lineno] = ["", generated]
    return ruff_format(path, "\n".join(lines))


def main() -> None:
    check = "--check" in sys.argv[1:]
    stale = []
    written = 0
    for path in sorted(PACKAGE.glob("*/_*.py")):
        content = generate(path)
        if content is None:
            continue
        if read(path) == content:
            continue
        if check:
            stale.append(path.relative_to(ROOT).as_posix())
        else:
            write(path, content)
            written += 1
    if stale:
        fail(
            f"Out of date with their sync methods: {', '.join(stale)}. "
            "Run `python scripts/generate_async.py`."
        )
    if check or not written:
        print("The async methods are up to date")
    else:
        print(f"Wrote the async methods of {written} resource{'' if written == 1 else 's'}")


if __name__ == "__main__":
    main()

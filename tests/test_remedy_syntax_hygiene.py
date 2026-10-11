"""Guard: user-facing messages never tell the author to type a syntax that does not exist (#700, #739).

An author edits a `.pflow.md` file (`- timeout: 60`, `- overwrite: true`), passes `--force` to the
CLI, or `force: true` to an MCP tool. Messages raised below those surfaces once spoke the code's
own dialect instead — a JSON key (`"timeout": 2`, `"inputs": {...}`) or a Python keyword argument
(`overwrite=True`, `force=True`) — and an agent pasting the advice got an invalid file. This scans
every string literal in ``src/pflow`` (docstrings and ``logger.*`` arguments excluded) for both
shapes. Write the fix in the reader's spelling instead: a backticked ``- param: value`` step line
(``binding_phrase()`` for a name bound through ``inputs:``/``env:``), and a service raises a typed
error with no remedy so each surface names its own switch.

Allow-list entries are literals that really are JSON or name a real Python argument; an entry that
no longer matches anything fails the test, so the list only shrinks.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

_SHAPES = {
    "a JSON key": re.compile(r'"[a-z_]+": ?'),
    "a Python keyword argument": re.compile(r"\b[a-z_]+=(?:True|False|true|false)\b"),
}

# (file under src/pflow, matched text) -> why the literal is legitimate.
_ALLOWED: dict[tuple[str, str], str] = {
    ("cli/commands/mcp.py", '"name": '): "MCP server config really is a JSON file",
    ("cli/commands/mcp.py", '"command": '): "MCP server config really is a JSON file",
    ("core/types.py", '"a": '): "an example JSON value of an input",
    **{
        (path, f'"{key}": '): "a JSON Schema example (output_schema is JSON Schema)"
        for path in ("core/workflow/validator.py", "nodes/agent/agent_node.py")
        for key in ("type", "properties", "required", "field", "result")
    },
    ("core/llm_client.py", "thinking=True"): "names the provider option a Python caller passed",
    ("nodes/agent/agent_node.py", "is_error=True"): "quotes the field the agent SDK reported",
    ("core/ir_schema.py", "parallel=true"): "a JSON Schema field description, not a remedy",
    ("nodes/file/delete_file.py", "confirm_delete=true"): (
        "a real member outside lane #700's ownership — reword to `- confirm_delete: true`, then drop this entry"
    ),
}


def _message_literals(tree: ast.AST) -> list[ast.Constant]:
    """String constants that can reach a reader: not docstrings, not logger arguments."""
    skipped: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            skipped.add(id(node.value))  # module/class/function/attribute docstrings
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id in {"logger", "logging"}
        ):
            skipped.update(id(child) for child in ast.walk(node))
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in skipped
    ]


def _hits(source: str) -> list[tuple[int, str, str]]:
    """``(line, matched text, shape)`` for each banned shape in a module's message literals."""
    return [
        (literal.lineno, match.group(0), shape)
        for literal in _message_literals(ast.parse(source))
        for shape, pattern in _SHAPES.items()
        for match in pattern.finditer(literal.value)
    ]


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("raise NodeError(f'Increase timeout: \"timeout\": {t}')", [(1, '"timeout": ', "a JSON key")]),
        ('msg = "Set overwrite=True to replace it."', [(1, "overwrite=True", "a Python keyword argument")]),
        ('msg = "Use force=true to overwrite."', [(1, "force=true", "a Python keyword argument")]),
        ("msg = '{\"timeout\":2}'", [(1, '"timeout":', "a JSON key")]),
        ('def f():\n    """Use force=True or "timeout": 2."""', []),
        ('logger.info(f"Deleted {name} (force=True)")', []),
        ('msg = "Set `- overwrite: true` on the step."', []),
    ],
)
def test_scanner_flags_message_literals_only(source: str, expected: list[tuple[int, str, str]]) -> None:
    """The guard sees f-string parts and plain literals, and skips docstrings and log calls."""
    assert _hits(source) == expected


def test_messages_name_the_syntax_the_reader_types() -> None:
    src_root = Path(__file__).resolve().parents[1] / "src" / "pflow"
    assert src_root.is_dir(), f"expected src/pflow/ at {src_root}"

    violations: list[str] = []
    used: set[tuple[str, str]] = set()
    for py_file in sorted(src_root.rglob("*.py")):
        rel = py_file.relative_to(src_root).as_posix()
        for line, text, shape in _hits(py_file.read_text(encoding="utf-8")):
            if (rel, text) in _ALLOWED:
                used.add((rel, text))
            else:
                violations.append(f"src/pflow/{rel}:{line}: {text!r} is {shape}")

    assert not violations, (
        "A message tells the reader to type syntax they never write. Use the `.pflow.md` step line "
        "(`- param: value`), the CLI flag, or the MCP argument instead — see this test's docstring:\n"
        + "\n".join(violations)
    )
    stale = sorted(set(_ALLOWED) - used)
    assert not stale, f"Allow-list entries that no longer match anything — delete them: {stale}"

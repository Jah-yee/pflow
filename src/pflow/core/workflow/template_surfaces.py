"""Every template-bearing location in a workflow IR, in one enumeration.

The validator's template checks (the Issue pass, reference extraction, the data-flow
root check) each walk ``iter_template_surfaces`` instead of their own copy of "where
templates live", so a new location (Task 100's ``batch.initial``) is one line here and
every check sees it.

How a param's text is read is decided here too, keyed on (node type, param): a code
body (``shell.command``, ``code.code`` — ``param_mode`` → ``"body"``) is never a
surface, embedded code (``"embedded"``) is a surface read through ``embedded_code``,
and every other param walk asks ``param_mode`` or iterates ``template_params``.
"""

from __future__ import annotations

import typing
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from pflow.core.templates import Template, embedded_code, parse

SurfaceKind = typing.Literal["param", "batch_items", "loop", "carry", "output_source", "cache_var", "cache_prose"]

ParamMode = typing.Literal["template", "body", "embedded"]
BodyLanguage = typing.Literal["sh", "python"]

# (node type, param) -> the language of a param that holds plain code — see ``param_mode``.
_BODIES: dict[tuple[str, str], BodyLanguage] = {("shell", "command"): "sh", ("code", "code"): "python"}
# (MCP tool, param) pairs whose param is JavaScript another process runs — see ``param_mode``.
# JavaScript only: a JSON insert is a JavaScript literal. Ordered: diagnostics list it as written.
EMBEDDED_CODE: tuple[tuple[str, str], ...] = (
    ("evaluate_script", "function"),
    ("browser_evaluate", "function"),
    ("navigate_page", "initScript"),
    ("browser_run_code_unsafe", "code"),
)


def param_mode(node_type: str | None, key: str) -> ParamMode:
    """How pflow reads one param's text:

    - ``"template"`` (the default) — ``${…}`` is a Template.
    - ``"body"`` — plain code in another language, never scanned, validated or resolved;
      values reach it through the node's own binding (ADR-0016).
    - ``"embedded"`` — JavaScript an MCP tool runs (``EMBEDDED_CODE``): sent as written,
      a bare ``${…}`` belonging to JavaScript; only a JSON insert ``${x|json}`` is pflow's
      (``templates.embedded_code``). Matched on the tool-name suffix of
      ``mcp-<server>-<tool>`` (the server name is the user's): a JavaScript tool missing
      from the table stays a Template, and a same-named tool of another server is read as
      embedded code, its in-scope bare names reported by the validator.
    """
    if (node_type, key) in _BODIES:
        return "body"
    if (
        node_type is not None
        and node_type.startswith("mcp-")
        and any(param == key and node_type.endswith(f"-{tool}") for tool, param in EMBEDDED_CODE)
    ):
        return "embedded"
    return "template"


def template_params(node: dict[str, Any]) -> dict[str, Any]:
    """A node's params minus its bodies — the params pflow reads as Templates."""
    params = node.get("params")
    if not isinstance(params, dict):
        return {}
    node_type = node.get("type")
    return {key: value for key, value in params.items() if param_mode(node_type, key) != "body"}


def code_bodies(node: dict[str, Any]) -> Iterator[tuple[str, BodyLanguage, str]]:
    """``(param, language, text)`` for each string body of a node (at most one today)."""
    params = node.get("params")
    node_type = node.get("type")
    for key, value in (params if isinstance(params, dict) else {}).items():
        language = _BODIES.get((node_type, key)) if isinstance(node_type, str) else None
        if language is not None and isinstance(value, str):
            yield key, language, value


@dataclass(frozen=True, slots=True)
class TemplateSurface:
    """One template-bearing IR location and its raw value."""

    kind: SurfaceKind
    node_id: str | None  # None for workflow-level surfaces (outputs, the cache block)
    # The author's name for the location: a param name, ``batch.items``, ``loop.while``,
    # ``loop.carry.<key>``, an output name, or a chunk name.
    key: str
    value: Any  # the raw IR value; dicts and lists nest
    mode: ParamMode = "template"  # a param's ``param_mode``; ``"embedded"`` reads the view

    def templates(self) -> Iterator[tuple[str, Template]]:
        """``(location, parsed text)`` for every string in the value.

        ``location`` extends ``key`` into nested values (``headers.Authorization``,
        ``batch.items[0].platform``). A cache var is stored bare in the IR (``p.x``),
        so it is parsed as the ``${p.x}`` the chunk came from. Embedded code yields its
        ``embedded_code`` view: only JSON inserts are Expressions, so no check sees
        JavaScript's own ``${…}``.
        """
        if self.kind == "cache_var":
            yield self.key, parse("${" + self.value + "}")
            return
        for location, text in _strings(self.key, self.value):
            template = parse(text)
            yield location, embedded_code(template) if self.mode == "embedded" else template

    def path(self, location: str) -> str:
        """The diagnostic path of ``location`` (``nodes[id=X].params.a.b``, ``outputs.o.source``)."""
        match self.kind:
            case "param":
                return f"nodes[id={self.node_id}].params.{location}"
            case "batch_items" | "loop" | "carry":
                return f"nodes[id={self.node_id}].{location}"
            case "output_source":
                return f"outputs.{location}.source"
            case "cache_var":
                return f"cache.items[name={location}].var"
            case "cache_prose":
                return f"cache.items[name={location}].prose_before"


def iter_template_surfaces(workflow_ir: dict[str, Any]) -> Iterator[TemplateSurface]:
    """Every template-bearing location, nodes first (IR order), then outputs, then the cache block."""
    for node in workflow_ir.get("nodes", []):
        yield from iter_node_surfaces(node)
    for name, output in (workflow_ir.get("outputs") or {}).items():
        if isinstance(output, dict) and isinstance(output.get("source"), str):
            yield TemplateSurface("output_source", None, name, output["source"])
    cache = workflow_ir.get("cache")
    items = cache.get("items") if isinstance(cache, dict) else None
    for item in items if isinstance(items, list) else ():
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            continue
        if isinstance(item.get("var"), str) and item["var"]:
            yield TemplateSurface("cache_var", None, item["name"], item["var"])
        if isinstance(item.get("prose_before"), str):
            yield TemplateSurface("cache_prose", None, item["name"], item["prose_before"])


def iter_node_surfaces(node: dict[str, Any]) -> Iterator[TemplateSurface]:
    """One node's surfaces: its params, ``batch.items``, loop fields, and carry values."""
    node_id = node.get("id")
    node_type = node.get("type")
    for key, value in template_params(node).items():
        yield TemplateSurface("param", node_id, key, value, param_mode(node_type, key))
    batch = node.get("batch")
    if isinstance(batch, dict) and batch.get("items") is not None:
        yield TemplateSurface("batch_items", node_id, "batch.items", batch["items"])
    loop = node.get("loop")
    if not isinstance(loop, dict):
        return
    for key in ("while", "until", "max_iterations"):
        if isinstance(loop.get(key), str):
            yield TemplateSurface("loop", node_id, f"loop.{key}", loop[key])
    carry = loop.get("carry")
    for key, value in (carry if isinstance(carry, dict) else {}).items():
        yield TemplateSurface("carry", node_id, f"loop.carry.{key}", value)


def _strings(location: str, value: Any) -> Iterator[tuple[str, str]]:
    if isinstance(value, str):
        if "${" in value:
            yield location, value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from _strings(f"{location}.{key}", item)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _strings(f"{location}[{index}]", item)

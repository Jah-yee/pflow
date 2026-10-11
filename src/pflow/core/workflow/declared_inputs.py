"""Declared inputs are never re-parsed (ADR-0017): the authoring errors that rule makes certain.

The resolver never JSON-parses a reference whose root is a declared non-``any`` input
(``templates._declared_typed``). So some reads are certain to miss — and a miss under ``??``,
in ``loop.while`` or a cache var is SILENT at run time (a fallback, a stopped loop, a dropped
chunk). ``declared_input_diagnostics`` reports them, and an input named like a batch alias (whose
declared type the resolver would apply to the item). It runs inside ``validate_data_flow``, so
the compiler enforces it too — a child chosen at run time (``workflow: ${…}``) is only compiled.

``declared_root_type`` is the one answer to "is this root the declared input here"; the
template validator's container rule (Passes 6 and 9) reads it as well.
"""

from __future__ import annotations

from collections.abc import Iterator
from itertools import chain, count
from typing import Any

from pflow.core.diagnostic import Diagnostic, Severity
from pflow.core.ir_schema import declared_input_types
from pflow.core.templates import Expression, Field, Reference, parse
from pflow.core.workflow.data_flow import step_scope
from pflow.core.workflow.template_surfaces import (
    WORKFLOW_NODE_TYPES,
    SurfaceKind,
    TemplateSurface,
    iter_template_surfaces,
)

_SCALAR_NOUNS = {"string": "a string", "integer": "a number", "number": "a number", "boolean": "a boolean"}


def declared_input_diagnostics(workflow_ir: dict[str, Any]) -> list[Diagnostic]:
    """Every certain miss on a declared input (``_declared_reads``) and every input named like a
    batch alias (``_inputs_named_like_batch_aliases``)."""
    return [*_inputs_named_like_batch_aliases(workflow_ir), *_declared_reads(workflow_ir)]


def declared_root_type(
    workflow_ir: dict[str, Any],
    node: dict[str, Any] | None,
    root: str,
    *,
    surface_kind: SurfaceKind,
    param_key: str | None = None,
) -> str | None:
    """The declared type of workflow input ``root`` where that input is CERTAINLY the active
    binding of ``root`` on this surface — ``None`` when it is not or may not be, or when it is
    ``any``/untyped.

    Bindings follow the runtime's merge points (``template_resolution._bind_locally``): a
    step's own ``inputs:`` values resolve before its keys are bound, so the workflow input owns
    the root there unless the batch alias holds it; every other param of the step reads its own
    ``inputs:`` key or alias first (``data_flow.step_scope``) — and after a whole-map
    ``inputs: ${…}``, whose keys are known only at run time, may read anything. ``batch.items``,
    loop fields and workflow-level surfaces resolve against the store itself.
    """
    declared = declared_input_types(workflow_ir).get(root, "any")
    if declared == "any":
        return None
    if node is None or surface_kind != "param":
        return declared
    if param_key == "inputs":
        owners: tuple[str, ...] = ("input", "inputs_key")
    elif isinstance((node.get("params") or {}).get("inputs"), str):
        return None
    else:
        owners = ("input",)
    return declared if step_scope(workflow_ir, node).kind(root, has_path=False) in owners else None


def _declared_reads(workflow_ir: dict[str, Any]) -> list[Diagnostic]:
    """An ERROR for every reference certain to miss because its root is a declared input: a path
    on a scalar, a field on an ``array``, an index on an ``object``; a ``batch.items`` whose
    declared root is not an ``array``, and a sub-workflow step's whole-map ``inputs:`` whose
    declared root is not an ``object``. Every operand counts, ``??`` ones included."""
    nodes = {node.get("id"): node for node in workflow_ir.get("nodes", []) if isinstance(node, dict)}
    diagnostics: list[Diagnostic] = []
    for surface, path, expression, ref in _surface_reads(workflow_ir):
        node = nodes.get(surface.node_id) if surface.node_id else None
        declared = declared_root_type(workflow_ir, node, ref.root, surface_kind=surface.kind, param_key=surface.key)
        if declared is None:
            continue
        if ref.path:
            diagnostic = _path_miss(ref, declared, surface.node_id, path, len(expression.operands) > 1)
        elif ref not in expression.operands or not isinstance(surface.value, str):
            diagnostic = None
        elif surface.kind == "batch_items":
            diagnostic = _whole_root(ref.root, declared, surface.node_id, path, "array", "`batch.items` needs a list")
        elif surface.key == "inputs" and node is not None and node.get("type") in WORKFLOW_NODE_TYPES:
            diagnostic = _whole_root(
                ref.root, declared, surface.node_id, path, "object", "A sub-workflow step's whole `inputs:` needs a map"
            )
        else:
            diagnostic = None
        if diagnostic is not None:
            diagnostics.append(diagnostic)
    return diagnostics


def _surface_reads(workflow_ir: dict[str, Any]) -> Iterator[tuple[TemplateSurface, str, Expression, Reference]]:
    """``(surface, diagnostic path, expression, reference)`` for every reference the runtime
    resolves: params, ``batch.items``, loop fields, a carry's index sources (its own reference
    is the carry check's), output sources as the runtime reads them, and cache vars."""
    from pflow.runtime.output_resolver import normalize_output_source  # runtime helper; lazy like data_flow

    for surface in iter_template_surfaces(workflow_ir):
        if surface.kind == "cache_prose":
            continue  # a reference there is the Issue pass's error
        if surface.kind == "output_source":
            templates = [(surface.key, parse(normalize_output_source(surface.value)))]
        else:
            templates = list(surface.templates())
        for location, template in templates:
            for expression in template.expressions:
                if expression.as_json and surface.mode != "embedded":
                    continue  # a misplaced `|json` insert is kept verbatim: the Issue pass's one error
                for operand in expression.operands:
                    if isinstance(operand, Reference):
                        refs = operand.index_sources if surface.kind == "carry" else operand.references
                        for ref in refs:
                            yield surface, surface.path(location), expression, ref


def _path_miss(ref: Reference, declared: str, node_id: str | None, path: str, in_coalesce: bool) -> Diagnostic | None:
    """The ERROR for a path the walk cannot take on a declared input's value, else ``None``
    (a field on an ``object`` and an index on an ``array`` may well resolve)."""
    root, written, by_field = ref.root, f"${{{ref.raw}}}", isinstance(ref.path[0], Field)
    if declared == "string":
        action = "read a field of it" if by_field else "index it"
        message = (
            f"Input '{root}' is declared `- type: string`, so `{written}` cannot {action} — "
            "a string input is never JSON-parsed."
        )
        shape = "object" if by_field else "array"
        fix = f"Declare `- type: {shape}` if '{root}' holds a JSON {shape}, or reference `${{{root}}}` whole."
    elif declared in _SCALAR_NOUNS:
        action = "read a field of" if by_field else "index"
        message = (
            f"Input '{root}' is declared `- type: {declared}`; `{written}` cannot {action} {_SCALAR_NOUNS[declared]}."
        )
        fix = f"Reference `${{{root}}}` whole."
    elif declared == "array" and by_field:
        message = (
            f"Input '{root}' is declared `- type: array`; `{written}` names a field, "
            f"but an array has only indexes (`${{{root}[0]}}`)."
        )
        fix = f"Index it first (`${{{root}[0]…}}`), or reference `${{{root}}}` whole."
    elif declared == "object" and not by_field:
        message = (
            f"Input '{root}' is declared `- type: object`; `{written}` indexes it, "
            f"but an object has only fields (`${{{root}.<field>}}`)."
        )
        fix = f"Read a field (`${{{root}.<field>}}`), or declare `- type: array` if '{root}' holds a list."
    else:
        return None
    if in_coalesce:
        message += " As a ?? operand the fallback would always win."
    return _error(node_id, path, message, fix, root, declared, written)


def _whole_root(root: str, declared: str, node_id: str | None, path: str, needed: str, needs: str) -> Diagnostic | None:
    """The ERROR for a whole declared root where the runtime needs a ``needed`` container and never
    parses text into one: ``batch.items: ${v}`` (a list) and a sub-workflow step's whole-map
    ``inputs: ${v}`` (a map — the host refuses anything else, ``_extract_child_inputs``)."""
    if declared == needed:
        return None
    parsed = " and is never JSON-parsed" if declared == "string" else ""
    message = f"{needs}; input '{root}' is declared `- type: {declared}`{parsed}."
    return _error(node_id, path, message, f"Declare `- type: {needed}` for '{root}'.", root, declared, f"${{{root}}}")


def _error(
    node_id: str | None, path: str, message: str, fix: str, root: str, declared: str, written: str
) -> Diagnostic:
    return Diagnostic(
        severity=Severity.ERROR,
        source="validator",
        title="Validation Error",
        node_id=node_id,
        message=message,
        suggestions=[fix],
        context={"category": "validation", "path": path, "input": root, "declared_type": declared, "template": written},
    )


def _inputs_named_like_batch_aliases(workflow_ir: dict[str, Any]) -> list[Diagnostic]:
    """One name, one owner: inside a batched step its alias (``batch.as``, default ``item``) IS
    the batch item, so a same-named input is unreachable there — and its declared type would be
    applied to the item (``templates.DECLARED_INPUT_TYPES_KEY`` is keyed by name)."""
    inputs = workflow_ir.get("inputs") or {}
    diagnostics: list[Diagnostic] = []
    for node in workflow_ir.get("nodes", []):
        batch = node.get("batch")
        if not isinstance(batch, dict):
            continue
        alias = batch.get("as") if isinstance(batch.get("as"), str) and batch.get("as") else "item"
        if alias not in inputs:
            continue
        candidates = chain(("entry", f"{alias}_item", f"{alias}_entry"), (f"{alias}_item{n}" for n in count(2)))
        rename = next(n for n in candidates if n not in inputs)
        step = node.get("id")
        diagnostics.append(
            Diagnostic(
                severity=Severity.ERROR,
                source="validator",
                title="Validation Error",
                message=(
                    f"Input '{alias}' has the same name as the batch alias of step '{step}' — inside "
                    f"that step `${{{alias}…}}` is the batch item, never the input."
                ),
                suggestions=[
                    f"Rename the input, or set `as: {rename}` under the step's `batch:` and update its item references."
                ],
                context={"category": "validation", "path": f"inputs.{alias}", "input": alias, "step": step},
            )
        )
    return diagnostics

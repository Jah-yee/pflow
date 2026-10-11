"""Declared inputs are never re-parsed (ADR-0017): the authoring errors that rule makes certain.

The resolver never JSON-parses a reference whose root is a declared non-``any`` input
(``templates._declared_typed``). So some reads are certain to miss — and a miss under ``??``,
in ``loop.while`` or a cache var is SILENT at run time (a fallback, a stopped loop, a dropped
chunk). ``declared_input_diagnostics`` reports them, and an input named like a batch alias (whose
declared type the resolver would apply to the item). It runs inside ``validate_data_flow``, so
the compiler enforces it too — a child chosen at run time (``workflow: ${…}``) is only compiled.

``declared_root`` is the one answer to "is this root the declared input here" — a name bound
to one by a single whole reference (a step ``inputs:`` key, a batch alias) included, as the
runtime binds it (``templates.bound_declaration``); the template validator's container rule
(Passes 6 and 9) reads it as well.
"""

from __future__ import annotations

from collections.abc import Iterator
from itertools import chain, count
from typing import Any

from pflow.core.diagnostic import Diagnostic, Severity
from pflow.core.ir_schema import declared_input_types
from pflow.core.templates import (
    PROTECTION_ONLY,
    Expression,
    Field,
    Reference,
    batch_item_declaration,
    bound_declaration,
    bound_reference,
    parse,
)
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


# What a name holds on a surface: its declared-input map entry and the input(s) its binding chain
# starts at — several when an inline batch list binds elements of different inputs of one type.
_Bound = tuple[str, tuple[str, ...]]


def declared_root(
    workflow_ir: dict[str, Any],
    node: dict[str, Any] | None,
    root: str,
    *,
    surface_kind: SurfaceKind,
    param_key: str | None = None,
) -> _Bound | None:
    """``(declared type, inputs)`` when ``root`` on this surface is CERTAINLY a declared input of
    that type, or a name bound to such inputs carrying their type — ``None`` when it is not or may
    not be, when the input is ``any``/untyped, or when the binding is protection-only (its type
    unknown). ``inputs`` names the declared input(s) behind the name (``(root,)`` for the input itself).

    Bindings follow the runtime's (``template_resolution._bind_locally``,
    ``batch_executor.bind_batch_item``): a batched step's alias is bound first; a step's own
    ``inputs:`` values resolve before its keys are bound, and every other param of the step then
    reads its own ``inputs:`` key first (a loop's carried key: its round-1 and carry bindings
    must agree) — after a whole-map ``inputs: ${…}``, whose keys are known only at run time, any
    root may be one. ``batch.items``, loop fields and workflow-level surfaces resolve against
    the store itself.
    """
    bound = _declared_scope(workflow_ir, node, surface_kind=surface_kind, param_key=param_key).get(root)
    return None if bound is None or bound[0] == PROTECTION_ONLY else bound


def _declared_scope(
    workflow_ir: dict[str, Any], node: dict[str, Any] | None, *, surface_kind: SurfaceKind, param_key: str | None
) -> dict[str, _Bound]:
    """Every name a declared input owns on this surface."""
    scope: dict[str, _Bound] = {
        name: (kind, (name,)) for name, kind in declared_input_types(workflow_ir).items() if kind != "any"
    }
    if node is None or surface_kind != "param":
        return scope
    batch = node.get("batch")
    if isinstance(batch, dict):
        raw_alias = batch.get("as")
        alias = raw_alias if isinstance(raw_alias, str) and raw_alias else "item"
        _bind(scope, {alias: _item_binding(batch.get("items"), scope)})
    if param_key == "inputs":
        return scope
    own_inputs = (node.get("params") or {}).get("inputs")
    if isinstance(own_inputs, str):
        return {}
    authored = own_inputs if isinstance(own_inputs, dict) else {}
    types = _types(scope)
    bound = {key: _inherit(scope, value, bound_declaration(value, types)) for key, value in authored.items()}
    loop = node.get("loop")
    carry = loop.get("carry") if isinstance(loop, dict) else None
    # From iteration 2 a carried key is bound to its carry template (`loop_control.apply_carry_overrides`):
    # what it inherits is certain only when every iteration's binding agrees.
    for key, value in (carry if isinstance(carry, dict) else {}).items():
        first = bound[key] if key in authored else scope.get(key)
        bound[key] = _agree([first, _inherit(scope, value, bound_declaration(value, types))])
    _bind(scope, bound)
    return scope


def _item_binding(items: Any, scope: dict[str, _Bound]) -> _Bound | None:
    """What the batch alias holds for EVERY item, statically: an inline list binds only when each
    element's entry is the same (``templates.batch_item_declaration``)."""
    types = _types(scope)
    if isinstance(items, str):
        return _inherit(scope, items.strip(), batch_item_declaration(items, 0, types))
    if not isinstance(items, list):
        return None
    return _agree([_inherit(scope, item, batch_item_declaration(items, i, types)) for i, item in enumerate(items)])


def _agree(bindings: list[_Bound | None]) -> _Bound | None:
    """The binding every case shares — one entry, the inputs of all — or ``None`` when one case is
    local or the entries differ (nothing about the name is certain)."""
    if not bindings or any(bound is None for bound in bindings):
        return None
    certain = [bound for bound in bindings if bound is not None]
    if len({entry for entry, _ in certain}) != 1:
        return None
    return certain[0][0], tuple(dict.fromkeys(name for _, inputs in certain for name in inputs))


def _inherit(scope: dict[str, _Bound], authored: Any, entry: str | None) -> _Bound | None:
    """``(entry, the input(s) the binding chain starts at)``; ``None`` for a local name."""
    ref = bound_reference(authored)
    return None if entry is None or ref is None else (entry, scope[ref.root][1])


def _types(scope: dict[str, _Bound]) -> dict[str, str]:
    return {name: entry for name, (entry, _) in scope.items()}


def _bind(scope: dict[str, _Bound], bindings: dict[str, _Bound | None]) -> None:
    for name, bound in bindings.items():
        if bound is None:
            scope.pop(name, None)
        else:
            scope[name] = bound


def _declared_reads(workflow_ir: dict[str, Any]) -> list[Diagnostic]:
    """An ERROR for every reference certain to miss because its root is a declared input: a path
    on a scalar, a field on an ``array``, an index on an ``object``; a ``batch.items`` whose
    declared root is not an ``array``, and a sub-workflow step's whole-map ``inputs:`` whose
    declared root is not an ``object``. Every operand counts, ``??`` ones included."""
    nodes = {node.get("id"): node for node in workflow_ir.get("nodes", []) if isinstance(node, dict)}
    diagnostics: list[Diagnostic] = []
    for surface, path, expression, ref in _surface_reads(workflow_ir):
        node = nodes.get(surface.node_id) if surface.node_id else None
        bound = declared_root(workflow_ir, node, ref.root, surface_kind=surface.kind, param_key=surface.key)
        for declared, input_name in [(bound[0], name) for name in bound[1]] if bound is not None else []:
            # One error per input behind the name: each is certain for the items that came from it.
            diagnostic = _declared_read(surface, node, path, expression, ref, (declared, input_name))
            if diagnostic is not None:
                diagnostics.append(diagnostic)
    return diagnostics


def _declared_read(
    surface: TemplateSurface,
    node: dict[str, Any] | None,
    path: str,
    expression: Expression,
    ref: Reference,
    bound: tuple[str, str],
) -> Diagnostic | None:
    """The certain miss of ``ref`` reading input ``bound`` = ``(declared type, input)``, if any."""
    if ref.path:
        return _path_miss(ref, bound, surface.node_id, path, len(expression.operands) > 1)
    if ref not in expression.operands or not isinstance(surface.value, str):
        return None
    if surface.kind == "batch_items":
        return _whole_root(ref.root, bound, surface.node_id, path, "array", "`batch.items` needs a list")
    if surface.key == "inputs" and node is not None and node.get("type") in WORKFLOW_NODE_TYPES:
        needs = "A sub-workflow step's whole `inputs:` needs a map"
        return _whole_root(ref.root, bound, surface.node_id, path, "object", needs)
    return None


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


def input_as(root: str, input_name: str) -> str:
    """``'v'`` — or ``'v' (as 'doc')`` when the template reads it through a name bound to it."""
    return f"'{input_name}'" if root == input_name else f"'{input_name}' (as '{root}')"


def _path_miss(
    ref: Reference, bound: tuple[str, str], node_id: str | None, path: str, in_coalesce: bool
) -> Diagnostic | None:
    """The ERROR for a path the walk cannot take on a declared input's value, else ``None``
    (a field on an ``object`` and an index on an ``array`` may well resolve)."""
    (declared, input_name), root = bound, ref.root
    written, by_field = f"${{{ref.raw}}}", isinstance(ref.path[0], Field)
    head = f"Input {input_as(root, input_name)} is declared `- type: {declared}`"
    if declared == "string":
        action = "read a field of it" if by_field else "index it"
        message = f"{head}, so `{written}` cannot {action} — a string input is never JSON-parsed."
        shape = "object" if by_field else "array"
        fix = f"Declare `- type: {shape}` if '{input_name}' holds a JSON {shape}, or reference `${{{root}}}` whole."
    elif declared in _SCALAR_NOUNS:
        action = "read a field of" if by_field else "index"
        message = f"{head}; `{written}` cannot {action} {_SCALAR_NOUNS[declared]}."
        fix = f"Reference `${{{root}}}` whole."
    elif declared == "array" and by_field:
        message = f"{head}; `{written}` names a field, but an array has only indexes (`${{{root}[0]}}`)."
        fix = f"Index it first (`${{{root}[0]…}}`), or reference `${{{root}}}` whole."
    elif declared == "object" and not by_field:
        message = f"{head}; `{written}` indexes it, but an object has only fields (`${{{root}.<field>}}`)."
        fix = f"Read a field (`${{{root}.<field>}}`), or declare `- type: array` if '{input_name}' holds a list."
    else:
        return None
    if in_coalesce:
        message += " As a ?? operand the fallback would always win."
    return _error(node_id, path, message, fix, input_name, declared, written)


def _whole_root(
    root: str, bound: tuple[str, str], node_id: str | None, path: str, needed: str, needs: str
) -> Diagnostic | None:
    """The ERROR for a whole declared root where the runtime needs a ``needed`` container and never
    parses text into one: ``batch.items: ${v}`` (a list) and a sub-workflow step's whole-map
    ``inputs: ${v}`` (a map — the host refuses anything else, ``_extract_child_inputs``)."""
    declared, input_name = bound
    if declared == needed:
        return None
    parsed = " and is never JSON-parsed" if declared == "string" else ""
    message = f"{needs}; input {input_as(root, input_name)} is declared `- type: {declared}`{parsed}."
    fix = f"Declare `- type: {needed}` for '{input_name}'."
    return _error(node_id, path, message, fix, input_name, declared, f"${{{root}}}")


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
    the batch item, so a same-named input is unreachable there."""
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

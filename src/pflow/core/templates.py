"""The ``${…}`` template language: one parse, one path walk, one resolution.

``parse(source)`` turns author text into an immutable ``Template`` of ``Text``,
``Expression`` and ``Issue`` segments. Every unescaped ``${`` is an Expression
or an Issue, never Text. ``resolve()`` walks a value against a context and
returns a ``Resolution``: the value plus what stayed literal. It is the single
judge of "unresolved" for every runtime consumer.

``parse`` is cached, so it runs on AUTHOR TEXT only. ``has_templates`` /
``has_references`` are uncached scans, the only helpers that may run on resolved
runtime values. Never decide unresolved-ness by re-scanning resolved text; read
the ``Resolution`` channels: resolved values may legitimately contain ``${`` text.

Lives in ``core/`` so the validator and the runtime share one module; it imports
only ``pflow.core`` (pinned by ``tests/test_core/test_templates_module.py``).
"""

from __future__ import annotations

import functools
import json
import logging
import re
import typing
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from typing import Any

from pflow.core.json_utils import try_parse_json
from pflow.core.types import outer_base_type

logger = logging.getLogger(__name__)


# ── Rules ────────────────────────────────────────────────────────────────────

CONTAINER_TYPES = frozenset({"dict", "object", "list", "array"})  # JSON auto-parse targets
LIST_TYPES = frozenset({"list", "array"})  # index access targets
TRAVERSABLE_TYPES = frozenset({"dict", "object", "any", "str", "string"})  # a path may walk into (str: JSON)
TRUSTED_TRAVERSABLE_TYPES = frozenset({"dict", "object", "any"})  # ...without a JSON-at-runtime warning


# Template-flow type compatibility: may a value of the declared SOURCE type flow
# through a template into a param of the TARGET type? It encodes auto-parse
# (str → dict) and stringification (int → str), so it is NOT a value-vs-declared-type
# check — a workflow input's value is typed by `param_coercion.coerce_declared_input`.
# source_type -> list of compatible target types
#
# BIDIRECTIONAL JSON compatibility for dict/list ↔ str:
#
#   Direction 1: str → dict/list (auto-parse feature)
#     Allows: ${shell.stdout} (type: str) → values (type: list) parameter
#     Runtime behavior (see runtime/engine/template_resolution.py):
#     - Simple templates (${var}) with JSON strings auto-parse to dict/list
#     - Complex templates ("text ${var}") stay as strings (escape hatch)
#     - Auto-parsing only happens when:
#       1. Template is simple (${var}, not "text ${var}")
#       2. String looks like JSON (starts with { or [)
#       3. String size ≤ 10MB (security limit)
#       4. Parsed type matches expected type
#     - Graceful fallback: invalid JSON stays as string, validation catches it
#
#   Direction 2: dict/list → str (auto-serialize feature)
#     Allows: ${node.results} (type: list) → prompt (type: str) parameter
#     Runtime behavior (see `to_string` below):
#     - Complex templates ("Data: ${var}") serialize dict/list to JSON
#     - Simple templates (${var} alone) preserve type (runtime check blocks)
#     - Enables embedding arrays/objects in prompts, shell env: values, etc.
#
#   This bidirectional compatibility enables shell+jq → MCP workflows.
TYPE_COMPATIBILITY_MATRIX = {
    "any": [
        "any",
        "str",
        "string",
        "int",
        "integer",
        "float",
        "number",
        "bool",
        "boolean",
        "dict",
        "object",
        "list",
        "array",
    ],  # any is universal
    "str": ["any", "str", "string", "dict", "object", "list", "array"],  # str can auto-parse to structured types
    "string": ["any", "str", "string", "dict", "object", "list", "array"],  # Alias for str
    "int": ["any", "int", "integer", "float", "number", "str", "string"],  # int can widen to float/number/str
    "integer": ["any", "int", "integer", "float", "number", "str", "string"],  # Alias for int
    "float": ["any", "float", "number", "str", "string"],  # float can stringify
    "number": ["any", "float", "number", "int", "integer", "str", "string"],  # number (generic numeric) → int/float/str
    "bool": ["any", "bool", "boolean", "str", "string"],  # bool can stringify
    "boolean": ["any", "bool", "boolean", "str", "string"],  # Alias for bool
    "dict": ["any", "dict", "object", "str", "string"],  # dict ↔ str bidirectional (parse/serialize JSON)
    "object": ["any", "dict", "object", "str", "string"],  # Alias for dict
    "list": ["any", "list", "array", "str", "string"],  # list ↔ str bidirectional (parse/serialize JSON)
    "array": ["any", "list", "array", "str", "string"],  # Alias for list
}


def is_type_compatible(source_type: str, target_type: str) -> bool:
    """Whether a ``source_type`` value may flow through a template into a ``target_type`` param.

    Args:
        source_type: Type of the value being provided
        target_type: Type expected by the parameter

    Returns:
        True if compatible, False otherwise

    Examples:
        >>> is_type_compatible("int", "float")
        True
        >>> is_type_compatible("str", "int")
        False
        >>> is_type_compatible("dict|str", "str")  # union: every member must match
        True
    """
    # Exact match
    if source_type == target_type:
        return True

    # Handle union types in source (ALL types must be compatible with target)
    if "|" in source_type:
        source_types = [t.strip() for t in source_type.split("|")]
        return all(is_type_compatible(st, target_type) for st in source_types)

    # Handle union types in target (source must be compatible with ANY target type)
    if "|" in target_type:
        target_types = [t.strip() for t in target_type.split("|")]
        return any(is_type_compatible(source_type, tt) for tt in target_types)

    # Strip parameterized generics to their outer collection type before the
    # matrix lookup. The producer side already canonicalizes (list[str] -> array),
    # but registry param types keep generics verbatim (list[str]); without this an
    # array source could never satisfy a list[str] param. Element types are not
    # compared — consistent with code-node outputs, which also collapse to the
    # bare collection type.
    source_base = outer_base_type(source_type)
    target_base = outer_base_type(target_type)
    # Identity short-circuit: covers unknown-but-equal bracketed types (e.g. a
    # user-named generic `foo[bar]` outside the canonical vocabulary). For
    # canonical names this is redundant — every matrix entry already lists itself.
    if source_base == target_base:
        return True
    return target_base in TYPE_COMPATIBILITY_MATRIX.get(source_base, [])


# ── Grammar (regex strings; the tokenizer and the public patterns share them) ──

_IDENT = r"[a-zA-Z_][\w-]*"
# Digits are ASCII `[0-9]`, never `\d`: Python's `\d` also matches other scripts'
# digits, which `json.loads` rejects (and `web/src/graph/scan.ts`'s JS `\d` does not match).
# A static reference path: `a`, `a.b`, `a[0].b[1]` — one index per segment. It is
# also the grammar of a dynamic index's inner reference (one level, no `??`).
_VAR_NAME_PATTERN = rf"{_IDENT}(?:(?:\[[0-9]+\])?(?:\.{_IDENT}(?:\[[0-9]+\])?)*)?"
# One path segment: a name with at most one index, `[N]` or `[${static ref}]`.
_SEGMENT = rf"{_IDENT}(?:\[(?:[0-9]+|\$\{{{_VAR_NAME_PATTERN}\}})\])?"
_PATH = rf"{_SEGMENT}(?:\.{_SEGMENT})*"

# Literal operand grammar: JSON values that `json.loads` accepts and the `??`
# splitter cannot shred — double-quoted strings with JSON escapes only (no raw
# control characters, no `??` inside), word-bounded true/false/null, numbers
# without leading zeros, and the empty `[]` / `{}`. Composite literals are out:
# complex defaults belong in a code node.
_LITERAL_PATTERN = (
    r'(?:"(?:[^"\\?\x00-\x1f]|\\["\\/bfnrt]|\\u[0-9a-fA-F]{4}|\?(?!\?))*"'
    r"|\btrue\b|\bfalse\b|\bnull\b|-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?|\[\]|\{\})"
)
# Literal first: keyword literals win over same-spelled identifiers.
_OPERAND = rf"(?:{_LITERAL_PATTERN}|{_PATH})"
_EXPRESSION = rf"{_OPERAND}(?:\s*\?\?\s*{_OPERAND})*"
# A JSON insert's suffix: `${x|json}`, `${a ?? "d" | json}` — one fixed word, on the whole
# expression, spaced like `??`. Not a general `|<name>` position: in embedded JavaScript
# `${flags|mask}` is JavaScript, so each word pflow claims is taken from that language.
_JSON_INSERT = r"\s*\|\s*json"

_EXPRESSION_AT = re.compile(rf"\$\{{({_EXPRESSION})({_JSON_INSERT})?\}}")
_LITERAL_FULL = re.compile(_LITERAL_PATTERN)
_PATH_FULL = re.compile(_PATH)
_SEGMENT_AT = re.compile(rf"({_IDENT})(?:\[(?:([0-9]+)|\$\{{({_VAR_NAME_PATTERN})\}})\])?")
_COALESCE_SPLIT = re.compile(r"\s*\?\?\s*")
# One left-to-right scan: an escape `$${…}` (brace-balanced body, one nesting
# level; without a balanced close only `$${` is consumed) or an unescaped `${`.
_SCAN = re.compile(r"(?P<escape>\$\$\{(?:[^{}]|\{[^{}]*\})*\}|\$\$\{)|(?<!\$)\$\{")


# ── AST (frozen, slotted, tuples never lists) ────────────────────────────────


@dataclass(frozen=True, slots=True)
class Text:
    text: str  # unescaped literal text (`$${` already `${`)


@dataclass(frozen=True, slots=True)
class Field:
    name: str


@dataclass(frozen=True, slots=True)
class Index:
    value: int


@dataclass(frozen=True, slots=True)
class DynamicIndex:
    ref: Reference  # a plain static Reference: no `??`, no nesting


Segment = Field | Index | DynamicIndex


@dataclass(frozen=True, slots=True)
class Reference:
    root: str
    path: tuple[Segment, ...]
    raw: str  # the operand's source text

    @property
    def references(self) -> tuple[Reference, ...]:
        """This reference, then its dynamic-index inner references."""
        return (self, *self.index_sources)

    @property
    def index_sources(self) -> tuple[Reference, ...]:
        """The inner references of this reference's dynamic indices (``i`` in ``a[${i}].x``)."""
        return tuple(seg.ref for seg in self.path if isinstance(seg, DynamicIndex))

    def first_field(self) -> tuple[int, str] | None:
        """``(offset in raw of the "." before it, name)`` of the first field after the
        root — past a root index (``a[${i.j}].x`` → ``(9, "x")``); ``None`` if none.

        By the path grammar that field follows the first ``.`` outside brackets."""
        name = next((seg.name for seg in self.path if isinstance(seg, Field)), None)
        depth = 0
        for offset, char in enumerate(self.raw):
            depth += (char == "[") - (char == "]")
            if char == "." and depth == 0 and name is not None:
                return offset, name
        return None


@dataclass(frozen=True, slots=True)
class Literal:
    raw: str  # a JSON literal per the literal grammar

    @property
    def value(self) -> Any:
        # Computed fresh on every access: a cached `[]` / `{}` would be shared
        # across resolutions (and batch threads) through the parse cache.
        return json.loads(self.raw)


Operand = Reference | Literal


@dataclass(frozen=True, slots=True)
class Expression:
    operands: tuple[Operand, ...]  # more than one ⇔ coalesce
    raw: str  # the text inside `${…}`, a `|json` suffix included
    span: tuple[int, int]  # [start of `${`, end after `}`)
    # A JSON insert (`${x|json}`): its value enters text as a JSON literal (`to_json`); never
    # simple. Accepted only in embedded code (`embedded_code`); elsewhere resolution keeps it
    # as written, in the issues channel.
    as_json: bool = False

    @property
    def references(self) -> tuple[Reference, ...]:
        """Every Reference, dynamic-index inner ones included: the DEPENDENCY view."""
        return tuple(ref for op in self.operands if isinstance(op, Reference) for ref in op.references)

    @property
    def bare_raw(self) -> str:
        """``raw`` without a ``|json`` suffix: the text of ``${…}`` read as a plain Template."""
        return self.raw[: self.raw.rindex("|")].rstrip() if self.as_json else self.raw


IssueKind = typing.Literal["malformed", "bad_literal"]


@dataclass(frozen=True, slots=True)
class Issue:
    """An unescaped ``${`` that opens no Expression, through its first ``}`` (or EOS)."""

    raw: str
    span: tuple[int, int]
    kind: IssueKind


@dataclass(frozen=True, slots=True)
class Template:
    source: str
    segments: tuple[Text | Expression | Issue, ...]
    escaped: bool  # a `$${` escape was consumed

    @property
    def expressions(self) -> tuple[Expression, ...]:
        return tuple(seg for seg in self.segments if isinstance(seg, Expression))

    @property
    def issues(self) -> tuple[Issue, ...]:
        return tuple(seg for seg in self.segments if isinstance(seg, Issue))

    @property
    def references(self) -> tuple[Reference, ...]:
        return tuple(ref for expr in self.expressions for ref in expr.references)

    @property
    def is_simple(self) -> bool:
        """The whole source is one Expression, not a JSON insert: resolution preserves its value's type.

        One trailing newline is tolerated (and dropped by resolution): a YAML block
        scalar ``v: |`` ends in ``\n``, and ``${x}\n`` has always been simple.
        """
        first = self.segments[0] if self.segments else None
        if not isinstance(first, Expression) or first.as_json:
            return False
        return self.segments[1:] in ((), (Text("\n"),))

    @property
    def needs_resolution(self) -> bool:
        return self.escaped or any(isinstance(seg, Expression) for seg in self.segments)


# ── Parse ────────────────────────────────────────────────────────────────────


@functools.lru_cache(maxsize=4096)
def parse(source: str) -> Template:
    """Parse author template text. Pure, total (never raises), context-free."""
    return _tokenize(source)


def parse_path(path: str) -> Reference | None:
    """The bare path grammar (``node.f[0].g``, ``a[${i}].x``); ``None`` if invalid."""
    if not _PATH_FULL.fullmatch(path):
        return None
    segments: list[Segment] = []
    pos = 0
    while pos < len(path):
        match = _SEGMENT_AT.match(path, pos)
        if match is None:  # pragma: no cover — unreachable after the fullmatch
            return None
        name, index, inner = match.groups()
        segments.append(Field(name))
        if index is not None:
            try:
                segments.append(Index(int(index)))
            except ValueError:  # past Python's int-string conversion limit
                return None
        elif inner is not None:
            inner_ref = parse_path(inner)
            if inner_ref is None:  # pragma: no cover — the inner grammar is a subset
                return None
            segments.append(DynamicIndex(inner_ref))
        pos = match.end() + 1  # skip the `.` separator
    root = segments[0]
    assert isinstance(root, Field)  # noqa: S101 — the path grammar starts with a name
    return Reference(root.name, tuple(segments[1:]), path)


def _tokenize(source: str) -> Template:
    segments: list[Text | Expression | Issue] = []
    text: list[str] = []
    escaped = False
    pos = 0
    while (match := _SCAN.search(source, pos)) is not None:
        start = match.start()
        text.append(source[pos:start])
        if match.group("escape"):
            text.append(match.group(0)[1:])
            escaped = True
            pos = match.end()
            continue
        if text_so_far := "".join(text):
            segments.append(Text(text_so_far))
        text = []
        token = _expression_at(source, start) or _issue_at(source, start)
        segments.append(token)
        pos = token.span[1]
    text.append(source[pos:])
    if tail := "".join(text):
        segments.append(Text(tail))
    return Template(source, tuple(segments), escaped)


def _expression_at(source: str, start: int) -> Expression | None:
    match = _EXPRESSION_AT.match(source, start)
    if match is None:
        return None
    operands: list[Operand] = []
    for operand in _COALESCE_SPLIT.split(match.group(1)):
        # The decode check rejects the one grammar match `json.loads` cannot take:
        # an integer past Python's int-string limit (`Literal.value` never raises).
        if _LITERAL_FULL.fullmatch(operand) and try_parse_json(operand)[0]:
            operands.append(Literal(operand))
        elif (ref := parse_path(operand)) is not None:
            operands.append(ref)
        else:  # an oversized number or index: an Issue, like any other bad expression
            return None
    suffix = match.group(2)
    return Expression(tuple(operands), match.group(1) + (suffix or ""), match.span(), as_json=suffix is not None)


def _issue_at(source: str, start: int) -> Issue:
    close = source.find("}", start)
    end = len(source) if close == -1 else close + 1
    raw = source[start:end]
    inner = raw[2:-1] if raw.endswith("}") else raw[2:]
    bad_literal = "??" in inner and any(
        _looks_like_literal(op) and not _LITERAL_FULL.fullmatch(op) for op in _COALESCE_SPLIT.split(inner.strip())
    )
    return Issue(raw, (start, end), "bad_literal" if bad_literal else "malformed")


def _looks_like_literal(operand: str) -> bool:
    """A coarse first-char check: ``{ [ " -`` or a digit, or exactly true/false/null."""
    return bool(operand) and (operand[0] in '{["-0123456789' or operand in ("true", "false", "null"))


# ── Embedded code: a policy view over the one parse ──────────────────────────


def embedded_code(template: Template) -> Template:
    """How embedded code reads a parse: only the JSON inserts (``${…|json}``) are pflow's.

    Every other span — a bare ``${…}``, an Issue, a ``$${`` — is Text cut verbatim from
    the source (an escape is not collapsed). A policy view, not a parse: its Text may
    hold ``${``. Which params are embedded code: ``workflow/template_surfaces.param_mode``.
    """
    segments: list[Text | Expression | Issue] = []
    pos = 0
    for insert in (expr for expr in template.expressions if expr.as_json):
        start, end = insert.span
        if start > pos:
            segments.append(Text(template.source[pos:start]))
        segments.append(insert)
        pos = end
    if pos < len(template.source):
        segments.append(Text(template.source[pos:]))
    return Template(template.source, tuple(segments), escaped=False)


def hidden_inserts(template: Template) -> tuple[tuple[int, int], ...]:
    """Spans of ``${…|json}`` in the source that the parse did not produce as Expressions —
    inserts swallowed by a ``$${…}`` escape, an Issue (``${${x|json} + 1}``) or another
    Expression's literal (``${"${x|json}"}``). Every ``${`` is tried, so matches may nest."""
    visible = {expr.span[0] for expr in template.expressions}
    spans: list[tuple[int, int]] = []
    start = template.source.find("${")
    while start != -1:
        match = _EXPRESSION_AT.match(template.source, start)
        if match is not None and match.group(2) is not None and start not in visible:
            spans.append(match.span())
        start = template.source.find("${", start + 1)
    return tuple(spans)


_BRACE_OR_STRING = re.compile(r'"(?:[^"\\]|\\.)*"|[{}]')


def balanced_template(source: str, start: int) -> str:
    """The ``${…}`` opening at ``start`` through its brace-balanced ``}`` (to the end if
    unclosed) — wider than an Issue, which ends at its first ``}``. A brace inside a
    ``"…"`` string does not count (``${"}"|JSON}``)."""
    depth = 0
    for match in _BRACE_OR_STRING.finditer(source, start + 1):
        brace = match.group()  # or a whole string, skipped
        if brace == "{":
            depth += 1
        elif brace == "}":
            depth -= 1
            if depth == 0:
                return source[start : match.end()]
    return source[start:]


def near_miss_insert(source: str, issue: Issue) -> tuple[str, str] | None:
    """``(as written, meant)`` when an Issue was probably meant as a JSON insert
    (``${x|json }``, ``${ x|json}``, ``${x|JSON}``, ``${{}|JSON}`` → ``${…|json}``): the
    brace-balanced text from its ``${``, ends trimmed and the word after the last ``|``
    lower-cased, if that parses as one; else ``None``."""
    written = balanced_template(source, issue.span[0])
    if not written.endswith("}"):
        return None
    head, bar, word = written[2:-1].strip().rpartition("|")
    if not bar:
        return None
    meant = f"${{{head.rstrip()}|{word.strip().lower()}}}"
    expression = _expression_at(meant, 0)
    if expression is None or not expression.as_json or expression.span[1] != len(meant):
        return None
    return written, meant


# ── Walk ─────────────────────────────────────────────────────────────────────

_MISS: tuple[bool, Any] = (False, None)

# The running workflow's declared ``## Inputs`` types (``{name: canonical type}``), carried in
# the shared store beside ``__pflow_prompt_cache__`` and installed by the same owners (the
# engine per workflow, the dry-run planner, the runner's root store). A reference whose root
# is a declared non-``any`` input is never JSON-parsed — at the leaf or mid-path (ADR-0017).
DECLARED_INPUT_TYPES_KEY = "__pflow_input_types__"


def _declared_typed(context: Mapping[str, Any], root: str) -> bool:
    """Whether ``root`` is a declared non-``any`` input of the workflow ``context`` belongs to."""
    types: Mapping[str, str] = context.get(DECLARED_INPUT_TYPES_KEY) or {}
    return types.get(root, "any") != "any"


def _json_container(value: Any) -> Any:
    """A JSON-object/array string parsed for traversal; anything else unchanged.

    Primitives are NOT parsed, so numeric strings like Discord snowflake IDs
    ("1458059302022549698") stay strings.
    """
    if not isinstance(value, str):
        return value
    success, parsed = try_parse_json(value)
    if success and isinstance(parsed, (dict, list)):
        logger.debug(f"Auto-parsed JSON string for path traversal: {type(parsed).__name__}")
        return parsed
    return value


def lookup(ref: Reference, context: Mapping[str, Any]) -> tuple[bool, Any]:
    """Walk ``ref`` through ``context``: ``(found, value)``; see ``_walk``."""
    return _walk(ref.root, ref.path, context)


def _walk(root: str, path: Iterable[Segment], context: Mapping[str, Any]) -> tuple[bool, Any]:
    """The one path walk.

    Found means the walk reached a value — possibly ``None`` (a found ``None`` is
    not "missing"). A name reads a Mapping (``NamespacedSharedStore`` and
    ``MappingProxyType`` included); an index needs a list and ``0 <= N < len``; a
    JSON-container string is parsed before either — unless the root is a declared
    input (``_declared_typed``). A dynamic index must resolve to an ``int``
    (``bool`` excluded). Anything else — including walking on through ``None`` —
    is a miss.
    """
    if root not in context:
        return _MISS
    current = context[root]
    parse_text = not _declared_typed(context, root)
    for segment in path:
        found, current = _step(current, segment, context, parse_text=parse_text)
        if not found:
            return _MISS
    return True, current


def _step(current: Any, segment: Segment, context: Mapping[str, Any], *, parse_text: bool) -> tuple[bool, Any]:
    """One segment of the walk from ``current``."""
    if parse_text:
        current = _json_container(current)
    match segment:
        case Field(name):
            return (True, current[name]) if isinstance(current, Mapping) and name in current else _MISS
        case Index(value):
            index: int | None = value
        case DynamicIndex(inner):
            index = _dynamic_index(inner, context)
    if index is None or not isinstance(current, list) or not 0 <= index < len(current):
        return _MISS
    return True, current[index]


def unparsed_declared_text(ref: Reference, context: Mapping[str, Any]) -> tuple[str, str] | None:
    """Why a reference rooted in a declared input missed, when the reason is its rule.

    ``(path, text)`` of the JSON-container TEXT the walk stopped at (``("data.payload",
    '{"a":1}')`` for ``${data.payload.a}``) — text a declared input never re-parses.
    ``None`` when the root is not a declared input or the miss has another cause.
    """
    if ref.root not in context or not _declared_typed(context, ref.root):
        return None
    current, shown = context[ref.root], ref.root
    for segment in ref.path:
        found, following = _step(current, segment, context, parse_text=False)
        if not found:
            return (shown, current) if isinstance(current, str) and _json_container(current) is not current else None
        current = following
        match segment:
            case Field(name):
                shown += f".{name}"
            case Index(value):
                shown += f"[{value}]"
            case DynamicIndex(inner):
                shown += f"[${{{inner.raw}}}]"
    return None


def declared_text_misses(resolution: Resolution, context: Mapping[str, Any]) -> list[tuple[str, str, str]]:
    """``(reference, text path, text)`` for every operand of ``resolution``'s unresolved
    expressions that stopped at a declared input's JSON text (``unparsed_declared_text``).
    A consumer that treats "unresolved" as "absent" reads this first: such a miss is never
    an absent value, always an author error."""
    misses: list[tuple[str, str, str]] = []
    for raw in sorted(resolution.unresolved):
        for expression in parse("${" + raw + "}").expressions:
            for operand in expression.operands:
                if isinstance(operand, Reference) and (hit := unparsed_declared_text(operand, context)):
                    misses.append((operand.raw, *hit))
    return misses


def _dynamic_index(inner: Reference, context: Mapping[str, Any]) -> int | None:
    found, value = lookup(inner, context)
    if not found:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        # Kept loud: under `??` a bad index would otherwise fall through invisibly.
        logger.warning(
            f"Nested index must be integer, got {type(value).__name__}",
            extra={"template": inner.raw, "inner_value": value},
        )
        return None
    return int(value)


def _evaluate(expression: Expression, context: Mapping[str, Any]) -> tuple[bool, Any, Operand | None]:
    """The first operand that resolves: ``(found, value, that operand)``. A Literal
    always resolves; a Reference iff found.

    ``??`` falls through whenever the left side "isn't there" — the node did not
    run OR the field is missing (like ``??`` in JS/C#). A found ``None`` ends
    the chain. (Declared outputs use a stricter all-absent rule in
    ``output_resolver._is_all_absent_coalesce``.)
    """
    for operand in expression.operands:
        if isinstance(operand, Literal):
            return True, operand.value, operand
        found, value = lookup(operand, context)
        if found:
            return True, value, operand
    return False, None, None


# Raw-path lexer for USER-TYPED paths (`-o result.@type`, `read-fields result.dc:title`):
# split on dots outside brackets, then peel a trailing `[N][M]…` chain off each part.
# No identifier grammar — the path walks as written.
_RAW_DOT_SPLIT = re.compile(r"\.(?![^\[]*\])")
_RAW_INDEXED_PART = re.compile(r"^([^[]+)((?:\[\d+\])+)$")


def _split_raw_path(path: str) -> tuple[str, tuple[Segment, ...]]:
    """``"a.b[1][2].c"`` → ``("a", (Field("b"), Index(1), Index(2), Field("c")))``."""
    segments: list[Segment] = []
    for part in _RAW_DOT_SPLIT.split(path):
        match = _RAW_INDEXED_PART.match(part)
        if match:
            segments.append(Field(match.group(1)))
            segments.extend(Index(int(i)) for i in re.findall(r"\d+", match.group(2)))
        else:
            segments.append(Field(part))
    root = segments[0]
    assert isinstance(root, Field)  # noqa: S101 — every raw part starts with a key
    return root.name, tuple(segments[1:])


# ── Resolution ───────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class Resolution:
    """A resolved value plus what resolution had to leave literal.

    ``unresolved`` holds ``Expression.raw`` of every expression left literal;
    ``issues`` holds ``Issue.raw`` of every Issue routed through resolution, and the
    source text of every JSON insert outside embedded code (both kept verbatim). Both
    span the whole value. Text that came FROM a resolved value is
    never in either — only the author's template is judged. The channels
    stay distinct so a surface can tolerate Issues without tolerating misses (the
    deferred #621 tolerance ruling).
    """

    value: Any
    unresolved: frozenset[str] = frozenset()
    issues: frozenset[str] = frozenset()

    @property
    def ok(self) -> bool:
        return not self.unresolved and not self.issues

    @staticmethod
    def combine(value: Any, parts: Iterable[Resolution]) -> Resolution:
        """``value`` carrying the union of ``parts``' channels (a container's resolution)."""
        parts = tuple(parts)
        return Resolution(
            value,
            unresolved=frozenset().union(*(p.unresolved for p in parts)),
            issues=frozenset().union(*(p.issues for p in parts)),
        )


def resolve(value: Any, context: Mapping[str, Any], *, auto_parse: bool = False, embedded: bool = False) -> Resolution:
    """Resolve every template in ``value`` against ``context``.

    A string: a simple template yields its value, type preserved; otherwise one
    left-to-right pass — Text as written (unescaped), each Expression stringified
    or left as its raw ``${…}``, each Issue verbatim; substituted values are never
    re-scanned. No top-level JSON auto-parse. Dicts and lists recurse, keys
    untouched. ``auto_parse=True`` adds ``resolve_nested``'s leaf rule at every
    string leaf, the top-level one included: a simple template's resolved
    JSON-container string is parsed. ``embedded=True`` reads every string leaf as
    embedded code (``embedded_code``): only its JSON inserts are filled in. Other
    values pass through unchanged.
    """
    if isinstance(value, str):
        if "${" not in value:
            return Resolution(value)
        template = parse(value)
        return _resolve_string(embedded_code(template) if embedded else template, context, auto_parse, embedded)
    if isinstance(value, dict):
        entries = {key: resolve(item, context, auto_parse=auto_parse, embedded=embedded) for key, item in value.items()}
        return Resolution.combine({key: r.value for key, r in entries.items()}, entries.values())
    if isinstance(value, list):
        items = [resolve(item, context, auto_parse=auto_parse, embedded=embedded) for item in value]
        return Resolution.combine([r.value for r in items], items)
    return Resolution(value)


def _resolve_simple(template: Template, context: Mapping[str, Any], auto_parse: bool) -> Resolution:
    expression = template.expressions[0]
    found, value, operand = _evaluate(expression, context)
    if not found:
        logger.debug(f"Template '{template.source}' could not be resolved", extra={"var_name": expression.raw})
        return Resolution(template.source, unresolved=frozenset({expression.raw}))
    # resolve_nested's leaf rule; numeric strings stay strings (Discord snowflake IDs), and a
    # declared input's text is never re-parsed — judged by the operand that supplied the value.
    declared = isinstance(operand, Reference) and _declared_typed(context, operand.root)
    if auto_parse and isinstance(value, str) and not declared:
        success, parsed = try_parse_json(value)
        if success and isinstance(parsed, (dict, list)):
            return Resolution(parsed)
    return Resolution(value)


def _resolve_string(template: Template, context: Mapping[str, Any], auto_parse: bool, embedded: bool) -> Resolution:
    if template.is_simple:
        return _resolve_simple(template, context, auto_parse)

    parts: list[str] = []
    unresolved: set[str] = set()
    issues = {issue.raw for issue in template.issues}
    for segment in template.segments:
        match segment:
            case Text(text):
                parts.append(text)
            case Issue(raw):
                parts.append(raw)
            case Expression():
                written = template.source[segment.span[0] : segment.span[1]]
                if segment.as_json and not embedded:  # a JSON insert outside embedded code
                    issues.add(written)
                    parts.append(written)
                    continue
                found, value, _ = _evaluate(segment, context)
                if found:
                    parts.append(to_json(value) if segment.as_json else to_string(value))
                else:
                    unresolved.add(segment.raw)
                    _log_unresolved_inline(segment.raw)
                    parts.append(written)
    return Resolution("".join(parts), unresolved=frozenset(unresolved), issues=frozenset(issues))


def to_string(value: Any) -> str:
    """Stringify for complex interpolation.

    ``None``/``""`` → ``""``; ``False``/``True`` → ``"False"``/``"True"``;
    ``0`` → ``"0"``; ``[]``/``{}`` → ``"[]"``/``"{}"``; dict/list → JSON (not
    Python repr); everything else → ``str(value)``.
    """
    if value is None or value == "":
        return ""
    # Check for boolean BEFORE checking for 0 (since False == 0 in Python)
    elif value is False:
        return "False"
    elif value is True:
        return "True"
    elif value == 0:
        return "0"
    elif value == []:
        return "[]"
    elif value == {}:
        return "{}"
    elif isinstance(value, (dict, list)):
        try:
            return json.dumps(value, ensure_ascii=False)
        except (TypeError, ValueError):
            return str(value)
    else:
        return str(value)


def to_json(value: Any) -> str:
    """A JSON insert's text: the value as a JSON literal (``true``, ``null``, ``"Don't"``,
    ``{"a": [1, 2]}``) — non-ASCII kept as written. A value JSON cannot encode (a set,
    bytes) enters as the JSON string of its ``to_string`` text. Text is never re-parsed:
    a string holding JSON stays a string."""
    try:
        return json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError):
        return json.dumps(to_string(value), ensure_ascii=False)


def _log_unresolved_inline(var_expr: str) -> None:
    if ".response." in var_expr:
        logger.warning(
            f"Template variable '${{{var_expr}}}' could not be resolved. "
            f"This often indicates the LLM node didn't generate the expected JSON structure. "
            f"Check that the LLM response contains the field '{var_expr.split('.')[-1]}'"
        )
    else:
        logger.debug(f"Template variable '${{{var_expr}}}' could not be resolved", extra={"var_name": var_expr})


def _strings(value: Any) -> Iterator[str]:
    """Every string in ``value``, recursing into dicts (values) and lists."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)


# ── The string-helper facade (the permanent interface of the long tail) ──────


class TemplateResolver:
    """String-in/string-out helpers over ``parse`` / ``resolve`` / the walk."""

    # Static-discovery views built from the tokenizer's grammar (dynamic index
    # included). They cannot see escape CONSUMPTION (`$${a[${i}]}` still shows
    # `${i}`), so discovery over text that may hold escapes uses ``parse()``.
    TEMPLATE_PATTERN = re.compile(rf"(?<!\$)\$\{{({_EXPRESSION})(?:{_JSON_INSERT})?\}}")
    SIMPLE_TEMPLATE_PATTERN = re.compile(rf"^\$\{{({_EXPRESSION})\}}$")

    _COALESCE_SPLIT_PATTERN = _COALESCE_SPLIT
    # Root variable name: everything before the first `.` or `[`.
    _ROOT_SPLIT_PATTERN = re.compile(r"[\.\[]")

    @staticmethod
    def has_templates(value: Any, *, embedded: bool = False) -> bool:
        """Whether resolution rewrites ``value``: an Expression or a ``$${`` escape
        anywhere (an escape-only value still resolves to its literal ``${…}``;
        an Issue-only value is static). In embedded code only a JSON insert counts.
        Uncached — safe on resolved values."""
        return any(
            "${" in s and (embedded_code(_tokenize(s)) if embedded else _tokenize(s)).needs_resolution
            for s in _strings(value)
        )

    @staticmethod
    def has_references(value: Any) -> bool:
        """Whether ``value`` holds an Expression anywhere (escape-only → False).
        Uncached — safe on resolved values."""
        return any("${" in s and bool(_tokenize(s).expressions) for s in _strings(value))

    @staticmethod
    def extract_variables(value: str) -> set[str]:
        """The value-position References of every Expression, by source text.

        ``${a ?? b}`` → ``{"a", "b"}``; literal operands are values, not
        dependencies; ``${a[${i}].x}`` → ``{"a[${i}].x"}`` (the inner ``i`` is an
        index key, not a value — see ``Expression.references`` for dependencies).
        """
        return {op.raw for expr in parse(value).expressions for op in expr.operands if isinstance(op, Reference)}

    @staticmethod
    def is_simple_template(value: str) -> bool:
        """Whether the whole string is one Expression (its value's type is preserved).

        Examples:
            >>> TemplateResolver.is_simple_template("${data.field}")
            True
            >>> TemplateResolver.is_simple_template("Hello ${name}")
            False
        """
        return parse(value).is_simple

    @staticmethod
    def split_coalesce_operands(expr: str) -> list[str]:
        """Split an expression on ``??`` (lexical); one element when there is none."""
        if "??" not in expr:
            return [expr]
        return [op.strip() for op in TemplateResolver._COALESCE_SPLIT_PATTERN.split(expr)]

    @staticmethod
    def is_literal_operand(operand: str) -> bool:
        """Whether an operand LOOKS like a JSON literal (a coarse first-char check).

        Literals start with one of ``{ [ " -`` or a digit, or are exactly
        ``true`` / ``false`` / ``null``; identifiers start with ``[a-zA-Z_]``. It is
        BROADER than the literal grammar (``01``, ``[1,2]`` pass): it classifies an
        operand the grammar already accepted, it does not validate literal shape.

        Examples:
            >>> TemplateResolver.is_literal_operand('"hello"')
            True
            >>> TemplateResolver.is_literal_operand("truthy_value")
            False
        """
        return _looks_like_literal(operand)

    @staticmethod
    def is_coalesce_expression(expr: str) -> bool:
        """Check if a template expression contains the coalesce operator ??."""
        return "??" in expr

    @staticmethod
    def extract_root_node_id(template_path: str) -> str:
        """The root of a path (lexical): ``"node.field[0].sub"`` → ``"node"``, ``"data[0]"`` → ``"data"``."""
        return TemplateResolver._ROOT_SPLIT_PATTERN.split(template_path, maxsplit=1)[0]

    @staticmethod
    def extract_first_field_segment(var: str) -> str | None:
        """The first field segment after the root; ``None`` for a bare root.

        Examples:
            >>> TemplateResolver.extract_first_field_segment("node.field[0].nested")
            'field'
            >>> TemplateResolver.extract_first_field_segment("a[${item.i}].x")
            'x'
            >>> TemplateResolver.extract_first_field_segment("data[0]") is None
            True
        """
        ref = parse_path(var)
        if ref is not None:
            return next((seg.name for seg in ref.path if isinstance(seg, Field)), None)
        # A raw user-typed path (`result.@type`): split lexically.
        parts = var.split(".", 1)
        if len(parts) != 2:
            return None
        return parts[1].split(".", 1)[0].split("[", 1)[0]

    @staticmethod
    def resolve_coalesce(expr: str, context: Mapping[str, Any]) -> tuple[Any, str]:
        """Resolve an expression (the text inside ``${…}``): ``(value, "resolved")``
        from the first operand that resolves, else ``(None, "unresolved")`` —
        also when ``expr`` is not in the expression grammar."""
        expression = _expression_at("${" + expr + "}", 0)
        if expression is not None and expression.raw == expr:
            found, value, _ = _evaluate(expression, context)
            if found:
                return value, "resolved"
        return None, "unresolved"

    @staticmethod
    def extract_simple_template_var(value: str) -> str | None:
        """The expression text of a simple template (``"${a[${i}].x}"`` → ``"a[${i}].x"``), else ``None``.

        Examples:
            >>> TemplateResolver.extract_simple_template_var("${user.name}")
            'user.name'
            >>> TemplateResolver.extract_simple_template_var("Hello ${name}") is None
            True
        """
        template = parse(value)
        return template.expressions[0].raw if template.is_simple else None

    # Kept: the direct-test surface of `test_template_resolver.py`.
    _convert_to_string = staticmethod(to_string)

    @staticmethod
    def reads_declared_input(var_name: str, context: Mapping[str, Any]) -> bool:
        """Whether a RAW path's root is a declared non-``any`` input of ``context``'s workflow —
        a value read there is never re-parsed, by the walk or by whoever displays it."""
        return _declared_typed(context, _split_raw_path(var_name)[0])

    @staticmethod
    def variable_exists(var_name: str, context: Mapping[str, Any]) -> bool:
        """Whether a RAW path reaches a value (``None`` included) — the walk's ``found``."""
        return _walk(*_split_raw_path(var_name), context)[0]

    @staticmethod
    def resolve_value(var_name: str, context: Mapping[str, Any]) -> Any | None:
        """The value at a RAW path, or ``None`` on a miss (``variable_exists`` tells
        a found ``None`` from a miss). ``data.items[0].name`` →
        ``context['data']['items'][0]['name']``."""
        return _walk(*_split_raw_path(var_name), context)[1]

    @staticmethod
    def resolve_template(template: str, context: Mapping[str, Any]) -> Any:
        """``resolve(template, context).value``: a simple template keeps its value's
        type, a complex one is a string, an unresolved expression stays literal,
        each ``$${`` escape becomes ``${``.

        Examples:
            >>> TemplateResolver.resolve_template("${count}", {"count": 42})
            42
            >>> TemplateResolver.resolve_template("Missing: ${undefined}", {})
            'Missing: ${undefined}'
        """
        return resolve(template, context).value

    @staticmethod
    def resolve_nested(value: Any, context: Mapping[str, Any]) -> Any:
        """``resolve(value, context, auto_parse=True).value``: nested dicts/lists
        resolved in place, and a simple template's JSON-container string parsed
        (``{"data": "${shell.stdout}"}`` gets structured data; ``"prefix ${var}"``
        is the escape hatch that keeps the raw string).

        Examples:
            >>> TemplateResolver.resolve_nested({"data": "${s.out}"}, {"s": {"out": '{"a": 1}'}})
            {'data': {'a': 1}}
        """
        return resolve(value, context, auto_parse=True).value

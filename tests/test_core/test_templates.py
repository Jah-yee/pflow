"""The typed parse of ``pflow.core.templates``: AST shapes, spans, immutability,
boundedness, totality, and the path grammar (Task 170 phase 4a).

The corpus (``test_template_grammar.py``, ``test_template_parity.py``) pins what
consumers observe; this file pins the structure they read.
"""

from __future__ import annotations

import dataclasses
import itertools
import logging
from typing import Any

import pytest

from pflow.core.templates import (
    DynamicIndex,
    Expression,
    Field,
    Index,
    Issue,
    Literal,
    Reference,
    Resolution,
    Template,
    TemplateResolver,
    Text,
    embedded_code,
    hidden_inserts,
    lookup,
    near_miss_insert,
    parse,
    parse_path,
    resolve,
)


def ref(raw: str) -> Reference:
    parsed = parse_path(raw)
    assert parsed is not None, raw
    return parsed


# ---------------------------------------------------------------------------
# AST shapes and spans
# ---------------------------------------------------------------------------

SHAPES: tuple[tuple[str, tuple[Any, ...], bool], ...] = (
    ("", (), False),
    ("plain", (Text("plain"),), False),
    ("${a}", (Expression((Reference("a", (), "a"),), "a", (0, 4)),), False),
    (
        "${node.items[0].n}",
        (
            Expression(
                (Reference("node", (Field("items"), Index(0), Field("n")), "node.items[0].n"),),
                "node.items[0].n",
                (0, 18),
            ),
        ),
        False,
    ),
    (
        '${a[${i.j}].x ?? "d"}',
        (
            Expression(
                (
                    Reference("a", (DynamicIndex(Reference("i", (Field("j"),), "i.j")), Field("x")), "a[${i.j}].x"),
                    Literal('"d"'),
                ),
                'a[${i.j}].x ?? "d"',
                (0, 21),
            ),
        ),
        False,
    ),
    ("[${a}]", (Text("["), Expression((Reference("a", (), "a"),), "a", (1, 5)), Text("]")), False),
    (
        "${a}${b}",
        (Expression((Reference("a", (), "a"),), "a", (0, 4)), Expression((Reference("b", (), "b"),), "b", (4, 8))),
        False,
    ),
    ("Hi $${x} ${y}!", (Text("Hi ${x} "), Expression((Reference("y", (), "y"),), "y", (9, 13)), Text("!")), True),
    ("$$${x}", (Text("$${x}"),), True),
    ("$${a[${i}]}", (Text("${a[${i}]}"),), True),
    ("$${unclosed ${b}", (Text("${unclosed "), Expression((Reference("b", (), "b"),), "b", (12, 16))), True),
    ("${c.result.0} tail", (Issue("${c.result.0}", (0, 13), "malformed"), Text(" tail")), False),
    ("${a", (Issue("${a", (0, 3), "malformed"),), False),
    ("${a[${i ?? 0}]}", (Issue("${a[${i ?? 0}", (0, 13), "malformed"), Text("]}")), False),
    ('${a ?? "\\q"}', (Issue('${a ?? "\\q"}', (0, 12), "bad_literal"),), False),
    ("${a ?? 007}", (Issue("${a ?? 007}", (0, 11), "bad_literal"),), False),
    ("${0}", (Expression((Literal("0"),), "0", (0, 4)),), False),
    ("${true}", (Expression((Literal("true"),), "true", (0, 7)),), False),
    ("${truthy}", (Expression((Reference("truthy", (), "truthy"),), "truthy", (0, 9)),), False),
    # A JSON insert: `raw` keeps the suffix (the span reassembles), `as_json` marks it.
    ("${x|json}", (Expression((Reference("x", (), "x"),), "x|json", (0, 9), as_json=True),), False),
    (
        '${a ?? "d" | json}!',
        (Expression((Reference("a", (), "a"), Literal('"d"')), 'a ?? "d" | json', (0, 18), as_json=True), Text("!")),
        False,
    ),
    (
        '${a ?? "x|json"}',
        (Expression((Reference("a", (), "a"), Literal('"x|json"')), 'a ?? "x|json"', (0, 16)),),
        False,
    ),
    ("${x|JSON}", (Issue("${x|JSON}", (0, 9), "malformed"),), False),
)


@pytest.mark.parametrize(("source", "segments", "escaped"), SHAPES, ids=[s[0] or "<empty>" for s in SHAPES])
def test_parse_shape(source: str, segments: tuple[Any, ...], escaped: bool) -> None:
    assert parse(source) == Template(source, segments, escaped)


def test_views() -> None:
    template = parse("pre ${a[${i}].x ?? b} ${c.x.0} $${esc}")
    assert [e.raw for e in template.expressions] == ["a[${i}].x ?? b"]
    assert [i.raw for i in template.issues] == ["${c.x.0}"]
    # Dependency view: outer references, then each dynamic index's inner one.
    assert [r.raw for r in template.references] == ["a[${i}].x", "i", "b"]
    # Value view: only value-position operands.
    assert [op.raw for op in template.expressions[0].operands] == ["a[${i}].x", "b"]
    assert template.escaped and template.needs_resolution and not template.is_simple
    assert parse("${a[${i}].x}").is_simple
    assert not parse("${c.x.0}").needs_resolution  # an Issue-only value is static
    assert parse("$${x}").needs_resolution and not parse("$${x}").expressions
    # A JSON insert is never simple, so resolution never preserves (or auto-parses) its value.
    assert parse("${x}").is_simple and not parse("${x|json}").is_simple and not parse("${x|json}\n").is_simple


# ---------------------------------------------------------------------------
# Immutability and boundedness (a cached AST is shared across runs and threads)
# ---------------------------------------------------------------------------


def test_ast_is_frozen_and_uses_tuples() -> None:
    template = parse("${a[${i}].x ?? []} ${b}")
    assert parse("${a[${i}].x ?? []} ${b}") is template  # cached: one shared object
    expression = template.expressions[0]
    reference = expression.operands[0]
    assert isinstance(reference, Reference)
    for node, attr in ((template, "source"), (expression, "raw"), (reference, "root"), (reference.path[0], "ref")):
        with pytest.raises(dataclasses.FrozenInstanceError):
            setattr(node, attr, "mutated")
    assert all(type(seq) is tuple for seq in (template.segments, expression.operands, reference.path))


def test_literal_value_is_fresh_on_every_resolution() -> None:
    first = resolve("${missing ?? []}", {}).value
    first.append("leak")
    second = resolve("${missing ?? []}", {}).value
    assert second == [] and second is not first


def test_parse_cache_is_bounded() -> None:
    assert parse.cache_info().maxsize is not None


# ---------------------------------------------------------------------------
# Totality: parse and resolve never raise
# ---------------------------------------------------------------------------

_TOKENS = ("$", "{", "}", "${", "$${", "a", ".", "[", "]", "??", "0", '"', " ", "é", "|json")
_FIXED = (
    "${a[${i}].x}",
    "${a[${i}].x ?? b}",
    "${r[${i}]}",
    "$${a[${i}]}",
    "$${FOO:-${bar}}",
    "Type $${ to open. Hi ${name}",
    "${x} $${x}",
    "${arr[${idx ?? 0}]}",
    "${a[${b[${c}]}]}",
    '${a ?? "${b}"}',
    "[${none_val}]",
    "${m[0][1]}",
    "${data.result.}",
    "${data..result.x}",
    "${c.result.0}",
    "${ a }",
    "${#x}",
    "${VAR:-x}",
    "$",
    "${",
    "}",
    "$$",
    "${\u00e9}",
    "\u00e9 ${a} \u2603",
    "${a\n}",
    '${a ?? "\\u12"}',
    '${a ?? "a\tb"}',
    "$${",
    "$${}",
    "${}}",
    "{{${a}}}",
    "${a[${i}]",
    "${a[${}]}",
    "${a[${ i }]}",
    "${a[-1]}",
    "${a[01]}",
    "$$$$${a}",
    "${" * 20,
    "}" * 20,
    "${a}" * 50,
    "${a|json} ${a}",
    "$${a|json}",
    "${${a|json} + 1}",
    "$${x ${a|json}}",
    "${a|json }",
    "${a|JSON}",
    "${a[${i}]|json}",
    "'${a|json}'",
)
FUZZ: tuple[str, ...] = tuple("".join(p) for p in itertools.product(_TOKENS, repeat=2)) + _FIXED


def test_fuzz_set_size() -> None:
    assert len(FUZZ) == 15 * 15 + 48


@pytest.mark.parametrize("source", FUZZ)
def test_parse_and_resolve_never_raise(source: str) -> None:
    template = parse(source)
    assert isinstance(template, Template)
    context = {"a": [1], "i": 0, "b": "B"}
    assert isinstance(resolve(source, context), Resolution)
    assert isinstance(resolve(source, context, embedded=True), Resolution)
    for issue in template.issues:
        near_miss_insert(source, issue)
    # The uncached scans agree with the cached parse.
    assert TemplateResolver.has_templates(source) is template.needs_resolution
    assert TemplateResolver.has_references(source) is bool(template.expressions)
    # The embedded view is lossless: its Text plus its inserts' source spans are the source.
    view = embedded_code(template)
    rejoined = "".join(
        seg.text if isinstance(seg, Text) else source[seg.span[0] : seg.span[1]] for seg in view.segments
    )
    assert rejoined == source
    assert TemplateResolver.has_templates(source, embedded=True) is bool(view.expressions)
    assert all(source[start:end].endswith("json}") for start, end in hidden_inserts(template))


_OVERSIZED = "9" * 5000  # past Python's default int-string conversion limit (4300 digits)


@pytest.mark.parametrize(
    "source",
    [
        "${1\u0662}",  # Arabic-Indic digits: Python's `\\d` matches them, `json.loads` does not
        "${1\u0662 ?? 7}",
        "${x.missing ?? 1\u0661 ?? 0}",
        "${1.\u0662}",
        "${a[\u0661]}",
        "${a[" + _OVERSIZED + "]}",
        "${" + _OVERSIZED + "}",
        "${x.missing ?? " + _OVERSIZED + "}",
    ],
    ids=[
        "digit",
        "digit-coalesce",
        "digit-after-miss",
        "digit-fraction",
        "digit-index",
        "big-index",
        "big-literal",
        "big-fallback",
    ],
)
def test_numbers_json_cannot_decode_are_issues(source: str) -> None:
    """The grammar admits only what the walk can convert, so parse and resolve stay total."""
    assert [type(s) for s in parse(source).segments] == [Issue]
    resolution = resolve(source, {"x": {}})
    assert (resolution.value, resolution.issues) == (source, frozenset({source}))


def test_a_large_number_within_the_limit_is_a_literal() -> None:
    big = "9" * 100
    assert resolve("${x.missing ?? " + big + "}", {"x": {}}).value == int(big)
    assert resolve("${a[" + big + "]}", {"a": [1]}).unresolved == frozenset({"a[" + big + "]"})


# ---------------------------------------------------------------------------
# The path grammar (the eight ``TestSplitTemplatePath`` expectations, re-homed)
# ---------------------------------------------------------------------------

PATHS: tuple[tuple[str, Reference | None], ...] = (
    ("node.field", Reference("node", (Field("field"),), "node.field")),
    ("a.b.c", Reference("a", (Field("b"), Field("c")), "a.b.c")),
    ("node", Reference("node", (), "node")),
    (
        "drafts.results[${item.draft_index}].response",
        Reference(
            "drafts",
            (Field("results"), DynamicIndex(ref("item.draft_index")), Field("response")),
            "drafts.results[${item.draft_index}].response",
        ),
    ),
    (
        "node.data[${__index__}].field",
        Reference(
            "node", (Field("data"), DynamicIndex(ref("__index__")), Field("field")), "node.data[${__index__}].field"
        ),
    ),
    (
        "a[${x.y}].b[${z.w}].c",
        Reference(
            "a", (DynamicIndex(ref("x.y")), Field("b"), DynamicIndex(ref("z.w")), Field("c")), "a[${x.y}].b[${z.w}].c"
        ),
    ),
    (
        "node.results[${item.data.index}].value",
        Reference(
            "node",
            (Field("results"), DynamicIndex(ref("item.data.index")), Field("value")),
            "node.results[${item.data.index}].value",
        ),
    ),
    ("", None),
    ("node.data[${idx}]", Reference("node", (Field("data"), DynamicIndex(ref("idx"))), "node.data[${idx}]")),
    # Outside the grammar: multi-index, `??` or nesting in an index, digit/empty segments.
    ("m[0][1]", None),
    ("a[${i ?? 0}]", None),
    ("a[${b[${c}]}]", None),
    ("c.result.0", None),
    ("data..x", None),
    ("result.@type", None),
)


@pytest.mark.parametrize(("path", "expected"), PATHS, ids=[p[0] or "<empty>" for p in PATHS])
def test_parse_path(path: str, expected: Reference | None) -> None:
    assert parse_path(path) == expected


def test_inner_reference_is_static() -> None:
    inner = ref("a[${i.j[0]}]").path[0]
    assert inner == DynamicIndex(Reference("i", (Field("j"), Index(0)), "i.j[0]"))


# ---------------------------------------------------------------------------
# The walk: one Reference, whatever fails inside it
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("index", "found"),
    [(0, True), (1, True), (2, False), (-1, False), (True, False), (None, False), ("1", False), (1.0, False)],
)
def test_dynamic_index_must_be_an_in_range_int(index: Any, found: bool) -> None:
    context = {"a": [{"x": "v0"}, {"x": "v1"}], "i": index}
    assert lookup(ref("a[${i}].x"), context)[0] is found
    result = resolve("${a[${i}].x}", context)
    assert result.ok is found
    if not found:
        assert result == Resolution("${a[${i}].x}", unresolved=frozenset({"a[${i}].x"}))


def test_non_int_index_warns_and_coalesce_falls_through(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.WARNING, logger="pflow.core.templates")
    assert resolve("${a[${i}].x ?? b}", {"a": [{"x": "v"}], "i": "s", "b": "fb"}) == Resolution("fb")
    assert "Nested index must be integer, got str" in caplog.text


def test_dynamic_index_over_json_string_list() -> None:
    assert resolve("${a[${i}].x}", {"a": '[{"x": 7}]', "i": 0}) == Resolution(7)


def test_raw_path_reader_chains_indices_through_json_strings() -> None:
    """The raw reader and the template walk share one walk: every index step parses a
    JSON-array string (before Task 170 4a the raw reader parsed only before the chain)."""
    context = {"x": ["[1, 2]"]}
    assert TemplateResolver.variable_exists("x[0][1]", context) is True
    assert TemplateResolver.resolve_value("x[0][1]", context) == 2


# ---------------------------------------------------------------------------
# Facade helpers that read the parse
# ---------------------------------------------------------------------------


def test_extract_first_field_segment_reads_the_path_grammar() -> None:
    assert TemplateResolver.extract_first_field_segment("a[${item.i}].x") == "x"
    assert TemplateResolver.extract_first_field_segment("node[0].field") == "field"
    assert TemplateResolver.extract_first_field_segment("data[0]") is None
    assert TemplateResolver.extract_first_field_segment("result.@type") == "@type"  # raw fallback


def test_resolve_coalesce_speaks_the_expression_grammar() -> None:
    context = {"b": {"x": 1}, "i": 0, "a": [{"x": 2}]}
    assert TemplateResolver.resolve_coalesce("missing ?? b.x", context) == (1, "resolved")
    assert TemplateResolver.resolve_coalesce("a[${i}].x", context) == (2, "resolved")
    assert TemplateResolver.resolve_coalesce("b.x.0", context) == (None, "unresolved")  # not an expression


def test_extract_variables_is_the_value_view() -> None:
    assert TemplateResolver.extract_variables('${a[${i}].x ?? b ?? "d"} $${e} ${c.0}') == {"a[${i}].x", "b"}


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("a.x", (1, "x")),
        ("a[0].x.y", (4, "x")),
        ("a[01].x", (5, "x")),  # the offset is read from the source, not a re-rendered `[1]`
        ("a[${i.j}].x", (9, "x")),
        ("a", None),
        ("a[${i}]", None),
    ],
)
def test_first_field_offset_skips_the_root_index(path: str, expected: tuple[int, str] | None) -> None:
    reference = ref(path)
    assert reference.first_field() == expected
    if expected is not None:
        assert path[expected[0]] == "." and path[expected[0] + 1 :].startswith(expected[1])


def test_one_trailing_newline_keeps_a_template_simple() -> None:
    """A YAML block scalar (`v: |`) ends in `\\n`; `${x}\\n` has always been simple — type
    preserved, newline dropped (the old `^…$` anchor matched before a final newline)."""
    context = {"p": {"items": [1, 2]}}
    assert resolve("${p.items}\n", context) == Resolution([1, 2])
    assert TemplateResolver.extract_simple_template_var("${p.items}\n") == "p.items"
    assert resolve("${missing}\n", {}) == Resolution("${missing}\n", unresolved=frozenset({"missing"}))
    # Only one newline: anything more is complex text.
    assert resolve("${p.items}\n\n", context) == Resolution("[1, 2]\n\n")
    assert not parse(" ${p.items}").is_simple and not parse("${p.items} ").is_simple


# ---------------------------------------------------------------------------
# JSON inserts and the embedded-code view (Task 181)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "inserted"),
    [
        ("Don't Stop", '"Don\'t Stop"'),
        (True, "true"),
        (None, "null"),
        (3, "3"),
        ({"a": [1, 2]}, '{"a": [1, 2]}'),
        ("é", '"é"'),
        ("42\n", '"42\\n"'),  # text stays a string — never re-parsed
        ('{"a":1}', '"{\\"a\\":1}"'),  # JSON text is a string too
        ({1}, '"{1}"'),  # JSON cannot encode a set: the JSON string of its text
    ],
    ids=["apostrophe", "true", "null", "int", "object", "non-ascii", "text", "json-text", "set"],
)
def test_a_json_insert_enters_its_value_as_a_json_literal(value: Any, inserted: str) -> None:
    assert resolve("const v = ${v|json};", {"v": value}, embedded=True) == Resolution(f"const v = {inserted};")
    # A whole-value insert is text too: never type-preserved, never auto-parsed.
    assert resolve("${v|json}", {"v": value}, auto_parse=True, embedded=True) == Resolution(inserted)


def test_a_json_insert_of_a_coalesce_encodes_the_winning_operand() -> None:
    assert resolve('${missing ?? "x" | json}', {}, embedded=True) == Resolution('"x"')
    assert resolve("${missing ?? b|json}", {"b": False}, embedded=True) == Resolution("false")
    assert resolve("${a[${i}].x|json}", {"a": [{"x": "v"}], "i": 0}, embedded=True) == Resolution('"v"')


def test_an_unresolved_insert_stays_literal_in_the_unresolved_channel() -> None:
    assert resolve("f(${up.missing|json})", {"up": {}}, embedded=True) == Resolution(
        "f(${up.missing|json})", unresolved=frozenset({"up.missing|json"})
    )


def test_a_json_insert_outside_embedded_code_is_kept_as_written_like_an_issue() -> None:
    """D4: ordinary resolution never fills a JSON insert in — the validator rejects it there,
    and a run that skipped validation must not run what validation rejects."""
    assert resolve("say ${x|json} ${x}", {"x": 1}) == Resolution("say ${x|json} 1", issues=frozenset({"${x|json}"}))
    assert resolve("${x|json}", {"x": 1}, auto_parse=True) == Resolution("${x|json}", issues=frozenset({"${x|json}"}))


_JS = "`${a + b}` $${p} ${user.name} ${t|json} '${x}'"


def test_the_embedded_view_keeps_only_json_inserts_and_cuts_the_rest_from_the_source() -> None:
    view = embedded_code(parse(_JS))
    assert [(e.raw, e.span) for e in view.expressions] == [("t|json", (30, 39))]
    assert [seg.text for seg in view.segments if isinstance(seg, Text)] == [_JS[:30], _JS[39:]]
    assert not view.issues and not view.escaped


def test_embedded_resolution_fills_only_the_insert() -> None:
    context = {"t": "it's", "user": {"name": "N"}, "p": "P", "x": "X"}
    assert resolve(_JS, context, embedded=True) == Resolution("`${a + b}` $${p} ${user.name} \"it's\" '${x}'")
    # Presence pair: ordinary resolution of the same text does fill `${user.name}`.
    assert "N" in resolve(_JS, context).value
    # A container's leaves are read the same way.
    assert resolve({"f": ["${user.name} ${t|json}"]}, context, embedded=True).value == {"f": ['${user.name} "it\'s"']}


@pytest.mark.parametrize(
    ("value", "ordinary", "embedded"),
    [
        ("`$${p}`", True, False),  # an escape is not one in embedded code: static, both `$` kept
        ("${user.name}", True, False),  # a bare `${…}` is JavaScript
        ("${t|json}", True, True),
        ({"k": ["x", "${t|json}"]}, True, True),
        ("${a + b}", False, False),
    ],
)
def test_has_templates_in_embedded_code_counts_only_json_inserts(value: Any, ordinary: bool, embedded: bool) -> None:
    assert TemplateResolver.has_templates(value) is ordinary
    assert TemplateResolver.has_templates(value, embedded=True) is embedded


@pytest.mark.parametrize(
    ("source", "hidden"),
    [
        ("`cost: $${count|json}`", ["${count|json}"]),  # inside an escape
        ("$${foo ${x|json}}", ["${x|json}"]),  # inside an escape's body
        ("`${${x|json} + 1}`", ["${x|json}"]),  # swallowed by an Issue
        ("${x|json}", []),
        ("`$${price}`", []),
        ("${a + b}", []),
        ("${x|json} $${y|json}", ["${y|json}"]),  # a visible insert beside a hidden one
        ('`${"${x|json}"}`', ["${x|json}"]),  # inside another Expression's literal operand
        ("$${a[${i}]|json}", ["${a[${i}]|json}"]),  # nested `${`: every opening is tried
    ],
)
def test_hidden_inserts_are_the_inserts_the_parse_could_not_see(source: str, hidden: list[str]) -> None:
    spans = hidden_inserts(parse(source))
    assert [source[start:end] for start, end in spans] == hidden
    assert all(source.index(text) == start for text, (start, _) in zip(hidden, spans, strict=True))


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("${x|json }", ("${x|json }", "${x|json}")),
        ("${ x|json}", ("${ x|json}", "${x|json}")),
        ("${x|JSON}", ("${x|JSON}", "${x|json}")),
        ('${ a ?? "d" | Json }', ('${ a ?? "d" | Json }', '${a ?? "d"|json}')),
        # The Issue ends at the first `}`; the written text runs brace-balanced past it.
        ("(${{}|JSON})", ("${{}|JSON}", "${{}|json}")),
        ("${rows[${i}]|JSON} tail", ("${rows[${i}]|JSON}", "${rows[${i}]|json}")),
        ("${x|jsn}", None),  # a different word: in JavaScript a bitwise or
        ("${a + b}", None),
        ("${ x }", None),
        ("${x|json", None),  # unclosed
    ],
)
def test_near_miss_insert_names_the_insert_an_issue_was_meant_to_be(
    source: str, expected: tuple[str, str] | None
) -> None:
    """``(as written, meant)``."""
    (issue,) = parse(source).issues
    assert near_miss_insert(source, issue) == expected


def test_the_lexical_patterns_read_an_insert_as_its_expression() -> None:
    match = TemplateResolver.TEMPLATE_PATTERN.search("x ${a.b|json} y")
    assert match is not None and match.group(1) == "a.b" and match.group(0) == "${a.b|json}"
    # One group: `findall` consumers (prompt refs, token estimation) still get strings.
    assert TemplateResolver.TEMPLATE_PATTERN.findall("${a ?? b|json} ${c}") == ["a ?? b", "c"]
    assert TemplateResolver.SIMPLE_TEMPLATE_PATTERN.match("${a.b|json}") is None

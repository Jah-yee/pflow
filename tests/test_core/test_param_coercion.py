"""Tests for parameter type coercion utilities.

Focus:
1. Behavior that matters for MCP tools expecting JSON strings (coerce_param_for_node)
2. The declared-type input boundary (coerce_declared_input): decision (b)'s grammar for
   text, decision (h) for typed values, decision (d)'s lossless inference, and the error.
"""

import json
import logging
from typing import Any, get_args

import pytest

from pflow.core.exceptions import InputTypeError
from pflow.core.param_coercion import InputSource, coerce_declared_input, coerce_param_for_node
from pflow.core.validation_utils import VALIDATION_PLACEHOLDER

ALL_TYPES = ["string", "integer", "number", "boolean", "object", "array", "any"]
ALL_SOURCES: tuple[InputSource, ...] = get_args(InputSource)


class TestDictToStringCoercion:
    """Test dict -> JSON string coercion for str-typed parameters."""

    def test_dict_becomes_json_string_when_type_is_str(self):
        """Main use case: MCP tool expects JSON string, we have dict."""
        result = coerce_param_for_node({"channel_id": "123"}, "str")

        assert isinstance(result, str)
        # Should be valid JSON that parses back to original
        assert json.loads(result) == {"channel_id": "123"}

    def test_nested_dict_serializes_correctly(self):
        """Nested structures should serialize to valid JSON."""
        value = {"outer": {"inner": {"deep": "value"}}}
        result = coerce_param_for_node(value, "str")

        assert isinstance(result, str)
        assert json.loads(result) == value


class TestListToStringCoercion:
    """Test list -> JSON string coercion for str-typed parameters."""

    def test_list_becomes_json_string_when_type_is_str(self):
        """List should serialize to JSON array string."""
        result = coerce_param_for_node([1, 2, 3], "str")

        assert isinstance(result, str)
        assert json.loads(result) == [1, 2, 3]

    def test_list_of_dicts_serializes_correctly(self):
        """Complex list structures should serialize properly."""
        value = [{"id": 1, "name": "a"}, {"id": 2, "name": "b"}]
        result = coerce_param_for_node(value, "str")

        assert isinstance(result, str)
        assert json.loads(result) == value


class TestNoCoercionWhenTypeMatches:
    """Ensure we don't break params that should stay as dict/list."""

    def test_dict_unchanged_when_type_is_dict(self):
        """Dict stays dict when expected type is dict."""
        original = {"key": "value"}
        result = coerce_param_for_node(original, "dict")

        assert result is original  # Same object, not serialized
        assert isinstance(result, dict)

    def test_dict_unchanged_when_type_is_object(self):
        """Dict stays dict when expected type is object (JSON Schema alias)."""
        original = {"key": "value"}
        result = coerce_param_for_node(original, "object")

        assert result is original
        assert isinstance(result, dict)

    def test_list_unchanged_when_type_is_list(self):
        """List stays list when expected type is list."""
        original = [1, 2, 3]
        result = coerce_param_for_node(original, "list")

        assert result is original
        assert isinstance(result, list)

    def test_list_unchanged_when_type_is_array(self):
        """List stays list when expected type is array (JSON Schema alias)."""
        original = [1, 2, 3]
        result = coerce_param_for_node(original, "array")

        assert result is original
        assert isinstance(result, list)


class TestPassthroughBehavior:
    """Values that should pass through unchanged."""

    def test_string_unchanged_when_type_is_str(self):
        """String passes through unchanged (no double-encoding)."""
        result = coerce_param_for_node("already a string", "str")
        assert result == "already a string"

    def test_json_string_not_double_encoded(self):
        """If user already passed JSON string, don't double-encode."""
        json_string = '{"already": "json"}'
        result = coerce_param_for_node(json_string, "str")
        assert result == json_string  # Same string, not '"{...}"'

    def test_none_passes_through(self):
        """None should pass through (let node handle it)."""
        result = coerce_param_for_node(None, "str")
        assert result is None

    def test_no_coercion_when_type_unknown(self):
        """No coercion when expected_type is None (unknown)."""
        original = {"key": "value"}
        result = coerce_param_for_node(original, None)
        assert result is original


class TestUnicodeHandling:
    """Test Unicode and special characters."""

    def test_unicode_in_dict_serializes_correctly(self):
        """Unicode characters should serialize and parse correctly."""
        result = coerce_param_for_node({"emoji": "🚀", "chinese": "你好"}, "str")

        assert isinstance(result, str)
        parsed = json.loads(result)
        assert parsed["emoji"] == "🚀"
        assert parsed["chinese"] == "你好"

    def test_special_characters_in_values(self):
        """Special characters (newlines, quotes) should be escaped."""
        result = coerce_param_for_node({"text": 'line1\nline2\twith "quotes"'}, "str")

        assert isinstance(result, str)
        parsed = json.loads(result)
        assert parsed["text"] == 'line1\nline2\twith "quotes"'


class TestNonSerializableHandling:
    """Test graceful handling of non-JSON-serializable objects."""

    def test_non_serializable_object_falls_back(self):
        """Non-serializable objects should fall back to original value."""

        class CustomClass:
            pass

        original = {"obj": CustomClass()}
        result = coerce_param_for_node(original, "str")

        # Should return original dict (not crash)
        assert result is original
        assert isinstance(result, dict)

    def test_partially_serializable_dict_falls_back(self):
        """Dict with non-serializable values should fall back."""
        import io

        # File handles are not JSON serializable
        original = {"file": io.StringIO("test")}
        result = coerce_param_for_node(original, "str")

        assert result is original


# =============================================================================
# coerce_declared_input — a workflow input typed by its declaration
# =============================================================================


def _error(name: str, declared: str | None, value: Any, source: InputSource = "argument") -> InputTypeError:
    with pytest.raises(InputTypeError) as exc_info:
        coerce_declared_input(name, declared, value, source=source)
    return exc_info.value


def _context(error: InputTypeError) -> dict[str, Any]:
    (diagnostic,) = error.to_diagnostics()
    assert diagnostic.context is not None
    return diagnostic.context


# Text that fits its declared type → the typed value (type checked exactly: 3 == 3.0 in Python).
ACCEPTED_TEXT: list[tuple[str, str, Any]] = [
    ("integer", "3", 3),
    ("integer", "-3", -3),
    ("integer", "007", 7),
    ("integer", " 3\n", 3),  # stdin arrives with a newline; surrounding whitespace is stripped
    ("integer", "-0", 0),
    ("number", "3", 3),  # integer text yields an int
    ("number", "3.0", 3.0),
    ("number", "1e3", 1000.0),
    ("number", "-0.5", -0.5),
    ("number", "0", 0),
    ("number", "2.5\n", 2.5),
    *[("boolean", text, True) for text in ("true", "TRUE", "True", "yes", "YES", "Yes", "1")],
    *[("boolean", text, False) for text in ("false", "FALSE", "False", "no", "NO", "No", "0")],
    ("boolean", " true\n", True),
    ("object", '{"a":1}', {"a": 1}),
    ("object", ' {"a": [1, 2]}\n', {"a": [1, 2]}),
    ("array", "[1]", [1]),
    ("array", '["a", "b"]', ["a", "b"]),
    ("string", " 42", " 42"),  # a string's text is kept exactly — never stripped
    ("string", '{"a":1}', '{"a":1}'),  # never parsed
    ("string", "02134", "02134"),
]

REJECTED_TEXT: list[tuple[str, str]] = [
    *[("integer", t) for t in ("3.0", "3.5", "1e3", "true", "1_000", "\u0663", "", "abc", "0x10", "+3")],
    *[("number", t) for t in ("007", "nan", "inf", "Infinity", "-Infinity", "1_000", "abc", "1e999", "", ".5", "1.")],
    *[("boolean", t) for t in ("maybe", "2", "", "on", "t")],
    *[("object", t) for t in ("[1]", "{", '"x"', '{"a": NaN}', "null", "")],
    *[("array", t) for t in ('{"a":1}', "1", "[1,", "[Infinity]", "")],
]


class TestDeclaredTypeGrammar:
    """Decision (b): text is read by the strict ASCII grammar of its declared type."""

    @pytest.mark.parametrize(("declared", "text", "expected"), ACCEPTED_TEXT)
    def test_accepted_text_becomes_the_typed_value(self, declared: str, text: str, expected: Any) -> None:
        result = coerce_declared_input("v", declared, text, source="argument")
        assert result == expected
        assert type(result) is type(expected)

    @pytest.mark.parametrize(("declared", "text"), REJECTED_TEXT)
    def test_text_outside_the_grammar_is_an_error(self, declared: str, text: str) -> None:
        context = _context(_error("v", declared, text))
        assert context["declared_type"] == declared
        assert context["received"] == text
        assert context["input"] == "v"


# A value that is already typed (MCP JSON, a parent's value, a YAML-typed default) — decision (h).
ACCEPTED_VALUES: list[tuple[str, Any, Any]] = [
    ("string", 3, "3"),
    ("string", True, "True"),  # the text ${x} produces — Task 118's to_string rule
    ("string", 2.5, "2.5"),
    ("string", 1458059302022549698, "1458059302022549698"),  # no precision loss (Discord snowflake)
    ("integer", 3, 3),
    ("number", 3, 3),
    ("number", 2.5, 2.5),
    ("boolean", True, True),
    ("boolean", False, False),
    ("object", {"a": 1}, {"a": 1}),
    ("array", [1], [1]),
    ("any", {"a": 1}, {"a": 1}),
]

REJECTED_VALUES: list[tuple[str, Any]] = [
    ("string", {"a": 1}),
    ("string", [1]),
    ("integer", True),
    ("integer", 3.0),
    ("number", True),
    ("boolean", 1),
    ("object", [1]),
    ("array", {"a": 1}),
]


class TestTypedValues:
    """Decision (h): a non-text value must already fit; a string takes any scalar."""

    @pytest.mark.parametrize(("declared", "value", "expected"), ACCEPTED_VALUES)
    def test_fitting_value(self, declared: str, value: Any, expected: Any) -> None:
        result = coerce_declared_input("v", declared, value, source="call")
        assert result == expected
        assert type(result) is type(expected)

    @pytest.mark.parametrize(("declared", "value"), REJECTED_VALUES)
    def test_misfit_value_is_an_error(self, declared: str, value: Any) -> None:
        context = _context(_error("v", declared, value, source="call"))
        assert context["declared_type"] == declared
        assert context["received"] == json.dumps(value)  # a non-text value shows as its JSON

    def test_boolean_text_one_is_true_but_the_integer_one_is_not(self) -> None:
        assert coerce_declared_input("flag", "boolean", "1", source="argument") is True
        _error("flag", "boolean", 1, source="call")


class TestAnyIsInferredLosslesslyFromTheCommandLineOnly:
    """Decision (d): an ``any`` / untyped CLI token is typed only when it reads back as the same text."""

    @pytest.mark.parametrize(
        ("text", "expected"),
        [("true", True), ("false", False), ("42", 42), ("-1", -1), ("2.5", 2.5), ("[1]", [1]), ('{"a":1}', {"a": 1})],
    )
    def test_text_that_reads_back_identically_is_typed(self, text: str, expected: Any) -> None:
        result = coerce_declared_input("v", "any", text, source="argument")
        assert result == expected
        assert type(result) is type(expected)

    @pytest.mark.parametrize(
        "text", ["02134", "1.10", "0755", "1e3", "TRUE", "yes", "null", " 42", "[1, 2]", '"x"', "-Infinity", "abc"]
    )
    def test_text_that_would_not_read_back_stays_text(self, text: str) -> None:
        assert coerce_declared_input("v", "any", text, source="argument") == text

    @pytest.mark.parametrize("source", [s for s in ALL_SOURCES if s != "argument"])
    def test_other_sources_are_kept_as_given(self, source: InputSource) -> None:
        assert coerce_declared_input("v", "any", "42", source=source) == "42"

    @pytest.mark.parametrize("declared", [None, "", "str"])
    def test_untyped_or_unknown_type_behaves_as_any(self, declared: str | None) -> None:
        assert coerce_declared_input("v", declared, "42", source="argument") == 42
        assert coerce_declared_input("v", declared, "02134", source="argument") == "02134"
        assert coerce_declared_input("v", declared, {"a": 1}, source="call") == {"a": 1}


class TestIdempotence:
    """A typed value passes through unchanged — resume replay, the child's compile and the
    web preflight all coerce a value a second time."""

    @pytest.mark.parametrize(
        ("declared", "value"),
        [(d, v) for d, v, _ in ACCEPTED_TEXT] + [(d, v) for d, v, _ in ACCEPTED_VALUES],
    )
    @pytest.mark.parametrize("source", ["argument", "recorded", "parent"])
    def test_second_coercion_changes_nothing(self, declared: str, value: Any, source: InputSource) -> None:
        once = coerce_declared_input("v", declared, value, source=source)
        twice = coerce_declared_input("v", declared, once, source=source)
        assert twice is once


class TestNoValueAndPlaceholder:
    @pytest.mark.parametrize("declared", ALL_TYPES)
    @pytest.mark.parametrize("source", ALL_SOURCES)
    def test_none_is_no_value_never_a_type_error(self, declared: str, source: InputSource) -> None:
        assert coerce_declared_input("v", declared, None, source=source) is None

    @pytest.mark.parametrize("declared", ALL_TYPES)
    def test_placeholder_passes_through_without_a_warning(
        self, declared: str, caplog: pytest.LogCaptureFixture
    ) -> None:
        """``generate_dummy_parameters()`` pads unresolved inputs with the sentinel during
        validation, cache-key prediction and the cross-workflow walker's compile pass."""
        with caplog.at_level(logging.WARNING):
            assert coerce_declared_input("v", declared, VALIDATION_PLACEHOLDER, source="argument") == (
                VALIDATION_PLACEHOLDER
            )
        assert caplog.records == []

    def test_a_failing_coercion_raises_and_never_warns(self, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(logging.WARNING):
            _error("count", "integer", "abc")
        assert caplog.records == []


class TestTheError:
    """The Diagnostic every boundary carries (diagnostics-checkpoint §1)."""

    def test_argument_error_names_input_type_value_and_the_fix(self) -> None:
        (diagnostic,) = _error("topics", "array", "tea").to_diagnostics()
        assert diagnostic.title == "Invalid input value"
        assert diagnostic.source == "validation"
        assert (
            diagnostic.message == "Input 'topics' is declared `- type: array` but received 'tea' from the command line."
        )
        assert diagnostic.suggestions == ['Pass a JSON array (e.g. ["a", "b"]): topics=\'["tea"]\'']
        assert diagnostic.context == {
            "category": "validation",
            "path": "inputs.topics",
            "input": "topics",
            "declared_type": "array",
            "received": "tea",
            "source": "argument",
            "accepted": 'a JSON array (e.g. ["a", "b"])',
        }

    @pytest.mark.parametrize(
        ("source", "clause", "suggestion"),
        [
            ("argument", "'3.0' from the command line", "Pass a whole number (e.g. 3): count=3"),
            ("stdin", "'3.0' from stdin", "Pipe a whole number (e.g. 3), or pass count=3 on the command line"),
            (
                "env",
                "'3.0' from the environment variable count",
                "export count=3, or pass count=3 (an argument wins over the environment)",
            ),
            ("settings", "'3.0' from settings.env", "pflow settings set-env count 3, or pass count=3"),
            ("recorded", "'3.0' recorded by the run being resumed", "Override it: pflow resume <run-id> count=3"),
            ("call", "'3.0' in the call's parameters", 'Pass a whole number: "count": 3'),
        ],
    )
    def test_each_source_names_where_the_value_came_from(
        self, source: InputSource, clause: str, suggestion: str
    ) -> None:
        (diagnostic,) = _error("count", "integer", "3.0", source=source).to_diagnostics()
        assert diagnostic.message == f"Input 'count' is declared `- type: integer` but received {clause}."
        assert diagnostic.suggestions == [suggestion]
        assert diagnostic.context is not None
        assert diagnostic.context["source"] == source
        assert diagnostic.context["path"] == "inputs.count"

    def test_a_default_is_blamed_at_its_own_path(self) -> None:
        (diagnostic,) = _error("n", "integer", "abc", source="default").to_diagnostics()
        assert diagnostic.message == "The default of input 'n' is 'abc' but its type is `- type: integer`."
        assert diagnostic.suggestions == [
            "Change the default to a whole number (e.g. `- default: 3`), or the type to `- type: string`."
        ]
        assert diagnostic.context is not None
        assert diagnostic.context["path"] == "inputs.n.default"
        assert diagnostic.context["source"] == "default"

    def test_a_default_fix_names_the_type_the_value_has(self) -> None:
        (diagnostic,) = _error("cfg", "object", [1], source="default").to_diagnostics()
        assert diagnostic.suggestions is not None
        assert diagnostic.suggestions[0].endswith("or the type to `- type: array`.")

    def test_a_typed_value_shows_as_json_unquoted(self) -> None:
        error = _error("count", "integer", 3.0, source="call")
        assert str(error) == "Input 'count' is declared `- type: integer` but received 3.0 in the call's parameters."

    @pytest.mark.parametrize(
        ("declared", "received", "fix"),
        [
            ("integer", "1e3", "count=1000"),
            ("integer", "abc", "count=3"),
            ("number", "1_000", "count=3"),
            ("array", "tea", "count='[\"tea\"]'"),
            ("object", "[1, 2]", "count='{\"a\": 1}'"),
        ],
    )
    def test_the_fix_is_the_smallest_repair_when_obvious(self, declared: str, received: str, fix: str) -> None:
        (diagnostic,) = _error("count", declared, received).to_diagnostics()
        assert diagnostic.suggestions is not None
        assert diagnostic.suggestions[0].endswith(f": {fix}")

    def test_a_sensitive_input_never_shows_its_value(self) -> None:
        shown = _error("ids", "array", "hunter2")
        assert "hunter2" in str(shown)  # presence: a non-sensitive name shows the value…
        (shown_diagnostic,) = shown.to_diagnostics()
        assert shown_diagnostic.suggestions == ['Pass a JSON array (e.g. ["a", "b"]): ids=\'["hunter2"]\'']

        masked = _error("token", "array", "hunter2")
        (diagnostic,) = masked.to_diagnostics()
        assert "hunter2" not in str(masked)  # …a sensitive one shows neither the value…
        assert "<REDACTED>" in str(masked)
        assert diagnostic.context is not None
        assert diagnostic.context["received"] == "<REDACTED>"
        # …nor a fix built from it.
        assert diagnostic.suggestions == ['Pass a JSON array (e.g. ["a", "b"]): token=\'["a", "b"]\'']

    @pytest.mark.parametrize(
        ("received", "shown"),
        [
            ({"password": "hunter2", "user": "bob"}, '{"password": "<REDACTED>", "user": "bob"}'),
            ('{"api_key": "hunter2", "n": 1}', '\'{"api_key": "<REDACTED>", "n": 1}\''),
            ([{"token": "hunter2"}], '[{"token": "<REDACTED>"}]'),
        ],
    )
    def test_a_sensitive_key_inside_the_value_is_redacted_and_never_echoed_by_the_fix(
        self, received: object, shown: str
    ) -> None:
        """The repo's display convention (`redact_sensitive`) reaches inside the value — a dict, a list, or
        JSON text — and the fix line, which could quote the value, falls back to the canonical example."""
        error = _error("s", "string" if not isinstance(received, str) else "integer", received, source="call")
        (diagnostic,) = error.to_diagnostics()
        assert "hunter2" not in str(error) + str(diagnostic.suggestions) + str(diagnostic.context)
        assert str(error).endswith(f"received {shown} in the call's parameters.")
        assert diagnostic.suggestions in (['Pass text: "s": "text"'], ['Pass a whole number: "s": 3'])

    def test_a_fix_line_never_carries_more_of_the_value_than_the_message(self) -> None:
        """R5 caps `received` at 80 characters; the fix line repeated a container in full (14k characters)."""
        long = {f"k{i}": i for i in range(400)}
        (diagnostic,) = _error("s", "string", long, source="call").to_diagnostics()
        assert diagnostic.suggestions == ['Pass text: "s": "text"']
        (short,) = _error("s", "string", {"a": 1}, source="call").to_diagnostics()
        assert short.suggestions == ['Pass text: "s": "{\\"a\\": 1}"']  # presence: a short one is still repaired

    @pytest.mark.parametrize(
        ("source", "suggestion"),
        [
            (
                "env",
                "export port=3, or pass `port: 3` under step 'call' `inputs:` (a passed value wins over the environment)",
            ),
            ("settings", "pflow settings set-env port 3, or pass `port: 3` under step 'call' `inputs:`"),
        ],
    )
    def test_a_childs_env_or_settings_fix_passes_the_value_from_the_calling_step(
        self, source: InputSource, suggestion: str
    ) -> None:
        """At a sub-workflow boundary there is no command line to pass `port=3` on — the root has no such input."""
        error = InputTypeError(
            name="port", declared_type="integer", received="abc", source=source, step="call", sub_workflow_path="./c.md"
        )
        assert error.to_diagnostics()[0].suggestions == [suggestion]

    @pytest.mark.parametrize(
        ("received", "accepted"),
        [(1, "true or false"), ("maybe", "true or false (also yes/no, 1/0)")],
    )
    def test_accepted_describes_the_form_the_value_came_in(self, received: object, accepted: str) -> None:
        """A typed JSON `1` is refused for a boolean: `accepted` must not say "also 1/0", which is the TEXT grammar."""
        assert _context(_error("b", "boolean", received, source="call"))["accepted"] == accepted

    def test_a_long_value_is_cut_at_80_characters(self) -> None:
        context = _context(_error("count", "integer", "x" * 300))
        assert context["received"] == "x" * 80 + "…"
        assert _context(_error("count", "integer", "x" * 80))["received"] == "x" * 80  # the limit itself is kept

    def test_the_parent_boundary_names_the_step_and_child(self) -> None:
        error = InputTypeError(
            name="n",
            declared_type="integer",
            received="x",
            source="parent",
            step="call",
            sub_workflow_path="./child.pflow.md",
        )
        (diagnostic,) = error.to_diagnostics()
        assert (
            diagnostic.message == "Step 'call' passes 'x' to input 'n' of ./child.pflow.md, declared `- type: integer`."
        )
        assert diagnostic.context is not None
        assert diagnostic.context["path"] == "nodes[id=call].params.inputs.n"
        assert diagnostic.context["sub_workflow_step"] == "call"
        assert diagnostic.context["sub_workflow_path"] == "./child.pflow.md"
        # The ruled "(here ${item} resolved to 'x')" clause is not built (the boundary never sees the
        # parent's template text): the fix line names only what to pass.
        assert diagnostic.suggestions == ["Pass a whole number from the parent."]

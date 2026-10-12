"""Tests for direct execution helper functions in CLI."""

import pytest

from pflow.cli.param_parsing import format_param_value, infer_type, parse_workflow_params
from pflow.cli.workflow_resolution import is_likely_workflow_name
from pflow.execution.formatters.run_outcome import format_cost_summary_lines


class TestInferType:
    """Test type inference from string values."""

    def test_boolean_true(self):
        """Test that 'true' variants are converted to boolean True."""
        assert infer_type("true") is True
        assert infer_type("True") is True
        assert infer_type("TRUE") is True

    def test_boolean_false(self):
        """Test that 'false' variants are converted to boolean False."""
        assert infer_type("false") is False
        assert infer_type("False") is False
        assert infer_type("FALSE") is False

    def test_integer(self):
        """Test integer detection."""
        assert infer_type("42") == 42
        assert infer_type("0") == 0
        assert infer_type("-10") == -10
        assert isinstance(infer_type("42"), int)

    def test_float(self):
        """Test float detection."""
        assert infer_type("3.14") == 3.14
        assert infer_type("-2.5") == -2.5
        assert infer_type("1e5") == 100000.0
        assert isinstance(infer_type("3.14"), float)

    def test_json_array(self):
        """Test JSON array parsing."""
        assert infer_type('["a", "b", "c"]') == ["a", "b", "c"]
        assert infer_type("[1, 2, 3]") == [1, 2, 3]
        assert infer_type("[]") == []

    def test_json_object(self):
        """Test JSON object parsing."""
        assert infer_type('{"key": "value"}') == {"key": "value"}
        assert infer_type('{"num": 42}') == {"num": 42}
        assert infer_type("{}") == {}

    def test_string_default(self):
        """Test that non-special strings remain strings."""
        assert infer_type("hello") == "hello"
        assert infer_type("data.csv") == "data.csv"
        assert infer_type("/path/to/file") == "/path/to/file"
        assert infer_type("true-but-not-boolean") == "true-but-not-boolean"

    def test_invalid_json_stays_string(self):
        """Test that invalid JSON stays as string."""
        assert infer_type("[invalid") == "[invalid"
        assert infer_type("{bad json}") == "{bad json}"


class TestParseWorkflowParams:
    """``name=value`` splitting — the CLI never guesses a workflow input's type."""

    def test_single_param(self):
        """Test parsing a single parameter."""
        result = parse_workflow_params(("input_file=data.csv",))
        assert result == {"input_file": "data.csv"}

    def test_no_params(self):
        """Test with no parameters."""
        assert parse_workflow_params(()) == {}
        assert parse_workflow_params(("no-equals-sign",)) == {}

    def test_every_value_stays_the_text_typed(self):
        """Typing is the declaration's job at the input boundary: a token that LOOKS typed arrives as
        its exact text (the #687 class — ``02134`` once arrived as ``2134``, ``TRUE`` as ``True``)."""
        tokens = ["02134", "1.10", "TRUE", "1e3", "42", "true", "[1, 2]", '{"a":1,"b":[1,2]}', "null", " 7 "]
        result = parse_workflow_params(tuple(f"v{i}={token}" for i, token in enumerate(tokens)))
        assert result == {f"v{i}": token for i, token in enumerate(tokens)}

    def test_empty_value(self):
        """Test parameter with empty value."""
        result = parse_workflow_params(("key=",))
        assert result == {"key": ""}

    def test_multiple_equals_signs(self):
        """Test parameter value containing equals sign."""
        result = parse_workflow_params(("expression=a=b+c",))
        assert result == {"expression": "a=b+c"}


class TestFormatParamValue:
    """Test the format_param_value function that converts Python values to CLI strings."""

    @pytest.mark.parametrize(
        "input_value,expected",
        [
            # Booleans - must be lowercase strings
            (True, "true"),
            (False, "false"),
            # Integers
            (0, "0"),
            (42, "42"),
            (-999, "-999"),
            (1234567890, "1234567890"),
            # Floats
            (3.14, "3.14"),
            (0.0, "0.0"),
            (-2.5, "-2.5"),
            (1.23e10, "12300000000.0"),  # Scientific notation converts to regular
            # Lists - compact JSON (no spaces)
            ([], "[]"),
            ([1], "[1]"),
            ([1, 2, 3], "[1,2,3]"),
            (["a", "b"], '["a","b"]'),
            ([True, False], "[true,false]"),  # Booleans in JSON are lowercase
            ([1, "two", 3.0], '[1,"two",3.0]'),
            # Dicts - compact JSON (no spaces after colons)
            ({}, "{}"),
            ({"key": "value"}, '{"key":"value"}'),
            ({"a": 1, "b": 2}, '{"a":1,"b":2}'),
            ({"nested": {"inner": "value"}}, '{"nested":{"inner":"value"}}'),
            ({"bool": True, "num": 42}, '{"bool":true,"num":42}'),
            # Strings - pass through as-is
            ("", ""),
            ("hello", "hello"),
            ("hello world", "hello world"),
            ("with\nnewlines", "with\nnewlines"),
            ('with "quotes"', 'with "quotes"'),
            ("with 'single' quotes", "with 'single' quotes"),
            ("special$chars&here;|", "special$chars&here;|"),
            ("path/to/file.txt", "path/to/file.txt"),
        ],
    )
    def test_type_conversions(self, input_value, expected):
        """Test that all Python types convert to correct CLI strings."""
        result = format_param_value(input_value)
        assert result == expected

    def test_none_handling(self):
        """Test that None values are handled (though typically filtered out)."""
        # None should fallback to string representation
        assert format_param_value(None) == "None"

    def test_unsupported_type_fallback(self):
        """Test that unsupported types fall back to str()."""

        class CustomObject:
            def __str__(self):
                return "custom_object"

        obj = CustomObject()
        assert format_param_value(obj) == "custom_object"


class TestIsLikelyWorkflowName:
    """Test workflow name detection heuristics."""

    def test_with_parameters(self):
        """Test that args with parameters are detected as workflow names."""
        assert is_likely_workflow_name("my-workflow", ("input=data.csv", "output=result"))
        assert is_likely_workflow_name("analyzer", ("file=test.txt",))
        # Permissive keys (hyphens, dots, leading digits) still count as parameters
        assert is_likely_workflow_name("analyzer", ("api-key=abc", "2fa.token=1"))
        # A token with no key before "=" is not a parameter
        assert not is_likely_workflow_name("node1", ("=>", "node2"))
        assert not is_likely_workflow_name("analyzer", ("=value",))

    def test_kebab_case(self):
        """Test that kebab-case names are detected."""
        assert is_likely_workflow_name("my-analyzer", ())
        assert is_likely_workflow_name("generate-report", ())
        assert is_likely_workflow_name("test-workflow-name", ())
        # But not if followed by flags
        assert not is_likely_workflow_name("read-file", ("--verbose",))

    def test_natural_language(self):
        """Test that natural language is not detected as workflow name."""
        assert not is_likely_workflow_name("analyze the data", ())
        assert not is_likely_workflow_name("create a report from csv", ())
        assert not is_likely_workflow_name("process this file", ())

    def test_excluded_starters(self):
        """Test that common command starters are excluded."""
        # Single words without params are not treated as workflow names anymore
        assert not is_likely_workflow_name("analyze", ())
        assert not is_likely_workflow_name("create", ())
        assert not is_likely_workflow_name("generate", ())
        assert not is_likely_workflow_name("process", ())

    def test_single_word_workflow(self):
        """Test single word that could be workflow name."""
        # Single words without kebab-case or params are NOT workflow names
        assert not is_likely_workflow_name("myworkflow", ())
        assert not is_likely_workflow_name("reporter", ())
        assert not is_likely_workflow_name("analyze", ())
        # But they are if they have params
        assert is_likely_workflow_name("myworkflow", ("input=data.csv",))
        assert is_likely_workflow_name("reporter", ("format=pdf",))

    def test_edge_cases(self):
        """Test edge cases."""
        # Empty string
        assert not is_likely_workflow_name("", ())
        # Very long string without spaces (unlikely workflow name)
        long_name = "a" * 60
        assert not is_likely_workflow_name(long_name, ())
        # With spaces never a workflow name
        assert not is_likely_workflow_name("has spaces", ("param=value",))

    def test_help_flag_handling(self):
        """Test that --help flag is allowed with workflow names."""
        # --help is special-cased to allow showing workflow help
        assert is_likely_workflow_name("my-workflow", ("--help",))
        assert is_likely_workflow_name("read-file", ("--help",))
        assert is_likely_workflow_name("test-workflow-name", ("--help",))

        # Other flags still indicate natural language
        assert not is_likely_workflow_name("my-workflow", ("--verbose",))
        assert not is_likely_workflow_name("my-workflow", ("--force",))

        # --help with other arguments
        assert is_likely_workflow_name("my-workflow", ("--help", "param=value"))


def _agent_call(model: str | None, estimate: float | None) -> dict:
    """An agent-backend llm_call record as the trace stores it (codex/claude backends)."""
    return {
        "model": model,
        "input_tokens": 1000,
        "output_tokens": 100,
        "cost_usd": None,
        "api_equivalent_cost_usd": estimate,
        "num_turns": 1,
    }


class TestCostLinesSubscriptionBilling:
    """The CLI cost line keeps paid / subscription / unpriced distinguishable (#634).

    Driven through ``MetricsCollector.get_summary`` so the metrics → formatter
    seam is exercised with the dict shape the runner actually produces.
    """

    @staticmethod
    def _lines(llm_calls: list[dict]) -> list[str]:
        from pflow.core.metrics import MetricsCollector

        summary = MetricsCollector().get_summary(llm_calls)
        return format_cost_summary_lines({"total_cost_usd": summary["total_cost_usd"], "metrics": summary["metrics"]})

    def test_agent_only_run_shows_labelled_estimate_not_missing_pricing(self) -> None:
        lines = self._lines([
            _agent_call("gpt-6-astra", 2.0),
            _agent_call("gpt-6-astra", 3.0),
            _agent_call("gpt-6-astra", 0.9507),
        ])

        assert lines == [
            "💰 Cost: subscription (3 agent calls) · API-equivalent: $5.9507",
            "   Total LLM calls: 3",
        ]

    def test_mixed_run_shows_paid_plus_subscription_and_api_equivalent_total(self) -> None:
        lines = self._lines([{"model": "gpt-4o", "cost_usd": 0.42}, _agent_call("gpt-6-astra", 5.95)])

        assert lines == [
            "💰 Cost: $0.4200 + subscription (1 agent call) · API-equivalent total: $6.3700",
            "   Total LLM calls: 2",
        ]

    def test_unpriced_api_model_keeps_the_missing_pricing_warning(self) -> None:
        lines = self._lines([{"model": "ollama/llama3.2", "cost_usd": None}])

        assert lines == [
            "⚠️  Cost unavailable — pricing data missing for: ollama/llama3.2 (1 call)",
            "   Total LLM calls: 1",
        ]

    def test_unpriced_api_model_beside_agent_calls_names_only_the_api_model(self) -> None:
        lines = self._lines([{"model": "ollama/llama3.2", "cost_usd": None}, _agent_call("gpt-6-astra", 1.0)])

        assert lines == [
            "⚠️  Cost unavailable — pricing data missing for: ollama/llama3.2 (1 call)",
            "   + subscription (1 agent call) · API-equivalent: $1.0000",
            "   Total LLM calls: 2",
        ]

    def test_agent_model_without_pricing_names_it_on_the_estimate(self) -> None:
        lines = self._lines([_agent_call("gpt-x", None)])

        assert lines[0] == "💰 Cost: subscription (1 agent call) · API-equivalent: unavailable for: gpt-x (1 call)"

    def test_partially_estimated_agent_calls_mark_the_estimate_partial(self) -> None:
        lines = self._lines([
            {"model": "gpt-4o", "cost_usd": 0.42},
            _agent_call("gpt-6-astra", 1.0),
            _agent_call("gpt-x", None),
        ])

        # No API-equivalent *total* when part of it is unknown.
        assert lines[0] == (
            "💰 Cost: $0.4200 + subscription (2 agent calls) · "
            "API-equivalent: $1.0000+ (partial — unavailable for: gpt-x (1 call))"
        )

"""One declared input, every surface that tells a caller how to supply it (#804).

``types.input_usage`` reads a ``## Inputs`` declaration the way a run treats it; every
surface renders from it. These tests pin (1) the helper to what ``prepare_inputs`` does and
(2) each surface to the helper, for every declared type and every way an input can be
required or optional — present where it must be, absent where it must not be.
"""

from __future__ import annotations

from typing import Any

import pytest

from pflow.core.prompt_cache_analysis.stages.summary import _format_workflow_run_command
from pflow.core.types import CANONICAL_TYPES, input_usage
from pflow.core.workflow.context import _build_workflow_entry
from pflow.core.workflow.graph.build import build_graph
from pflow.core.workflow.skill_service import generate_usage_section
from pflow.core.workflow.validator import WorkflowValidator
from pflow.execution.formatters.discovery_formatter import format_discovery_result
from pflow.execution.formatters.workflow_describe_formatter import format_workflow_interface
from pflow.execution.formatters.workflow_save_formatter import format_execution_hint, format_save_success
from pflow.registry.context_builder import _format_workflow_inputs
from pflow.runtime.compilation.ir_preparation import prepare_inputs
from pflow.runtime.template_validation.path_validation import _get_input_description

NAME = "probe_in"  # an input name no test environment sets

# What a caller types after `name=` — written out, never read from production code.
_PLACEHOLDERS: dict[str, str] = {
    "string": "<string>",
    "integer": "<integer>",
    "number": "<number>",
    "boolean": "<true/false>",
    "array": "'[...]'",
    "object": "'{...}'",
    "any": "<value>",
}

# A default each type accepts, and that default as a caller types it.
_DEFAULTS: dict[str, tuple[Any, str]] = {
    "string": ("a b", "a b"),
    "integer": (2, "2"),
    "number": (2.5, "2.5"),
    "boolean": (False, "false"),
    "array": ([1], "[1]"),
    "object": ({"k": True}, '{"k": true}'),
    "any": ("a", "a"),
}

# (case, spec builder, required?) — every way a declaration is required or optional.
_SHAPES: list[tuple[str, Any, bool]] = [
    ("required (implicit)", lambda t: {}, True),
    ("required: true", lambda t: {"required": True}, True),
    ("default, no required line", lambda t: {"default": _DEFAULTS[t][0]}, False),
    ("required: true + default", lambda t: {"required": True, "default": _DEFAULTS[t][0]}, False),
    ("default: null", lambda t: {"default": None}, True),
    ("required: false", lambda t: {"required": False}, False),
    ("stdin", lambda t: {"stdin": True}, True),
]


def _declared(type_name: str | None, extra: dict[str, Any]) -> dict[str, Any]:
    spec: dict[str, Any] = {"description": "The probe.", **extra}
    if type_name is not None:
        spec["type"] = type_name
    return spec


def _cases() -> list[Any]:
    cases = []
    for type_name in [*CANONICAL_TYPES, None]:
        for label, build, required in _SHAPES:
            shown = type_name or "any"
            spec = _declared(type_name, build(shown))
            cases.append(pytest.param(spec, shown, required, id=f"{type_name or 'untyped'}-{label}"))
    return cases


def _missing_input_errors(spec: dict[str, Any], **caller: Any) -> list[Any]:
    errors, _, _ = prepare_inputs({"inputs": {NAME: spec}}, {}, {}, **caller)
    return errors


class TestTheHelperIsTheRunsRule:
    """``required`` is what ``prepare_inputs`` does with an omitted input — not the ``required:`` key."""

    def test_an_empty_default_is_still_required_because_the_run_rejects_it(self) -> None:
        spec = _declared("string", {"default": ""})
        assert input_usage(spec).required is True
        assert input_usage(spec).default == '""'
        [error] = _missing_input_errors(spec)
        assert error.message == f"Required input '{NAME}' is empty (resolved from default): The probe."

    def test_an_empty_value_for_an_input_its_default_makes_optional_is_not_called_required(self) -> None:
        """Leaving it out is fine (its default fills it); passing it empty is not — and the message
        must not contradict every surface that labels it optional."""
        spec = _declared("string", {"default": "hello"})
        assert input_usage(spec).required is False
        errors, _, _ = prepare_inputs({"inputs": {NAME: spec}}, {NAME: ""}, {})
        assert [(e.message, e.suggestions) for e in errors] == [
            (
                f"Input '{NAME}' is empty: The probe.",
                ["Provide a non-empty value, or leave it out to use its default"],
            )
        ]

    def test_at_a_sub_workflow_boundary_an_empty_default_does_not_open_the_settings_fallback(self) -> None:
        """The child boundary reads the same rule: a required input whose default the run rejects
        comes from the parent, never from settings — as the validator rules statically."""
        spec = _declared("string", {"default": ""})
        errors, updates, _ = prepare_inputs({"inputs": {NAME: spec}}, {}, {NAME: "from-settings"}, step="call")
        assert updates == {}
        assert [e.message for e in errors] == [f"The sub-workflow requires input '{NAME}': The probe."]
        assert errors[0].suggestions[0].startswith("Pass it under step 'call' `inputs:`")

        validator_errors = WorkflowValidator._check_required_inputs("call", "./child.pflow.md", {}, {NAME: spec})
        assert [e.message for e in validator_errors] == [
            f"Step 'call': sub-workflow './child.pflow.md' requires input '{NAME}' but it is not provided."
        ]


class TestEverySurfaceAgrees:
    """Each surface shows the declared type's placeholder, and lists, labels or omits the input by one rule."""

    @pytest.mark.parametrize(("spec", "type_name", "required"), _cases())
    def test_every_surface_renders_the_input_from_the_one_rule(
        self, spec: dict[str, Any], type_name: str, required: bool, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        ir: dict[str, Any] = {"inputs": {NAME: spec}, "nodes": [{"id": "work", "type": "shell"}], "edges": []}
        assert input_usage(spec).required is required
        placeholder = _PLACEHOLDERS[type_name]
        argument = f"{NAME}={placeholder}"
        status = "required" if required else "optional"
        stdin = " [stdin]" if spec.get("stdin") else ""
        default = spec.get("default")
        default_text = None if default is None else _DEFAULTS[type_name][1]

        # describe / `--help` / MCP describe — label line, default line, example command
        describe = format_workflow_interface("wf", {"ir": ir, "description": "d"})
        assert f"  - {NAME}{stdin} ({type_name}, {status}): The probe." in describe
        assert (f"    Default: {default_text}" in describe) is (default_text is not None)
        assert describe.endswith(f"  pflow wf {argument}" if required else "  pflow wf")

        # save — every input in the command; "Optional params" names the optional ones
        assert format_execution_hint("wf", ir) == f"pflow wf {argument}"
        assert (f"Optional params: {NAME}" in format_save_success("wf", "/p", ir)) is not required

        # skill Usage section — the required inputs only
        usage = generate_usage_section("wf", ir)
        assert (f"pflow wf {argument}\n" if required else "pflow wf\n") in usage
        assert (NAME in usage) is required

        # find — label line and the "Run it" command
        found = format_discovery_result({"workflow_name": "wf", "confidence": 1.0}, {"ir": ir})
        assert f"  - {NAME}: {type_name} ({status}) - The probe." in found
        assert found.endswith(f"  pflow wf {argument}" if required else "  pflow wf")

        # LLM discovery context and component context
        entry = _build_workflow_entry(1, {"name": "wf", "ir": ir})
        assert (f"**Inputs:** {NAME}" in entry) is required
        assert (f"**Optional:** {NAME}" in entry) is not required
        component = "\n".join(_format_workflow_inputs({"ir": ir}))
        assert f"- `{NAME}: {type_name}` - The probe." in component
        assert ("(optional" in component) is not required
        assert (f"default: {default_text})" in component) is (not required and default_text is not None)

        # template-error hint
        hint = _get_input_description(NAME, ir)
        assert ("(required)" in hint) is required
        assert (f"(optional, default: {default_text})" in hint) is (not required and default_text is not None)

        # the graph the web UI's run form and canvas read
        [port] = [n.io for n in build_graph(ir).nodes if n.kind == "input"]
        assert port is not None and port.required is required

        # analyze-cache's suggested command
        assert _format_workflow_run_command("/w.pflow.md", ir["inputs"]) == f"pflow run /w.pflow.md {argument}"

        # the run: an omitted input fails exactly when the helper says required, and its remedy
        # names the same argument
        monkeypatch.delenv(NAME, raising=False)
        errors = _missing_input_errors(spec)
        if required:
            passed = f"Pipe it on stdin or pass {argument}" if stdin else f"Pass {argument}"
            assert [e.suggestions for e in errors] == [
                [
                    f"{passed} — or set the name '{NAME}' in the shell environment, "
                    f"or once with: pflow settings set-env {NAME} {placeholder}"
                ]
            ]
        else:
            assert errors == []


def test_a_scalar_default_on_a_string_input_shows_as_the_text_the_run_receives() -> None:
    """`default: false` on a `string` input reaches the run as "False" — typing `false` would not."""
    ir: dict[str, Any] = {"inputs": {"flag": {"type": "string", "default": False}}, "nodes": []}
    _, updates, _ = prepare_inputs(ir, {}, {})
    assert updates == {"flag": "False"}
    assert "    Default: False\n" in format_workflow_interface("wf", {"ir": ir})


def test_required_inputs_come_first_and_optional_ones_only_where_every_input_is_listed() -> None:
    inputs = {
        "opt": {"type": "integer", "required": False},
        "req": {"type": "array"},
        "dflt": {"type": "boolean", "default": True},
    }
    ir: dict[str, Any] = {"inputs": inputs, "nodes": []}
    assert format_execution_hint("wf", ir) == "pflow wf req='[...]' opt=<integer> dflt=<true/false>"
    assert _format_workflow_run_command("/w.pflow.md", inputs) == (
        "pflow run /w.pflow.md req='[...]' opt=<integer> dflt=<true/false>"
    )
    assert format_workflow_interface("wf", {"ir": ir}).endswith("  pflow wf req='[...]'")

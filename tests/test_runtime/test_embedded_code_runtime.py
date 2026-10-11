"""Embedded code at run time (Task 181): what the MCP tool receives, and what a miss says.

The tool receives the param's source text with each JSON insert ``${x|json}`` replaced by
a JSON literal; a bare ``${…}`` and ``$${`` are sent as written. Every row goes through the
engine's own resolver (``compile_workflow`` → ``resolve_templates``) or a full run with the
MCP call stubbed at the connection boundary (``tests/shared/mcp_tool.py``).
"""

from __future__ import annotations

from typing import Any

import pytest

from pflow.execution.result import RunnerConfig
from pflow.execution.runner import WorkflowRunner
from pflow.registry import Registry
from pflow.runtime import compile_workflow
from pflow.runtime.engine.template_resolution import resolve_templates
from tests.shared.mcp_tool import register_mcp_tool, stub_mcp_calls


@pytest.fixture
def tool() -> str:
    """``mcp-chrome-devtools-evaluate_script``: ``function`` is embedded code, ``label`` a Template."""
    return register_mcp_tool("chrome-devtools", "evaluate_script", {"function": "str", "label": "str"})


def _ir(tool: str, *, mode: str = "strict", **params: Any) -> dict[str, Any]:
    ir: dict[str, Any] = {
        "ir_version": "0.1.0",
        "nodes": [
            {"id": "up", "type": "shell", "params": {"command": "echo hi"}},
            {"id": "s", "type": tool, "params": params},
        ],
        "edges": [{"from": "up", "to": "s"}],
    }
    if mode != "strict":
        ir["template_resolution_mode"] = mode
    return ir


def _config(ir: dict[str, Any]) -> Any:
    return compile_workflow(ir, Registry()).node_configs["s"].template_config


UP = {"up": {"stdout": "hi\n", "stderr": "", "exit_code": 0, "data": {"a": [1, 2]}}}


def test_the_tool_receives_the_source_with_each_insert_replaced(tool: str) -> None:
    function = "() => [${up.stdout|json}, ${up.exit_code|json}, `${a + b}`, `$${price}`, `${up.stdout}`]"
    merged, resolutions, errors = resolve_templates(_config(_ir(tool, function=function)), dict(UP), "s")
    sent = '() => ["hi\\n", 0, `${a + b}`, `$${price}`, `${up.stdout}`]'
    assert (merged["function"], errors) == (sent, [])
    assert resolutions["function"] == {"template": function, "resolved": sent}


def test_bare_javascript_routes_static_with_its_escape_intact(tool: str) -> None:
    config = _config(_ir(tool, function="() => `${a} $${b} ${up.stdout}`", label="${up.stdout}"))
    assert config.static_params["function"] == "() => `${a} $${b} ${up.stdout}`"
    assert set(config.template_params) == {"label"}  # presence: a Template beside it still resolves


def test_a_whole_value_insert_is_json_text_never_auto_parsed(tool: str) -> None:
    """Even with a container-typed param, a JSON insert's text is never parsed back
    (the simple-template auto-parse never applies: an insert is never simple)."""
    tool = register_mcp_tool("chrome-devtools", "evaluate_script", {"function": "dict"})
    merged, _, _ = resolve_templates(_config(_ir(tool, function="${up.data|json}")), dict(UP), "s")
    assert merged["function"] == '{"a": [1, 2]}'


def _strict_failure(tool: str, **params: Any) -> str:
    with pytest.raises(ValueError) as caught:
        resolve_templates(_config(_ir(tool, **params)), dict(UP), "s")
    return str(caught.value)


def test_an_unresolved_insert_names_itself_and_its_fix_as_an_insert(tool: str) -> None:
    message = _strict_failure(tool, function="() => ${up.stdot|json}")
    assert "Unresolved variables in parameter 'function': ${up.stdot|json}" in message
    assert "Did you mean: ${up.stdout|json}" in message
    # Presence pair: the same miss in a Template param is written bare, and so is its fix.
    bare = _strict_failure(tool, function="() => 1", label="${up.stdot}")
    assert "Unresolved variables in parameter 'label': ${up.stdot}" in bare
    assert "Did you mean: ${up.stdout}" in bare
    assert "|json" not in bare


def test_a_coalesce_fix_puts_the_suffix_at_the_end_of_the_chain(tool: str) -> None:
    message = _strict_failure(tool, function="() => ${g1.out ?? g2.out|json}")
    assert "Add another fallback: ${g1.out ?? g2.out ?? <another-node>.out|json}" in message
    assert "|json ??" not in message


def test_permissive_mode_records_the_miss_and_the_step_runs(tool: str) -> None:
    merged, _, errors = resolve_templates(
        _config(_ir(tool, mode="permissive", function="() => ${up.stdot|json}")), dict(UP), "s"
    )
    assert merged["function"] == "() => ${up.stdot|json}"
    assert [e["unresolved_expressions"] for e in errors] == [("up.stdot|json",)]


def test_each_batch_item_is_inserted_into_its_own_call(tool: str) -> None:
    """Through the engine's per-item resolution, with MCPNode stubbed at the pool."""
    ir = _ir(tool, function="() => [${item|json}, `${i}`]")
    ir["nodes"][1]["batch"] = {"items": ["Don't", "x"]}
    with stub_mcp_calls() as calls:
        result = WorkflowRunner().run(ir, {}, RunnerConfig(cache_enabled=False, trace_enabled=False))
    assert result.success, [d.message for d in result.errors]
    assert sorted(call["function"] for call in calls) == ['() => ["Don\'t", `${i}`]', '() => ["x", `${i}`]']


def test_dry_run_plans_an_embedded_step_without_a_template_error(tool: str) -> None:
    """The planner resolves the step like the engine: JavaScript's ``${a}`` is no miss."""
    ir = {
        "ir_version": "0.1.0",
        "inputs": {"title": {"type": "string", "required": True}},
        "nodes": [{"id": "s", "type": tool, "params": {"function": "() => [${title|json}, `${a}`]"}}],
        "edges": [],
    }
    plan = WorkflowRunner().plan(ir, {"title": "T"}, RunnerConfig(cache_enabled=False, trace_enabled=False))
    assert [(entry.node_id, entry.status, entry.diagnostic) for entry in plan.entries] == [("s", "execute", None)]
    assert plan.diagnostics == []


def _dynamic_child_run(tool: str, tmp_path: Any, function: str) -> tuple[Any, list[dict[str, Any]]]:
    """A parent that picks its child at run time (``workflow: ${which}``) — the child is
    never seen by the parent's validation, only by the compiler's data-flow check."""
    child = tmp_path / "child.pflow.md"
    child.write_text(
        "# Child\n\nEvaluate.\n\n## Inputs\n\n### selector\n\nA selector.\n\n- type: string\n- required: true\n\n"
        f"## Steps\n\n### probe\n\nEvaluate it.\n\n- type: {tool}\n- function: {function}\n",
        encoding="utf-8",
    )
    string_input = {"type": "string", "required": True, "description": "An input."}
    parent = {
        "ir_version": "0.1.0",
        "inputs": {"selector": string_input, "which": string_input},
        "nodes": [
            {
                "id": "call",
                "type": "workflow",
                "params": {"workflow": "${which}", "inputs": {"selector": "${selector}"}},
            }
        ],
        "edges": [],
    }
    with stub_mcp_calls() as calls:
        result = WorkflowRunner().run(
            parent, {"selector": "#main", "which": str(child)}, RunnerConfig(cache_enabled=False, trace_enabled=False)
        )
    return result, calls


def test_a_dynamic_child_with_an_input_used_only_bare_fails_before_the_tool_is_called(tool: str, tmp_path: Any) -> None:
    """A child chosen at run time skips template validation; data flow, which the compiler
    runs, owns the §4a ERROR — so the stale ``'${selector}'`` is never sent as JavaScript."""
    result, calls = _dynamic_child_run(tool, tmp_path, "() => { const sel = '${selector}'; return sel; }")
    assert not result.success
    assert calls == []
    assert [(error.node_id, error.message) for error in result.errors] == [
        (
            "probe",
            "Input 'selector' is never inserted: its only use, '${selector}' in 'function', is JavaScript text "
            "that pflow sends to the MCP tool unchanged.",
        )
    ]
    # Presence pair: the converted child runs and the tool receives the inserted value.
    result, calls = _dynamic_child_run(tool, tmp_path, "() => { const sel = ${selector|json}; return sel; }")
    assert result.success, [error.message for error in result.errors]
    assert [call["function"] for call in calls] == ['() => { const sel = "#main"; return sel; }']

"""Every consumer that reads a param's ``${…}`` reads embedded code through its view (Task 181).

Embedded code is JavaScript an MCP tool runs (``template_surfaces.param_mode`` →
``"embedded"``): a bare ``${…}`` there is JavaScript, only a JSON insert ``${x|json}`` is
pflow's. One row per consumer, each through its own entry point: the row puts a bare
reference the consumer WOULD act on into ``function`` (it must not), then the same
reference as an insert (it must — the presence half, proving the row's input is one the
consumer reports at all). Mutation ledger: dropping the view at a row's site turns that
row red (recorded in the task log).
"""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any
from unittest.mock import Mock

import pytest

from pflow.core.diagnostic import Diagnostic
from pflow.core.workflow.data_flow import validate_data_flow
from pflow.core.workflow.graph.build import build_graph
from pflow.core.workflow.graph.model import EdgeKind
from pflow.core.workflow.graph.renderers.react_flow import render_react_flow
from pflow.core.workflow.template_surfaces import param_mode
from pflow.mcp_server.services.execution_service import ExecutionService
from pflow.registry import Registry
from pflow.runtime.template_validation import validate_workflow_templates
from tests.shared.mcp_tool import register_mcp_tool, stub_mcp_calls

EVAL = "mcp-chrome-devtools-evaluate_script"


@pytest.mark.parametrize(
    ("node_type", "key", "mode"),
    [
        (EVAL, "function", "embedded"),
        ("mcp-chrome-devtools-isolated-evaluate_script", "function", "embedded"),  # a hyphenated server
        ("mcp-chrome-devtools-navigate_page", "initScript", "embedded"),
        ("mcp-playwright-browser_evaluate", "function", "embedded"),
        ("mcp-playwright-browser_run_code_unsafe", "code", "embedded"),
        (EVAL, "args", "template"),  # another param of the same tool
        ("mcp-x-evaluate_scripts", "function", "template"),  # a suffix, not a substring
        ("evaluate_script", "function", "template"),  # not an MCP type
        ("mcp-chrome-devtools-navigate_page", "function", "template"),  # the pair, not the param name
        ("shell", "function", "template"),
        (None, "function", "template"),
        ("shell", "command", "body"),
    ],
)
def test_param_mode_reads_embedded_code_by_tool_suffix_and_param(node_type: str | None, key: str, mode: str) -> None:
    assert param_mode(node_type, key) == mode


@pytest.fixture
def registry() -> Registry:
    """The isolated test registry (function scope: built after ``isolate_pflow_config``)."""
    reg = Registry()
    reg.load()
    return reg


def _up_and_eval(function: str, *, node_type: str = EVAL, **step: Any) -> dict[str, Any]:
    """``up`` (a shell step) → ``s`` (an evaluate_script step whose ``function`` is the row's)."""
    return {
        "ir_version": "0.1.0",
        "nodes": [
            {"id": "up", "type": "shell", "params": {"command": "echo hi"}},
            {"id": "s", "type": node_type, "params": {"function": function}, **step},
        ],
        "edges": [{"from": "up", "to": "s"}],
    }


def _messages(diagnostics: list[Diagnostic], needle: str) -> list[str]:
    return [d.message for d in diagnostics if needle in d.message]


# ── one function per consumer: (bare run, insert run) → assertions ─────────


def _data_flow(_registry: Registry) -> None:
    needle = "non-existent node 'ghost'"
    assert _messages(validate_data_flow(_up_and_eval("() => ${ghost.x}")), needle) == []
    assert len(_messages(validate_data_flow(_up_and_eval("() => ${ghost.x|json}")), needle)) == 1


def _pass_5(registry: Registry) -> None:
    needle = "does not output 'nope'"
    assert _messages(validate_workflow_templates(_up_and_eval("() => ${up.nope}"), {}, registry), needle) == []
    insert = validate_workflow_templates(_up_and_eval("() => ${up.nope|json}"), {}, registry)
    assert len(_messages(insert, needle)) == 1


def _pass_8(_registry: Registry) -> None:
    llm = {
        "interface": {
            "inputs": [{"key": "prompt", "type": "str", "description": "prompt"}],
            "outputs": [{"key": "response", "type": "str", "description": "response"}],
            "params": [],
            "actions": ["default"],
        }
    }
    tool = {
        "interface": {
            "inputs": [],
            "outputs": [{"key": "result", "type": "any", "description": "r"}],
            "params": [{"key": "function", "type": "str"}],
            "actions": ["default"],
        }
    }
    mock = Mock()
    mock.get_nodes_metadata = Mock(side_effect=lambda types: {t: {"llm": llm, EVAL: tool}[t] for t in types})

    def ir(function: str) -> dict[str, Any]:
        return {
            "inputs": {"data": {"type": "array", "required": True}},
            "nodes": [
                {"id": "process", "type": "llm", "batch": {"items": "${data}"}, "params": {"prompt": "P ${item}"}},
                {"id": "s", "type": EVAL, "batch": {"items": "${process.results}"}, "params": {"function": function}},
            ],
            "edges": [{"from": "process", "to": "s"}],
        }

    needle = "not available on batch items"
    assert _messages(validate_workflow_templates(ir("() => ${item.nope}"), {"data": ["a"]}, mock), needle) == []
    insert = validate_workflow_templates(ir("() => ${item.nope|json}"), {"data": ["a"]}, mock)
    assert len(_messages(insert, needle)) == 1


def _issue_pass(registry: Registry) -> None:
    needle = "Malformed template"
    assert _messages(validate_workflow_templates(_up_and_eval("() => `${a + b}`"), {}, registry), needle) == []
    prompt = _up_and_eval("x", node_type="llm")
    prompt["nodes"][1]["params"] = {"prompt": "`${a + b}`"}
    assert len(_messages(validate_workflow_templates(prompt, {}, registry), needle)) == 1


def _pass_6(_registry: Registry) -> None:
    """No real output type trips a ``str`` param, so a mock declares ``function: int`` on
    the embedded tool and on a same-shaped tool whose ``function`` is a Template."""
    tool = {
        "interface": {
            "inputs": [],
            "outputs": [{"key": "result", "type": "any", "description": "r"}],
            "params": [{"key": "function", "type": "int"}],
            "actions": ["default"],
        }
    }
    shell = {
        "interface": {
            "inputs": [],
            "outputs": [{"key": "stdout", "type": "str", "description": "out"}],
            "params": [{"key": "command", "type": "str"}],
            "actions": ["default"],
        }
    }
    other = "mcp-chrome-devtools-other_tool"
    metadata = {"shell": shell, EVAL: tool, other: tool}
    mock = Mock()
    mock.get_nodes_metadata = Mock(side_effect=lambda types: {t: metadata[t] for t in types if t in metadata})
    needle = "Type mismatch"
    embedded = validate_workflow_templates(_up_and_eval("${up.stdout|json}"), {}, mock)
    assert _messages(embedded, needle) == []
    template = validate_workflow_templates(_up_and_eval("${up.stdout}", node_type=other), {}, mock)
    assert len(_messages(template, needle)) == 1


def _graph_build(_registry: Registry) -> None:
    def edges(function: str) -> list[tuple[str, str, str | None]]:
        graph = build_graph(_up_and_eval(function))
        return [
            (edge.source.node_id, edge.target.node_id, edge.input_name)
            for edge in graph.edges
            if edge.kind is EdgeKind.DATA_FLOW
        ]

    assert edges("() => `${up.stdout}`") == []
    assert edges("() => ${up.stdout|json}") == [("up", "s", "function")]


def _canvas(_registry: Registry) -> None:
    def param(function: str) -> tuple[bool, str]:
        rendered = render_react_flow(build_graph(_up_and_eval(function)))
        [node] = [node for node in rendered.nodes if node.ref.node_id == "s"]
        [fn] = [p for p in node.params if p.name == "function"]
        return fn.is_dynamic, fn.mode

    assert param("() => `${up.stdout}`") == (False, "embedded")
    assert param("() => ${up.stdout|json}") == (True, "embedded")


def _mcp_expansion(_registry: Registry) -> None:
    """``registry_run`` expands ``${ENV}`` in params — never in embedded code, whose ``${…}``
    is JavaScript (a missing variable there would refuse the run)."""
    node_type = register_mcp_tool("chrome-devtools", "evaluate_script", {"function": "str", "label": "str"})
    os.environ["PFLOW_TEST_X"] = "expanded"
    try:
        with stub_mcp_calls() as calls:
            ExecutionService.run_registry_node(
                node_type, {"function": "() => `${a} ${PFLOW_TEST_X}`", "label": "${PFLOW_TEST_X}"}
            )
    finally:
        del os.environ["PFLOW_TEST_X"]
    assert [(call["function"], call["label"]) for call in calls] == [("() => `${a} ${PFLOW_TEST_X}`", "expanded")]


CONSUMERS: list[tuple[str, Callable[[Registry], None]]] = [
    ("data_flow", _data_flow),
    ("pass_5", _pass_5),
    ("pass_8", _pass_8),
    ("issue_pass", _issue_pass),
    ("pass_6", _pass_6),
    ("graph_build", _graph_build),
    ("canvas", _canvas),
    ("mcp_expansion", _mcp_expansion),
]


@pytest.mark.parametrize("check", [pytest.param(fn, id=name) for name, fn in CONSUMERS])
def test_consumer_reads_only_json_inserts_in_embedded_code(
    check: Callable[[Registry], None], registry: Registry
) -> None:
    check(registry)


# Where an agent reads a tool's interface before writing a step: `pflow mcp describe` and the
# discovery/MCP-server component context. Embedded code shows how it reads and a snippet
# with a JSON insert; the same tool's other params keep the plain reference.
_NOTE = "(JavaScript, sent as written; insert a pflow value as ${x|json})"


def test_mcp_describe_shows_embedded_code_with_a_json_insert() -> None:
    from click.testing import CliRunner

    from pflow.cli.commands.mcp import mcp

    node_type = register_mcp_tool(
        "chrome-devtools", "evaluate_script", {"pageId": "int", "function": "str", "label": "str"}
    )
    result = CliRunner().invoke(mcp, ["describe", node_type])

    assert result.exit_code == 0, result.output
    lines = result.output.splitlines()
    assert f"  - function: str (required) {_NOTE} - function" in lines
    assert "  - label: str (required) - label" in lines
    assert "    - function: () => ${previous-step.response|json}" in lines
    assert "    - label: ${previous-step.response}" in lines


def test_component_context_shows_embedded_code_with_a_json_insert() -> None:
    from pflow.registry.context_builder import build_component_context

    node_type = register_mcp_tool(
        "chrome-devtools", "evaluate_script", {"pageId": "int", "function": "str", "label": "str"}
    )
    context = build_component_context([node_type], [], Registry().load(), saved_workflows=[])

    assert isinstance(context, str)
    lines = context.splitlines()
    assert f"- `function: str` {_NOTE} - function" in lines
    assert "- `label: str` - label" in lines
    assert "    - function: () => ${previous-step.response|json}" in lines
    assert "    - label: ${previous-step.response}" in lines

"""What the validator says about embedded code and JSON inserts (Task 181, ADR-0016).

Embedded code is JavaScript an MCP tool runs: a bare ``${…}`` there is JavaScript, a pflow
value enters only as ``${x|json}``. The validator reports:
- a JSON insert anywhere else (an ERROR naming where it is accepted);
- an insert the embedded view cannot see — inside ``$${…}`` or a JavaScript ``${…}`` —
  and a near-miss spelling (ERRORs: either reaches the tool as text);
- a bare pflow name in embedded code: an ERROR when it is a workflow input used nowhere
  else (in place of the unused-input error), else one WARNING per param;
- an insert left inside quotes (a WARNING).

Messages are the ruled text of the task's diagnostics checkpoint, plus the 2026-10-11
rulings on the variants it did not enumerate (progress log).
"""

from __future__ import annotations

import logging
from itertools import pairwise
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner, Result

from pflow.cli.main import main
from pflow.core.diagnostic import Diagnostic, Severity
from pflow.core.workflow.validator import WorkflowValidator
from pflow.registry import Registry
from tests.shared.mcp_tool import register_mcp_tool

EVAL = "mcp-chrome-devtools-evaluate_script"
PLACES = (
    "the 'function' param of an mcp-<server>-evaluate_script or mcp-<server>-browser_evaluate step, "
    "'initScript' of mcp-<server>-navigate_page, 'code' of mcp-<server>-browser_run_code_unsafe"
)
JS_VALUE_PLACE = "where a JavaScript value goes, outside any quotes or `…`"


@pytest.fixture(autouse=True)
def embedded_tool() -> str:
    return register_mcp_tool("chrome-devtools", "evaluate_script", {"function": "str"})


def _string_input() -> dict[str, Any]:
    return {"type": "string", "required": True, "description": "An input."}


def _ir(*nodes: dict[str, Any], inputs: tuple[str, ...] = (), **extra: Any) -> dict[str, Any]:
    return {
        "ir_version": "0.1.0",
        "inputs": {name: _string_input() for name in inputs},
        "nodes": list(nodes),
        "edges": [{"from": a["id"], "to": b["id"]} for a, b in pairwise(nodes)],
        **extra,
    }


def _eval(node_id: str, function: str, **extra: Any) -> dict[str, Any]:
    return {"id": node_id, "type": EVAL, "params": {"function": function}, **extra}


def _validate(ir: dict[str, Any]) -> list[Diagnostic]:
    params = dict.fromkeys(ir.get("inputs", {}), "v")
    return WorkflowValidator.validate(ir, extracted_params=params, registry=Registry())


def _errors(diagnostics: list[Diagnostic]) -> list[Diagnostic]:
    return [d for d in diagnostics if d.severity is Severity.ERROR]


def _warnings(diagnostics: list[Diagnostic]) -> list[Diagnostic]:
    return [d for d in diagnostics if d.severity is Severity.WARNING]


def _only_error(ir: dict[str, Any]) -> Diagnostic:
    [error] = _errors(_validate(ir))
    return error


def _cli(tmp_path: Path, markdown: str, *args: str) -> Result:
    path = tmp_path / "probe.pflow.md"
    path.write_text(markdown, encoding="utf-8")
    return CliRunner(mix_stderr=False).invoke(main, ["--validate-only", *args, str(path)])


def _markdown(steps: str, inputs: tuple[str, ...] = (), extra: str = "") -> str:
    declared = "".join(f"### {name}\n\nAn input.\n\n- type: string\n- required: true\n\n" for name in inputs)
    inputs_section = f"## Inputs\n\n{declared}" if inputs else ""
    return f"# Probe\n\nA probe.\n\n{inputs_section}## Steps\n\n{steps}\n{extra}"


# ── §5: a JSON insert outside embedded code ────────────────────────────────


def _misplaced(written: str, fix: str) -> tuple[str, list[str]]:
    message = f"{written} is accepted only in JavaScript passed to an MCP tool: {PLACES}."
    return message, [f"Remove '|json': write {fix}. A dict or list is already inserted as JSON text."]


@pytest.mark.parametrize(
    ("ir", "path"),
    [
        (
            _ir({"id": "ask", "type": "llm", "params": {"prompt": "Echo ${x|json}"}}, inputs=("x",)),
            "nodes[id=ask].params.prompt",
        ),
        (
            _ir(
                {"id": "ask", "type": "llm", "batch": {"items": "${x|json}"}, "params": {"prompt": "${item}"}},
                inputs=("x",),
            ),
            "nodes[id=ask].batch.items",
        ),
        (
            _ir(
                {
                    "id": "poll",
                    "type": "shell",
                    "params": {"command": "echo"},
                    "loop": {"while": "${x|json}", "max_iterations": 3},
                },
                inputs=("x",),
            ),
            "nodes[id=poll].loop.while",
        ),
        (
            _ir(
                {"id": "s", "type": "shell", "params": {"command": "echo"}},
                inputs=("x",),
                outputs={"o": {"source": "${x|json}", "description": "Out."}},
            ),
            "outputs.o.source",
        ),
    ],
    ids=["param", "batch-items", "loop-while", "output-source"],
)
def test_a_json_insert_outside_embedded_code_is_the_one_error(ir: dict[str, Any], path: str) -> None:
    """Each the only ERROR: the Issue pass returns early, so a loop condition gets no
    loop-shape error beside it (as for any Issue there)."""
    error = _only_error(ir)
    assert (error.message, error.suggestions) == _misplaced("${x|json}", "${x}")
    assert error.context["path"] == path


def test_a_bare_output_source_insert_gets_one_error_written_bare() -> None:
    ir = _ir(
        {"id": "s", "type": "shell", "params": {"command": "echo"}},
        inputs=("x",),
        outputs={"o": {"source": "x|json", "description": "Out."}},
    )
    error = _only_error(ir)  # never also "non-existent source 'x|json'"
    assert (error.message, error.suggestions) == _misplaced("${x|json}", "x")
    assert error.context["path"] == "outputs.o.source"


def test_a_bare_coalesce_output_source_names_real_roots() -> None:
    """The bare branch reads roots from the parse: ``x ?? s.stdout`` is valid, a typo is named."""

    def source(text: str) -> list[str]:
        ir = _ir(
            {"id": "s", "type": "shell", "params": {"command": "echo"}},
            inputs=("x",),
            outputs={"o": {"source": text, "description": "Out."}},
        )
        return [e.message for e in _errors(_validate(ir))]

    assert source("x ?? s.stdout") == []
    assert source("x ?? ghost.stdout") == ["Output 'o' references non-existent source 'ghost'."]


def test_the_fix_strips_the_suffix_from_a_coalesce() -> None:
    ir = _ir({"id": "ask", "type": "llm", "params": {"prompt": '${x ?? "d" | json}'}}, inputs=("x",))
    assert _only_error(ir).suggestions == _misplaced("", '${x ?? "d"}')[1]


def test_a_cache_var_insert_is_the_error(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    steps = "### ask\n\nAsk.\n\n- type: llm\n- prompt: hi\n- prompt_cache: [x|json]\n"
    cache = "## Cache\n\n```cache\nContext: ${x|json}\n```\n"
    caplog.set_level(logging.ERROR, logger="pflow.runtime.template_validation.validator")
    result = _cli(tmp_path, _markdown(steps, inputs=("x",), extra=cache))
    assert result.exit_code == 2
    assert "Found 1 template error(s)" in caplog.messages  # no longer "malformed": it counts placement too
    assert f"${{x|json}} is accepted only in JavaScript passed to an MCP tool: {PLACES}." in result.stdout
    assert "At: cache.items[name=x|json].var" in result.stdout


# ── §7: inserts the embedded view cannot see ───────────────────────────────

_7A_FIX = "Insert it where a JavaScript value goes, outside any '${…}': const count = ${count|json}; — then use count in the JavaScript."


@pytest.mark.parametrize(
    ("function", "message", "fix"),
    [
        (
            "() => `cost: $${count|json}`",
            "${count|json} in 'function' sits inside '$${…}', which pflow sends to the MCP tool as written — "
            "so the value is never inserted.",
            _7A_FIX,
        ),
        (
            "() => `${${count|json} + 1}`",
            "${count|json} in 'function' sits inside another '${…}' ('${${count|json} + 1}'), which pflow sends "
            "to the MCP tool as written — so the value is never inserted.",
            _7A_FIX,
        ),
        (
            "() => ${count|json }",
            "'${count|json }' in 'function' is not a pflow insert (a space before '}'), so it would be sent to "
            "the MCP tool as JavaScript, unchanged.",
            "Write ${count|json}",
        ),
        (
            "() => ${count|JSON}",
            "'${count|JSON}' in 'function' is not a pflow insert ('JSON' must be lower-case), so it would be "
            "sent to the MCP tool as JavaScript, unchanged.",
            "Write ${count|json}",
        ),
        (
            "() => ${ count|json}",
            "'${ count|json}' in 'function' is not a pflow insert (a space after '${'), so it would be sent to "
            "the MCP tool as JavaScript, unchanged.",
            "Write ${count|json}",
        ),
    ],
    ids=["in-escape", "in-js-template", "space-before-brace", "upper-case", "space-after-open"],
)
def test_an_insert_the_view_cannot_see_is_the_one_error(function: str, message: str, fix: str) -> None:
    error = _only_error(_ir(_eval("cost", function), inputs=("count",)))
    assert (error.message, error.suggestions) == (message, [fix])
    assert error.context["path"] == "nodes[id=cost].params.function"


def test_without_an_insert_an_escape_is_just_javascript() -> None:
    """Presence pair of the escape row: no insert, so the unused input is the one error."""
    error = _only_error(_ir(_eval("cost", "() => `cost: $${count}`"), inputs=("count",)))
    assert error.message == "Declared input(s) never used as template variable: count"


@pytest.mark.parametrize("prompt", ["cost: $${count|json} ${count}", "${count|json }", "${count|JSON}"])
def test_the_unseen_insert_checks_are_embedded_code_only(prompt: str) -> None:
    """On a Template param the same text is an escape or an ordinary Issue — no §7 error."""
    diagnostics = _validate(_ir({"id": "ask", "type": "llm", "params": {"prompt": prompt}}, inputs=("count",)))
    assert not [d for d in diagnostics if "sits inside" in d.message or "not a pflow insert" in d.message]


def test_an_unbalanced_escape_in_embedded_code_is_javascript() -> None:
    assert _validate(_ir(_eval("s", "() => '$${'"))) == []


# ── §4: bare pflow names and quoted inserts ────────────────────────────────


def test_4a_an_input_used_only_bare_is_the_one_error_instead_of_unused() -> None:
    ir = _ir(_eval("click", "() => { const sel = '${selector}'; return sel; }"), inputs=("selector",))
    error = _only_error(ir)
    assert error.message == (
        "Input 'selector' is never inserted: its only use, '${selector}' in 'function', is JavaScript text "
        "that pflow sends to the MCP tool unchanged."
    )
    assert error.suggestions == [
        "Replace '${selector}' (the quotes too) with ${selector|json} — the value arrives already quoted: "
        "const sel = ${selector|json};"
    ]
    assert error.context["embedded_references"] == [
        {"reference": "${selector}", "root_kind": "input", "replacement": "${selector|json}"}
    ]


def test_4a_presence_pair_without_the_bare_reference_the_input_is_unused() -> None:
    error = _only_error(_ir(_eval("click", "() => 1"), inputs=("selector",)))
    assert error.message == "Declared input(s) never used as template variable: selector"


def test_4a_an_input_also_inserted_elsewhere_only_warns() -> None:
    ir = _ir(_eval("click", "() => [${selector|json}, `${selector}`]"), inputs=("selector",))
    diagnostics = _validate(ir)
    assert _errors(diagnostics) == []
    assert [w.message for w in _warnings(diagnostics)] == [
        "${selector} in 'function' is JavaScript: pflow sends it unchanged, so workflow input 'selector' is not inserted."
    ]


def test_4a_unquoted_inside_a_template_literal_names_where_a_value_goes() -> None:
    error = _only_error(_ir(_eval("read", "() => `${user.name}`"), inputs=("user",)))
    assert error.suggestions == [f"Put ${{user.name|json}} {JS_VALUE_PLACE}: const name = ${{user.name|json}};"]


def test_4a_one_error_per_input_in_a_param() -> None:
    function = "() => { const sel = '${selector}'; const text = \"${text}\"; return [sel, text]; }"
    errors = _errors(_validate(_ir(_eval("click", function), inputs=("selector", "text"))))
    assert [e.message.split(":")[0] for e in errors] == [
        "Input 'selector' is never inserted",
        "Input 'text' is never inserted",
    ]
    assert errors[1].suggestions == [
        'Replace "${text}" (the quotes too) with ${text|json} — the value arrives already quoted: '
        "const text = ${text|json};"
    ]


def test_4a_a_whole_value_input_gets_the_eval_fix() -> None:
    error = _only_error(_ir(_eval("run", "${code}"), inputs=("code",)))
    assert error.suggestions == [
        "A program produced by a step is text, not code: run it with eval — () => eval(${code|json})()"
    ]


def _batched_rows(function: str) -> dict[str, Any]:
    return _ir(_eval("rows", function, batch={"items": [1, 2]}))


def test_4b_a_batch_alias_written_bare_warns_with_the_spaces_escape_hatch() -> None:
    diagnostics = _validate(_batched_rows("() => [{id: 7}].map((item) => `${item.id}`)"))
    assert _errors(diagnostics) == []
    [warning] = _warnings(diagnostics)
    assert warning.message == (
        "${item.id} in 'function' is JavaScript: pflow sends it unchanged, so the batch item is not inserted."
    )
    assert warning.suggestions == [
        f"To insert it, put ${{item.id|json}} {JS_VALUE_PLACE}: const id = ${{item.id|json}};",
        "If 'item' here is your JavaScript variable, the code is correct — write ${ item.id } (spaces inside "
        "the braces) to clear this warning.",
    ]


def test_4b_spaces_inside_the_braces_clear_the_warning() -> None:
    assert _validate(_batched_rows("() => [{id: 7}].map((item) => `${ item.id }`)")) == []


def test_4b_several_references_share_one_warning_in_source_order() -> None:
    ir = _ir(
        {"id": "fetch", "type": "shell", "params": {"command": "echo"}},
        _eval("rows", "() => `${item.id} ${fetch.stdout}`", batch={"items": [1]}),
    )
    [warning] = _warnings(_validate(ir))
    assert warning.message == (
        "${item.id} and ${fetch.stdout} in 'function' are JavaScript: pflow sends them unchanged, so the batch "
        "item and the output of step 'fetch' are not inserted."
    )
    assert warning.suggestions == [
        f"To insert it, put ${{item.id|json}} {JS_VALUE_PLACE}: const id = ${{item.id|json}};",
        f"To insert it, put ${{fetch.stdout|json}} {JS_VALUE_PLACE}: const stdout = ${{fetch.stdout|json}};",
        "If 'item' or 'fetch' here is your JavaScript variable, the code is correct — write it with spaces "
        "inside the braces (${ item.id }) to clear this warning.",
    ]


@pytest.mark.parametrize(
    "function",
    [
        "() => `${fetch}`",  # a bare step id is ordinary JavaScript
        "() => `${a + b}`",  # an Issue
        "() => `${i}`",  # not a pflow name
        "() => ${fetch.stdout|json}",  # an insert, unquoted
    ],
)
def test_names_pflow_does_not_know_here_are_javascript(function: str) -> None:
    ir = _ir({"id": "fetch", "type": "shell", "params": {"command": "echo"}}, _eval("s", function))
    assert _validate(ir) == []


def test_a_batch_alias_is_in_scope_only_on_the_batched_step() -> None:
    ir = _ir(
        {"id": "batched", "type": "llm", "batch": {"items": [1]}, "params": {"prompt": "${item}"}},
        _eval("s", "() => `${item.x}`"),
    )
    assert _validate(ir) == []
    # Presence pair: the same text on the batched step warns.
    assert len(_warnings(_validate(_ir(_eval("s", "() => `${item.x}`", batch={"items": [1]}))))) == 1


def test_4c_a_whole_value_step_reference_gets_the_eval_fix() -> None:
    ir = _ir({"id": "gen", "type": "shell", "params": {"command": "echo"}}, _eval("run", "${gen.stdout}"))
    [warning] = _warnings(_validate(ir))
    assert warning.suggestions[0] == (
        "A program produced by a step is text, not code: run it with eval — () => eval(${gen.stdout|json})()"
    )


def test_4d_an_insert_inside_quotes_warns() -> None:
    quoted = _validate(_ir(_eval("click", "() => '${selector|json}'"), inputs=("selector",)))
    assert _errors(quoted) == []
    [warning] = _warnings(quoted)
    assert (warning.message, warning.suggestions) == (
        "'${selector|json}' in 'function': the insert is already a quoted JavaScript value, so these quotes "
        "wrap it a second time.",
        ["Remove the quotes around it: ${selector|json}"],
    )
    assert _validate(_ir(_eval("click", "() => ${selector|json}"), inputs=("selector",))) == []


# ── The rendered text, through the CLI ─────────────────────────────────────


def test_cli_renders_4a_and_4b(tmp_path: Path) -> None:
    steps = (
        "### click\n\nEvaluate.\n\n- type: mcp-chrome-devtools-evaluate_script\n- function: |\n"
        "    () => { const sel = '${selector}'; return sel; }\n"
    )
    result = _cli(tmp_path, _markdown(steps, inputs=("selector",)))
    assert result.exit_code == 2
    assert result.stdout.endswith(
        "Error 1: Template Error\n\n"
        "Input 'selector' is never inserted: its only use, '${selector}' in 'function', is JavaScript text that "
        "pflow sends to the MCP tool unchanged.\n"
        "  At: node 'click', nodes[id=click].params.function\n\n"
        "  → Replace '${selector}' (the quotes too) with ${selector|json} — the value arrives already quoted: "
        "const sel = ${selector|json};\n"
    )
    assert "never used as template variable" not in result.stdout

    batched = (
        "### rows\n\nEvaluate.\n\n- type: mcp-chrome-devtools-evaluate_script\n- batch:\n    items: [1, 2]\n"
        "- function: |\n    () => [{id: 7}].map((item) => `${item.id}`)\n"
    )
    result = _cli(tmp_path, _markdown(batched))
    assert result.exit_code == 0
    assert result.stdout == "✓ Workflow is valid\n"
    assert result.stderr == (
        "  ⚠ [rows] ${item.id} in 'function' is JavaScript: pflow sends it unchanged, so the batch item is not "
        "inserted.\n"
        f"    → To insert it, put ${{item.id|json}} {JS_VALUE_PLACE}: const id = ${{item.id|json}};\n"
        "    → If 'item' here is your JavaScript variable, the code is correct — write ${ item.id } (spaces inside "
        "the braces) to clear this warning.\n"
    )


# ── §6: a reference inside an insert keeps |json in every rebuilt template ──


def test_6_an_unknown_root_in_an_insert_renders_as_ruled(tmp_path: Path) -> None:
    steps = (
        "### click\n\nEvaluate.\n\n- type: mcp-chrome-devtools-evaluate_script\n- function: () => ${nod.result|json}\n"
    )
    result = _cli(tmp_path, _markdown(steps))
    assert result.exit_code == 2
    assert "Node 'click' references non-existent node 'nod' in parameter 'function'." in result.stdout
    assert result.stdout.endswith(
        "Error 2: Template Error\n\n"
        "Template variable ${nod.result|json} has no valid source — '${nod}' is neither a workflow input nor a "
        "node ID in this workflow.\n"
    )


def test_a_mis_cased_input_inside_an_insert_is_suggested_as_an_insert() -> None:
    ir = _ir(_eval("s", "() => ${Repo|json}"), inputs=("repo",))
    [error] = [e for e in _errors(_validate(ir)) if "undefined input" in e.message]
    assert error.suggestions == ["Did you mean '${repo|json}'?"]
    # Presence pair: a mis-cased bare reference in a Template param is suggested bare.
    bare = _ir({"id": "ask", "type": "llm", "params": {"prompt": "${Repo}"}}, inputs=("repo",))
    [error] = [e for e in _errors(_validate(bare)) if "undefined input" in e.message]
    assert error.suggestions == ["Did you mean '${repo}'?"]


def _data_flow_error(function: str, needle: str, **step: Any) -> Diagnostic:
    [error] = [e for e in _errors(_validate(_ir(_eval("s", function, **step)))) if needle in e.message]
    return error


def _llm_error(prompt: str, needle: str, **step: Any) -> Diagnostic:
    ask = {"id": "s", "type": "llm", "params": {"prompt": prompt}, **step}
    [error] = [e for e in _errors(_validate(_ir(ask))) if needle in e.message]
    return error


def test_a_reserved_name_inside_an_insert_is_corrected_as_an_insert() -> None:
    batched = {"batch": {"items": [1, 2]}}
    index = _data_flow_error("() => ${__index__.x|json}", "accesses fields on `__index__`", **batched)
    assert index.message.startswith("Template '${__index__.x|json}' in node 's'")
    assert index.suggestions == [
        "Use bare `${__index__|json}` for the item position number.",
        "For batch item data, use `${item|json}` or `${item.field|json}` on a batch node.",
    ]
    iteration = _data_flow_error("() => ${__iteration__.x|json}", "accesses fields on `__iteration__`")
    assert iteration.suggestions == ["Use bare `${__iteration__|json}` for the current loop iteration number."]
    reserved = _data_flow_error("() => ${__execution__|json}", "reserved by pflow")
    assert (
        reserved.suggestions[0] == "Only `${__index__|json}` (the current batch item index) is available in templates."
    )
    # Presence pair: the same mistakes in a Template param are corrected bare.
    index = _llm_error("${__index__.x}", "accesses fields on `__index__`", **batched)
    assert index.message.startswith("Template '${__index__.x}' in node 's'")
    assert index.suggestions == [
        "Use bare `${__index__}` for the item position number.",
        "For batch item data, use `${item}` or `${item.field}` on a batch node.",
    ]
    iteration = _llm_error("${__iteration__.x}", "accesses fields on `__iteration__`")
    assert iteration.suggestions == ["Use bare `${__iteration__}` for the current loop iteration number."]
    reserved = _llm_error("${__execution__}", "reserved by pflow")
    assert reserved.suggestions[0] == "Only `${__index__}` (the current batch item index) is available in templates."


def test_an_undeclared_input_inside_an_insert_is_corrected_as_an_insert() -> None:
    needle = "no inputs are declared"
    error = _data_flow_error("() => ${missing|json}", needle)
    assert error.message == (
        "Node 's' references '${missing|json}' in parameter 'function' but no inputs are declared in this workflow."
    )
    assert error.suggestions == [
        "Declare 'missing' under '## Inputs' or use a node output reference like ${node_id.field|json}."
    ]
    assert error.context["template"] == "${missing|json}"
    # Presence pair: the same mistake in a Template param is corrected bare.
    error = _llm_error("${missing}", needle)
    assert error.suggestions == [
        "Declare 'missing' under '## Inputs' or use a node output reference like ${node_id.field}."
    ]
    assert error.context["template"] == "${missing}"


@pytest.mark.parametrize(
    ("function", "message"),
    [
        (
            "() => ${item.nope|json}",
            "Node 's': ${item.nope|json} references field 'nope' which is not available on batch items "
            "(items come from: ${process.results}).",
        ),
        (
            "() => ${item.llm_usage.nope|json}",
            "Node 's': ${item.llm_usage.nope|json} — 'nope' does not exist on 'llm_usage' (dict).",
        ),
    ],
    ids=["item-field", "nested-item-field"],
)
def test_a_batch_item_miss_inside_an_insert_keeps_the_suffix(function: str, message: str) -> None:
    ir = _ir(
        {"id": "process", "type": "llm", "batch": {"items": "${data}"}, "params": {"prompt": "P ${item}"}},
        _eval("s", function, batch={"items": "${process.results}"}),
    )
    ir["inputs"] = {"data": {"type": "array", "required": True, "description": "Items."}}
    [error] = _errors(WorkflowValidator.validate(ir, extracted_params={"data": ["a"]}, registry=Registry()))
    assert error.message == message


# ── Mid-task review fixes ──────────────────────────────────────────────────


def test_a_bare_dynamic_index_output_source_insert_is_the_error() -> None:
    """``up.items[${i}]|json`` is one bare expression body, so it normalizes to ``${…|json}``:
    a misplaced insert, never the literal text ``up.items[0]|json``."""
    ir = _ir(
        {"id": "s", "type": "shell", "params": {"command": "echo"}},
        inputs=("i",),
        outputs={"o": {"source": "s.stdout[${i}]|json", "description": "Out."}},
    )
    error = _only_error(ir)
    assert (error.message, error.suggestions) == _misplaced("${s.stdout[${i}]|json}", "s.stdout[${i}]")


def test_a_near_miss_around_inner_braces_is_the_error() -> None:
    """The Issue ends at the ``{}``'s ``}``; the near-miss reads the whole written insert."""
    error = _only_error(_ir(_eval("s", "() => (${{}|JSON})")))
    assert (error.message, error.suggestions) == (
        "'${{}|JSON}' in 'function' is not a pflow insert ('JSON' must be lower-case), so it would be sent to "
        "the MCP tool as JavaScript, unchanged.",
        ["Write ${{}|json}"],
    )


def test_an_insert_inside_a_bare_expression_literal_is_the_error() -> None:
    error = _only_error(_ir(_eval("s", '() => `${"${count|json}"}`'), inputs=("count",)))
    assert error.message == (
        "${count|json} in 'function' sits inside another '${…}' ('${\"${count|json}\"}'), which pflow sends to "
        "the MCP tool as written — so the value is never inserted."
    )


def test_4a_every_input_of_a_coalesce_gets_its_own_error() -> None:
    errors = _errors(_validate(_ir(_eval("s", "() => `${a ?? b}`"), inputs=("a", "b"))))
    assert [e.message.split(":")[0] for e in errors] == ["Input 'a' is never inserted", "Input 'b' is never inserted"]


def test_4b_a_coalesce_of_two_scoped_roots_lists_both_owners_and_one_fix() -> None:
    ir = _ir(
        {"id": "fetch", "type": "shell", "params": {"command": "echo"}},
        _eval("rows", "() => `${item.id ?? fetch.stdout}`", batch={"items": [1]}),
    )
    [warning] = _warnings(_validate(ir))
    assert warning.message == (
        "${item.id ?? fetch.stdout} in 'function' is JavaScript: pflow sends it unchanged, so the batch item and "
        "the output of step 'fetch' are not inserted."
    )
    assert warning.suggestions[0] == (
        f"To insert it, put ${{item.id ?? fetch.stdout|json}} {JS_VALUE_PLACE}: const id = ${{item.id ?? fetch.stdout|json}};"
    )
    assert len(warning.suggestions) == 2  # one fix for the one expression, then the closing line


# ── Every reference a path pass shows or suggests keeps the insert's form (§6) ──


def _up_and(*consumers: dict[str, Any]) -> dict[str, Any]:
    return _ir({"id": "up", "type": "shell", "params": {"command": "echo"}}, *consumers)


def _path_error(diagnostics: list[Diagnostic]) -> list[Diagnostic]:
    return [d for d in _errors(diagnostics) if "does not output" in d.message or "not available on batch" in d.message]


def test_pass_5_suggests_a_changed_path_as_an_insert() -> None:
    [error] = _path_error(_validate(_up_and(_eval("s", "() => ${up.exit_cod|json}"))))
    assert error.suggestions == ["Change ${up.exit_cod|json} to ${up.exit_code|json}"]
    assert error.context["similar_names"] == ["${up.exit_code|json}"]
    assert "${up.stdout|json} (str)" in error.context["available_fields"]
    # Presence pair: the same miss in a Template param suggests the bare form.
    [bare] = _path_error(_validate(_up_and({"id": "ask", "type": "llm", "params": {"prompt": "${up.exit_cod}"}})))
    assert bare.suggestions == ["Change ${up.exit_cod} to ${up.exit_code}"]
    assert "${up.stdout} (str)" in bare.context["available_fields"]


def test_pass_5_mixed_use_renders_each_reference_in_its_own_form() -> None:
    """One missing path read bare by a prompt and as an insert by embedded code: each
    diagnostic carries its own form (their messages are identical, so a display that
    deduplicates by message shows the first — the bare one — until it is fixed)."""
    ir = _up_and(
        _eval("s", "() => ${up.exit_cod|json}"), {"id": "ask", "type": "llm", "params": {"prompt": "${up.exit_cod}"}}
    )
    assert [e.suggestions for e in _path_error(_validate(ir))] == [
        ["Change ${up.exit_cod} to ${up.exit_code}"],
        ["Change ${up.exit_cod|json} to ${up.exit_code|json}"],
    ]


def _batched(*consumers: dict[str, Any]) -> dict[str, Any]:
    ir = _ir(
        {"id": "process", "type": "llm", "batch": {"items": "${data}"}, "params": {"prompt": "P ${item}"}},
        *consumers,
    )
    ir["inputs"] = {"data": {"type": "array", "required": True, "description": "Items."}}
    return ir


def test_pass_8_suggests_item_fields_as_inserts_beside_a_bare_twin() -> None:
    ir = _batched(
        _eval("s", "() => ${item.respons|json}", batch={"items": "${process.results}"}),
        {"id": "ask", "type": "llm", "batch": {"items": "${process.results}"}, "params": {"prompt": "${item.respons}"}},
    )
    errors = _path_error(WorkflowValidator.validate(ir, extracted_params={"data": ["a"]}, registry=Registry()))
    by_node = {e.node_id: e for e in errors}
    assert by_node["s"].suggestions == ["Use ${item.response|json}"]
    assert by_node["s"].context["template"] == "${item.respons|json}"
    assert "${item.prompt|json} (str)" in by_node["s"].context["available_fields"]
    # Presence pair, same workflow: the Template param's twin is suggested bare.
    assert by_node["ask"].suggestions == ["Use ${item.response}"]
    assert "${item.prompt} (str)" in by_node["ask"].context["available_fields"]

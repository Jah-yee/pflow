"""The workflow validator types what an author WROTE against a declaration (Task 120 PE, D11 a/e/f).

A declared ``default:``, a literal a parent passes to a child's declared input, and an input named like a batch
alias are each certain to fail (or to be shadowed) at run time, so validation refuses them up front — on every
path that validates: ``--validate-only``, ``save`` and the run. The type rule is the input boundary's own
(``param_coercion.coerce_declared_input``), so the validator and the run say the same thing in the same words.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from pflow.cli.main import cli
from pflow.core.diagnostic import Diagnostic
from pflow.core.exceptions import CompilationError, WorkflowValidationError
from pflow.core.workflow.save_service import save_workflow_with_options
from pflow.execution.result import RunnerConfig
from pflow.execution.runner import WorkflowRunner
from pflow.registry import Registry
from pflow.runtime import WorkflowEngine, compile_workflow
from tests.shared.markdown_utils import write_workflow_file


def _errors(workflow: dict[str, Any] | str) -> list[Diagnostic]:
    return WorkflowRunner().validate(workflow, {}).errors


def _shell(node_id: str, value: str, **extra: Any) -> dict[str, Any]:
    return {
        "id": node_id,
        "type": "shell",
        "purpose": "Echo a value.",
        "params": {"env": {"X": value}, "command": 'printf "%s" "$X"'},
        **extra,
    }


def _with_input(spec: dict[str, Any], *nodes: dict[str, Any], name: str = "n") -> dict[str, Any]:
    return {
        "ir_version": "0.1.0",
        "inputs": {name: {"description": "An input.", "required": False, **spec}},
        "nodes": list(nodes) or [_shell("show", f"${{{name}}}")],
        "edges": [],
    }


# (a) — a declared default is typed by its declaration ------------------------------------------


class TestDeclaredDefaults:
    @pytest.mark.parametrize(
        ("spec", "message", "fix"),
        [
            pytest.param(
                {"type": "integer", "default": "abc"},
                "The default of input 'n' is 'abc' but its type is `- type: integer`.",
                "Change the default to a whole number (e.g. `- default: 3`), or the type to `- type: string`.",
                id="text-on-integer",
            ),
            pytest.param(
                {"type": "object", "default": [1]},
                "The default of input 'n' is [1] but its type is `- type: object`.",
                'Change the default to a JSON object (e.g. `- default: {"a": 1}`), or the type to `- type: array`.',
                id="list-on-object",
            ),
        ],
    )
    def test_a_default_that_does_not_fit_is_an_error_at_its_path(
        self, spec: dict[str, Any], message: str, fix: str
    ) -> None:
        (error,) = _errors(_with_input(spec))
        assert (error.title, error.message, error.suggestions) == ("Invalid input value", message, [fix])
        assert error.context is not None
        assert (error.context["path"], error.context["source"]) == ("inputs.n.default", "default")

    @pytest.mark.parametrize(
        "spec",
        [
            pytest.param({"type": "string", "default": 1.1}, id="yaml-typed-scalar-into-string"),
            pytest.param({"type": "boolean", "default": True}, id="boolean"),
            pytest.param({"type": "integer", "default": "7"}, id="integer-text"),
        ],
    )
    def test_a_default_that_fits_is_valid(self, spec: dict[str, Any]) -> None:
        assert _errors(_with_input(spec)) == []


BAD_DEFAULT_WF = """# Bad default

An integer input with a default that is not one.

## Inputs

### n

N.

- type: integer
- default: abc

## Steps

### show

Show it.

- type: shell
- env:
    N: ${n}

```shell command
printf 'n=%s' "$N"
```
"""


class TestADefaultIsRefusedOnEveryValidatingPath:
    """Break 12: before, ``--validate-only`` said valid and the run printed ``n=abc`` with exit 0."""

    @staticmethod
    def _json_errors(result: Any) -> list[dict[str, Any]]:
        payload = json.loads(result.stdout)
        assert payload["success"] is False, payload
        return payload["errors"]  # type: ignore[no-any-return]

    def test_validate_only_and_the_run_refuse_it_in_the_same_words(self, tmp_path: Path) -> None:
        workflow = tmp_path / "bad-default.pflow.md"
        workflow.write_text(BAD_DEFAULT_WF, encoding="utf-8")
        runner = CliRunner(mix_stderr=False)
        validated = runner.invoke(cli, ["--validate-only", "--output-format", "json", str(workflow)])
        ran = runner.invoke(cli, ["--output-format", "json", str(workflow)])
        assert validated.exit_code == ran.exit_code == 1
        shown = [(e["message"], e["context"]["path"]) for e in self._json_errors(validated)]
        assert shown == [("The default of input 'n' is 'abc' but its type is `- type: integer`.", "inputs.n.default")]
        assert [(e["message"], e["context"]["path"]) for e in self._json_errors(ran)] == shown

    def test_a_supplied_value_does_not_excuse_the_default(self, tmp_path: Path) -> None:
        workflow = tmp_path / "bad-default.pflow.md"
        workflow.write_text(BAD_DEFAULT_WF, encoding="utf-8")
        result = CliRunner(mix_stderr=False).invoke(cli, ["--validate-only", str(workflow), "n=3"])
        assert result.exit_code == 1
        assert "The default of input 'n' is 'abc'" in result.output

    def test_save_refuses_it(self) -> None:
        with pytest.raises(WorkflowValidationError) as exc_info:
            save_workflow_with_options("bad-default", BAD_DEFAULT_WF)
        paths = [d.context["path"] for d in exc_info.value.validation_errors if d.context]
        assert paths == ["inputs.n.default"]

    def test_save_accepts_the_corrected_default(self) -> None:
        """Presence half: the same workflow with a fitting default saves."""
        path, _, _ = save_workflow_with_options("good-default", BAD_DEFAULT_WF.replace("default: abc", "default: 3"))
        assert path.exists()


# (e) — a literal a parent passes is typed by the child's declaration ----------------------------

CHILD_WF = """# Child

Show two typed inputs.

## Inputs

### s

A string.

- type: string

### n

A number.

- type: integer

## Steps

### show

Show them.

- type: code
- inputs:
    s: ${s}
    n: ${n}

```python code
s: str
n: int
result: str = f"{s}:{n}"
```
"""


def _parent(tmp_path: Path, inputs: Any, *, batch: dict[str, Any] | None = None) -> dict[str, Any]:
    child = tmp_path / "child.pflow.md"
    child.write_text(CHILD_WF, encoding="utf-8")
    node: dict[str, Any] = {
        "id": "call",
        "type": "workflow",
        "purpose": "Call the child.",
        "params": {"workflow": "./child.pflow.md", "inputs": inputs},
    }
    if batch is not None:
        node["batch"] = batch
    return {"ir_version": "0.1.0", "nodes": [node], "edges": []}


def _validate_parent(tmp_path: Path, ir: dict[str, Any]) -> list[Diagnostic]:
    parent = tmp_path / "parent.pflow.md"
    write_workflow_file(ir, parent)
    return _errors(str(parent))


class TestLiteralChildInputs:
    def test_a_literal_the_child_cannot_type_is_an_error_at_the_steps_input(self, tmp_path: Path) -> None:
        (error,) = _validate_parent(tmp_path, _parent(tmp_path, {"s": "hello", "n": "abc"}))
        assert error.message == (
            "Step 'call' passes 'abc' to input 'n' of ./child.pflow.md, declared `- type: integer`."
        )
        assert error.suggestions == ["Pass a whole number from the parent."]
        assert error.context is not None
        assert error.context["path"] == "nodes[id=call].params.inputs.n"
        assert (error.context["source"], error.context["sub_workflow_path"]) == ("parent", "./child.pflow.md")

    @pytest.mark.parametrize(
        "inputs",
        [
            pytest.param({"s": "hello", "n": "7"}, id="integer-text"),
            pytest.param({"s": '{"a":1}', "n": 7}, id="json-text-stays-text-for-a-string"),
            pytest.param({"s": "${up.stdout}", "n": "${up.stdout}"}, id="templates-are-typed-at-run-time"),
        ],
    )
    def test_a_literal_the_child_types_is_valid(self, tmp_path: Path, inputs: dict[str, Any]) -> None:
        ir = _parent(tmp_path, inputs)
        if "${up.stdout}" in inputs.values():
            ir["nodes"].insert(0, _shell("up", "x"))
            ir["edges"] = [{"from": "up", "to": "call"}]
        assert _validate_parent(tmp_path, ir) == []

    def test_an_inline_batch_item_is_an_authored_literal(self, tmp_path: Path) -> None:
        """Inline ``items: ["7", "x", "9"]`` are written by the author: ``x`` is refused before anything runs."""
        batch = {"items": ["7", "x", "9"], "error_handling": "continue"}
        errors = _validate_parent(tmp_path, _parent(tmp_path, {"s": "hello", "n": "${item}"}, batch=batch))
        assert [(e.message, e.context["path"] if e.context else None) for e in errors] == [
            (
                "Step 'call' passes 'x' to input 'n' of ./child.pflow.md, declared `- type: integer`.",
                "nodes[id=call].params.inputs.n",
            )
        ]

    def test_an_inline_item_that_is_the_inputs_map_is_blamed_on_that_item(self, tmp_path: Path) -> None:
        """``inputs: ${item}`` over inline maps: the bad value was written in item 1, so the path says so."""
        batch = {"items": [{"s": "a", "n": 1}, {"s": "b", "n": "abc"}]}
        (error,) = _validate_parent(tmp_path, _parent(tmp_path, "${item}", batch=batch))
        assert error.message == "Step 'call' passes 'abc' to input 'n' of ./child.pflow.md, declared `- type: integer`."
        assert error.context is not None
        assert (error.context["path"], error.context["batch_item_index"]) == (
            "nodes[id=call].batch.items[1].inputs.n",
            1,
        )

    def test_an_inline_item_holding_json_text_is_not_a_map_of_inputs(self, tmp_path: Path) -> None:
        """A whole-map ``inputs: ${item}`` over an item that is JSON TEXT: the engine hands it on unparsed and the
        host refuses it ("resolved to str"); the validator agrees statically."""
        batch = {"items": ['{"s": "a", "n": 1}']}
        ir = _parent(tmp_path, "${item}", batch=batch)
        (error,) = _validate_parent(tmp_path, ir)
        assert error.message == (
            "Step 'call' (batch.items[0]): 'inputs:' on workflow node './child.pflow.md' must be a dict of child "
            "inputs, got str."
        )
        assert error.context is not None
        assert error.context["path"] == "nodes[id=call].batch.items[0].inputs"

        mapped = _parent(tmp_path, "${item}", batch={"items": [{"s": "a", "n": 1}]})  # presence: an item that IS a map
        assert _validate_parent(tmp_path, mapped) == []

        # The run's own refusal, behind no validator: the bare engine on the compiled parent.
        ir = _parent(tmp_path, "${item}", batch={"items": ['{"s": "a", "n": 1}']})
        ir["nodes"][0]["params"]["workflow"] = str(tmp_path / "child.pflow.md")
        with pytest.raises(
            RuntimeError,
            match=r"failed at item \[0\]: Step 'call': 'inputs:' resolved to text, expected a map of child inputs\.",
        ):
            WorkflowEngine().run(compile_workflow(ir, Registry(), initial_params={}), {})


class TestAWholeMapInputsFromADeclaredInput:
    """``inputs: ${m}`` must resolve to a map, and a declared input is never parsed into one — the host refuses
    anything else at run time (checkpoint §1.11), so validation does too."""

    def _parent(self, tmp_path: Path, kind: str) -> dict[str, Any]:
        ir = _parent(tmp_path, "${m}")
        ir["inputs"] = {"m": {"type": kind, "required": True, "description": "The child's inputs."}}
        return ir

    def test_a_declared_string_is_an_error(self, tmp_path: Path) -> None:
        (error,) = _validate_parent(tmp_path, self._parent(tmp_path, "string"))
        assert error.message == (
            "A sub-workflow step's whole `inputs:` needs a map; input 'm' is declared `- type: string` and is "
            "never JSON-parsed."
        )
        assert error.suggestions == ["Declare `- type: object` for 'm'."]
        assert error.context is not None
        assert error.context["path"] == "nodes[id=call].params.inputs"

    def test_a_declared_object_is_valid(self, tmp_path: Path) -> None:
        assert _validate_parent(tmp_path, self._parent(tmp_path, "object")) == []


# (f) — an input named like a batch alias --------------------------------------------------------


class TestAnInputNamedLikeABatchAlias:
    @pytest.mark.parametrize(
        ("alias", "batch", "fix"),
        [
            pytest.param("item", {"items": ["a"]}, "set `as: entry`", id="default-alias"),
            pytest.param("entry", {"items": ["a"], "as": "entry"}, "set `as: entry_item`", id="explicit-as"),
        ],
    )
    def test_is_an_error_naming_as(self, alias: str, batch: dict[str, Any], fix: str) -> None:
        ir = _with_input(
            {"type": "string"},
            _shell("show", f"${{{alias}}}", batch=batch),
            _shell("other", f"${{{alias}}}"),
            name=alias,
        )
        (error,) = _errors(ir)
        assert error.message == (
            f"Input '{alias}' has the same name as the batch alias of step 'show' — inside that step "
            f"`${{{alias}…}}` is the batch item, never the input."
        )
        assert error.suggestions == [
            f"Rename the input, or {fix} under the step's `batch:` and update its item references."
        ]
        assert error.context is not None
        assert error.context["path"] == f"inputs.{alias}"

    def test_a_renamed_alias_is_valid(self) -> None:
        ir = _with_input(
            {"type": "string"},
            _shell("show", "${row}", batch={"items": ["a"], "as": "row"}),
            _shell("other", "${item}"),
            name="item",
        )
        assert _errors(ir) == []


# The compiler enforces the certain-miss and alias rules too (mid-task review #2) -------------------

DYNAMIC_CHILD_WF = """# Dynamic child

A child that reads a field of a string input.

## Inputs

### s

A string.

- type: string

## Steps

### show

Show it.

- type: shell
- env:
    X: ${s.a ?? "fallback"}

```shell command
printf '%s' "$X"
```

## Outputs

### out

Shown.

- source: ${show.stdout}
"""


class TestTheCompilerEnforcesTheRules:
    """A child chosen at run time (``workflow: ${…}``) is only compiled — never validated — so the rules
    whose miss is SILENT at run time live in ``validate_data_flow``, which the compiler runs."""

    def test_a_run_time_child_with_a_certain_miss_fails_instead_of_falling_back(self, tmp_path: Path) -> None:
        child = tmp_path / "child.pflow.md"
        child.write_text(DYNAMIC_CHILD_WF, encoding="utf-8")
        parent = {
            "ir_version": "0.1.0",
            "inputs": {"which": {"type": "string", "required": True, "description": "The child to run."}},
            "nodes": [
                {
                    "id": "call",
                    "type": "workflow",
                    "purpose": "Call the chosen child.",
                    "params": {"workflow": "${which}", "inputs": {"s": '{"a":1}'}},
                }
            ],
            "edges": [],
            "outputs": {"out": {"source": "${call.out}", "description": "The child's output."}},
        }
        result = WorkflowRunner().run(parent, {"which": str(child)}, RunnerConfig())
        assert not result.success
        assert any("so `${s.a}` cannot read a field of it" in d.message for d in result.errors), [
            d.message for d in result.errors
        ]

        # Presence half: the same child declaring `object` runs and reads the field.
        child.write_text(DYNAMIC_CHILD_WF.replace("- type: string", "- type: object"), encoding="utf-8")
        result = WorkflowRunner().run(parent, {"which": str(child)}, RunnerConfig())
        assert result.success, [d.message for d in result.errors]
        assert result.shared_after["call"]["out"] == "1"

    def test_compile_refuses_an_input_named_like_a_batch_alias(self) -> None:
        ir = _with_input({"type": "string"}, _shell("show", "${item}", batch={"items": ["a"]}), name="item")
        with pytest.raises(CompilationError) as exc_info:
            compile_workflow(ir, Registry(), initial_params={"item": "x"})
        assert [d.message for d in exc_info.value.wrapped_diagnostics or []] == [
            "Input 'item' has the same name as the batch alias of step 'show' — inside that step `${item…}` is the "
            "batch item, never the input."
        ]

    def test_root_validation_reports_each_mistake_once(self) -> None:
        """Data flow runs inside the validator and before compile: the run path stops at the validator."""
        ir = _with_input({"type": "string"}, _shell("show", "${n.a}"))
        assert [d.message for d in _errors(ir)] == [
            "Input 'n' is declared `- type: string`, so `${n.a}` cannot read a field of it — a string input is "
            "never JSON-parsed."
        ]


class TestEnumerationKeepsWhatItCannotKnow:
    def test_a_fallback_after_an_unknown_root_is_not_typed_statically(self, tmp_path: Path) -> None:
        """``${count ?? "bad"}`` in an inline batch: the enumeration cannot see ``count``, so its fallback is a
        guess — the run would pass ``count``'s 7. Not an error; the item's own literal still is."""
        ir = _parent(tmp_path, {"s": "${item}", "n": '${count ?? "bad"}'}, batch={"items": ["hello"]})
        ir["inputs"] = {"count": {"type": "integer", "required": True, "description": "A count."}}
        assert _validate_parent(tmp_path, ir) == []

        literal = _parent(tmp_path, {"s": "hello", "n": "${item}"}, batch={"items": ["bad"]})  # presence half
        assert [e.context["path"] for e in _validate_parent(tmp_path, literal) if e.context] == [
            "nodes[id=call].params.inputs.n"
        ]

"""The declared-input rule at the engine sites (Task 120, ADR-0017).

A reference rooted in a declared non-``any`` input is never JSON-parsed; a workflow
step's ``inputs:``, an HTTP header and a code ``inputs:`` key annotated ``str`` are
handed on as text (the consumer types them); every other upstream-output auto-parse is
unchanged. Each case runs through ``compile_workflow`` + the engine's own resolution or a
real run, with the store carrying the compiled ``input_types`` as the engine installs it.
"""

import json
from pathlib import Path
from types import MappingProxyType
from typing import Any, ClassVar

import click.testing
import pytest

from pflow.cli.main import main
from pflow.core.diagnostic_render import format_diagnostic
from pflow.core.templates import DECLARED_INPUT_TYPES_KEY
from pflow.execution.result import RunnerConfig
from pflow.execution.runner import WorkflowRunner
from pflow.registry import Registry
from pflow.runtime.compilation import compile_workflow
from pflow.runtime.engine import WorkflowEngine
from pflow.runtime.engine.batch_executor import resolve_batch_items
from pflow.runtime.engine.engine import _EMPTY_INPUT_TYPES
from pflow.runtime.engine.template_resolution import resolve_templates

JSON_TEXT = '{"a":1}'


def _resolve_step(
    ir: dict[str, Any], step: str, store: dict[str, Any], params: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Compile ``ir`` and resolve ``step``'s params the way the engine does for one visit."""
    compiled = compile_workflow(ir, Registry(), dict(params or {}))
    config = compiled.node_configs[step].template_config
    assert config is not None
    shared = {**(params or {}), **compiled.resolved_defaults, **store}
    shared[DECLARED_INPUT_TYPES_KEY] = MappingProxyType(compiled.input_types)
    merged, _, errors = resolve_templates(config, shared, step)
    assert errors == []
    return merged


def _ir(nodes: list[dict[str, Any]], inputs: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"ir_version": "0.1.0", "inputs": inputs or {}, "nodes": nodes, "edges": []}


def _code(step: str, inputs: dict[str, str], annotations: str) -> dict[str, Any]:
    return {"id": step, "type": "code", "params": {"inputs": inputs, "code": f"{annotations}\nresult: str = 'ok'\n"}}


UPSTREAM = {"up": {"stdout": JSON_TEXT, "list_text": "[1, 2]"}}


class TestConsumerAndSourceRules:
    def test_declared_string_into_a_code_input_stays_text(self) -> None:
        """#686: the parent never re-infers a declared string."""
        ir = _ir([_code("show", {"t": "${s}"}, "from typing import Any\nt: Any")], {"s": {"type": "string"}})
        assert _resolve_step(ir, "show", {}, {"s": JSON_TEXT})["inputs"] == {"t": JSON_TEXT}

    def test_undeclared_any_input_into_a_code_input_is_parsed(self) -> None:
        ir = _ir([_code("show", {"t": "${s}"}, "from typing import Any\nt: Any")], {"s": {"type": "any"}})
        assert _resolve_step(ir, "show", {}, {"s": JSON_TEXT})["inputs"] == {"t": {"a": 1}}

    def test_code_str_annotation_receives_upstream_text(self) -> None:
        ir = _ir([_code("show", {"t": "${up.stdout}", "d": "${up.stdout}"}, "t: str\nd: dict")])
        assert _resolve_step(ir, "show", UPSTREAM)["inputs"] == {"t": JSON_TEXT, "d": {"a": 1}}

    @pytest.mark.parametrize("annotation", ["str | None", "Optional[str]"])
    def test_optional_str_is_text_too(self, annotation: str) -> None:
        ir = _ir([_code("show", {"t": "${up.stdout}"}, f"from typing import Optional\nt: {annotation}")])
        assert _resolve_step(ir, "show", UPSTREAM)["inputs"] == {"t": JSON_TEXT}

    def test_agent_inputs_keep_upstream_parsing(self) -> None:
        ir = _ir([{"id": "ask", "type": "agent", "params": {"prompt": "go", "inputs": {"t": "${up.stdout}"}}}])
        assert _resolve_step(ir, "ask", UPSTREAM)["inputs"] == {"t": {"a": 1}}

    def test_workflow_step_inputs_are_handed_on_as_text(self, tmp_path: Path) -> None:
        """The child's own ## Inputs types each value; the parent stops parsing."""
        ir = _ir([
            {
                "id": "call",
                "type": "workflow",
                "params": {"workflow": str(tmp_path / "c.pflow.md"), "inputs": {"s": "${up.stdout}"}},
            }
        ])
        assert _resolve_step(ir, "call", UPSTREAM)["inputs"] == {"s": JSON_TEXT}

    def test_http_header_values_are_text_but_query_params_still_parse(self) -> None:
        params = {"url": "https://example.com", "headers": {"X": "${up.stdout}"}, "params": {"ids": "${up.list_text}"}}
        merged = _resolve_step(_ir([{"id": "get", "type": "http", "params": params}]), "get", UPSTREAM)
        assert merged["headers"] == {"X": JSON_TEXT}
        assert merged["params"] == {"ids": [1, 2]}


class TestShadowing:
    """The rule follows the ACTIVE binding of a root, not its name."""

    INPUTS: ClassVar[dict[str, Any]] = {"data": {"type": "string"}}

    @staticmethod
    def _get(inputs: dict[str, Any], query: str) -> dict[str, Any]:
        params = {"inputs": inputs, "url": "https://example.com", "params": {"q": query}}
        return {"id": "get", "type": "http", "params": params}

    def test_a_steps_resolved_inputs_key_is_local_for_its_siblings(self) -> None:
        """The local `data` holds JSON text one level down; walking into it is today's parse."""
        upstream = {"up": {"stdout": json.dumps({"a": '{"b": 2}'})}}
        node = self._get({"data": "${up.stdout}"}, "${data.a.b}")
        merged = _resolve_step(_ir([node], self.INPUTS), "get", upstream, {"data": '{"a": "input"}'})
        assert merged["params"] == {"q": 2}

    def test_a_steps_static_inputs_key_is_local_for_its_siblings(self) -> None:
        node = self._get({"data": '{"b": 2}'}, "${data.b}")
        merged = _resolve_step(_ir([node], self.INPUTS), "get", {}, {"data": '{"b": "input"}'})
        assert merged["params"] == {"q": 2}

    def test_the_workflow_input_is_still_protected_in_another_step(self) -> None:
        nodes = [
            {"id": "get", "type": "http", "params": {"inputs": {"data": "${up.stdout}"}, "url": "https://example.com"}},
            _code("show", {"t": "${data}"}, "from typing import Any\nt: Any"),
        ]
        merged = _resolve_step(_ir(nodes, self.INPUTS), "show", UPSTREAM, {"data": JSON_TEXT})
        assert merged["inputs"] == {"t": JSON_TEXT}

    def test_a_same_named_input_value_resolves_against_the_workflow_input(self) -> None:
        """`inputs: {data: ${data}}` with `data: Any`: the value still reads the declared input."""
        ir = _ir([_code("show", {"data": "${data}"}, "from typing import Any\ndata: Any")], self.INPUTS)
        assert _resolve_step(ir, "show", {}, {"data": JSON_TEXT})["inputs"] == {"data": JSON_TEXT}


class TestStructuredParams:
    """The simple-template-into-container parse is the one resolve call now."""

    def _merged(self, template: str, store: dict[str, Any], params: dict[str, Any] | None = None) -> Any:
        params = params or {"v": "unused"}
        node = {"id": "ask", "type": "agent", "params": {"prompt": "go", "output_schema": template}}
        ir = _ir([node], {"v": {"type": "string"}})
        compiled = compile_workflow(ir, Registry(), dict(params or {}))
        config = compiled.node_configs["ask"].template_config
        assert config is not None
        assert config.expected_types.get("output_schema") in {"dict", "object"}
        shared = {**(params or {}), **store, DECLARED_INPUT_TYPES_KEY: MappingProxyType(compiled.input_types)}
        return config, shared

    def test_upstream_json_text_into_a_dict_param_is_parsed(self) -> None:
        config, shared = self._merged("${up.stdout}", UPSTREAM)
        assert resolve_templates(config, shared, "ask")[0]["output_schema"] == {"a": 1}

    def test_declared_string_into_a_dict_param_names_the_input(self) -> None:
        config, shared = self._merged("${v}", {}, {"v": JSON_TEXT})
        with pytest.raises(ValueError, match=r"reads input 'v', declared `- type: string`") as exc_info:
            resolve_templates(config, shared, "ask")
        assert "declare `- type: object` for 'v'" in str(exc_info.value)

    def test_upstream_array_text_into_a_dict_param_names_the_shape(self) -> None:
        config, shared = self._merged("${up.list_text}", UPSTREAM)
        with pytest.raises(ValueError, match=r"expects dict but \$\{up.list_text\} resolved to list"):
            resolve_templates(config, shared, "ask")


class TestBatchItems:
    def _shared(self, values: dict[str, Any], types: dict[str, str]) -> dict[str, Any]:
        return {**values, DECLARED_INPUT_TYPES_KEY: MappingProxyType(types)}

    def test_declared_array_is_the_list(self) -> None:
        assert resolve_batch_items("${arr}", self._shared({"arr": [1, 2]}, {"arr": "array"})) == [1, 2]

    def test_declared_string_holding_a_json_list_is_not_a_list(self) -> None:
        assert resolve_batch_items("${s}", self._shared({"s": '["a"]'}, {"s": "string"})) == '["a"]'

    def test_upstream_json_list_text_is_parsed(self) -> None:
        assert resolve_batch_items("${up.list_text}", self._shared(UPSTREAM, {})) == [1, 2]

    def test_inline_items_follow_each_reference(self) -> None:
        shared = self._shared({**UPSTREAM, "s": '["a"]'}, {"s": "string"})
        assert resolve_batch_items(["${s}", "${up.list_text}"], shared) == ['["a"]', [1, 2]]

    def test_a_complex_template_result_is_never_parsed(self) -> None:
        shared = self._shared(UPSTREAM, {})
        assert resolve_batch_items(" ${up.list_text} ", shared) == [1, 2]  # surrounding space is trimmed
        assert resolve_batch_items("[${up.stdout}]", shared) == '[{"a":1}]'


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def _run(path: Path, params: dict[str, Any]) -> Any:
    result = WorkflowRunner().run(str(path), params, RunnerConfig(trace_enabled=False))
    assert result.success, [format_diagnostic(d) for d in result.diagnostics]
    return result


CHILD_ANY = """# Child

Reads a field of its own `any` input.

## Inputs

### s

Untyped on purpose.

- type: any

### t

Declared text.

- type: string

## Steps

### read

Read field a of `s`, and what `t` arrived as.

- type: code
- inputs:
    v: ${s.a}
    w: ${t}

```python code
from typing import Any
v: Any
w: Any

result: str = f"{v!r} {type(w).__name__}"
```

## Outputs

### out

The field.

- source: ${read.result}
"""

PARENT = """# Parent

A declared string passed to a child, then read again.

## Inputs

### s

Text.

- type: string

## Steps

### call

Call the child.

- type: workflow
- workflow: ./child.pflow.md
- inputs:
    s: ${s}
    t: ${s}

### after

Read the parent's input after the child returned.

- type: code
- inputs:
    t: ${s}

```python code
from typing import Any
t: Any

result: str = type(t).__name__
```

## Outputs

### child

Child output.

- source: ${call.out}

### parent_type

Parent type.

- source: ${after.result}
"""


class TestInstallAndRestore:
    def test_engine_restores_the_outer_value(self) -> None:
        compiled = compile_workflow(
            _ir([{"id": "sh", "type": "shell", "params": {"command": "true"}}], {"s": {"type": "string"}}),
            Registry(),
            {"s": "x"},
        )
        sentinel = MappingProxyType({"other": "integer"})
        shared: dict[str, Any] = {"s": "x", DECLARED_INPUT_TYPES_KEY: sentinel}
        WorkflowEngine().run(compiled, shared)
        assert shared[DECLARED_INPUT_TYPES_KEY] is sentinel
        absent: dict[str, Any] = {"s": "x"}
        WorkflowEngine().run(compiled, absent)
        assert absent[DECLARED_INPUT_TYPES_KEY] is _EMPTY_INPUT_TYPES

    def test_a_child_reads_with_its_own_declarations_and_the_parents_come_back(self, tmp_path: Path) -> None:
        _write(tmp_path / "child.pflow.md", CHILD_ANY)
        parent = _write(tmp_path / "parent.pflow.md", PARENT)
        outputs = _run(parent, {"s": JSON_TEXT}).shared_after
        # The child reads with its OWN declarations: its `any` parses, its `string` stays text.
        assert outputs["call"]["out"] == "1 str"
        assert outputs["after"]["result"] == "str"  # the parent's declaration is back after the child


BATCH = """# Batch

A declared input read inside every batch item.

## Inputs

### s

Text, or any value.

- type: @TYPE@

## Steps

### show

Report what `s` arrived as, per item.

- type: code
- inputs:
    t: ${s}
- batch:
    items: [1, 2]
    parallel: @PARALLEL@

```python code
from typing import Any
t: Any

result: str = type(t).__name__
```

## Outputs

### kinds

Per item.

- source: ${show.results}
"""


@pytest.mark.parametrize("parallel", ["false", "true"])
@pytest.mark.parametrize(("declared", "kind"), [("string", "str"), ("any", "dict")])
def test_every_batch_item_store_carries_the_declarations(
    tmp_path: Path, parallel: str, declared: str, kind: str
) -> None:
    """Per-item stores are copies of the run's store: protection holds in each item, sequential
    and parallel; an `any` input keeps today's parse (the presence half)."""
    text = BATCH.replace("@TYPE@", declared).replace("@PARALLEL@", parallel)
    result = _run(_write(tmp_path / "batch.pflow.md", text), {"s": JSON_TEXT})
    assert [item["result"] for item in result.shared_after["show"]["results"]] == [kind, kind]


OBJECT_INPUT = """# Object input

Reads into an object input.

## Inputs

### d

An object.

- type: object

## Steps

### show

Echo the field.

- type: shell
- env:
    A: ${d.payload.a}

```shell command
printf '%s' "$A"
```
"""


class TestTheMissSaysWhy:
    D = json.dumps({"payload": JSON_TEXT})

    def test_text_inside_a_declared_object_is_unresolved_with_its_reason(self, tmp_path: Path) -> None:
        wf = _write(tmp_path / "wf.pflow.md", OBJECT_INPUT)
        result = WorkflowRunner().run(str(wf), {"d": json.loads(self.D)}, RunnerConfig(trace_enabled=False))
        assert not result.success
        (diagnostic,) = [d for d in result.diagnostics if (d.context or {}).get("category") == "template_error"]
        (reference,) = diagnostic.context["unresolved_references"]  # type: ignore[index]
        assert reference["text_not_parsed"] == "d.payload"
        rendered = format_diagnostic(diagnostic)
        assert "'d.payload' is text ('{\"a\":1}') — a declared input is never" in rendered
        assert 'Nest the object in the input (`{"payload": {"a": 1}}`)' in rendered
        assert "(`json.loads(payload)`)" in rendered

    def test_a_plain_missing_field_keeps_its_message(self, tmp_path: Path) -> None:
        wf = _write(tmp_path / "wf.pflow.md", OBJECT_INPUT.replace("${d.payload.a}", "${d.nope}"))
        result = WorkflowRunner().run(str(wf), {"d": json.loads(self.D)}, RunnerConfig(trace_enabled=False))
        (diagnostic,) = [d for d in result.diagnostics if (d.context or {}).get("category") == "template_error"]
        (reference,) = diagnostic.context["unresolved_references"]  # type: ignore[index]
        assert "text_not_parsed" not in reference
        assert "'d' has no 'nope'" in format_diagnostic(diagnostic)


class TestPostRunReaders:
    """`-o` reads the root store after the engine restored its keys."""

    def _invoke(self, tmp_path: Path, key: str) -> click.testing.Result:
        wf = _write(tmp_path / "wf.pflow.md", OBJECT_INPUT.replace("${d.payload.a}", "${d.payload}"))
        payload = json.dumps({"payload": JSON_TEXT})
        return click.testing.CliRunner().invoke(main, ["--no-trace", "-o", key, str(wf), f"d={payload}"])

    def test_text_inside_a_declared_input_is_not_walked_into(self, tmp_path: Path) -> None:
        result = self._invoke(tmp_path, "d.payload.a")
        assert "output key 'd.payload.a' not found. 'd.payload' is a string" in result.output
        assert "Workflow output" not in result.output

    def test_the_text_itself_is_read(self, tmp_path: Path) -> None:
        result = self._invoke(tmp_path, "d.payload")
        assert result.exit_code == 0, result.output
        assert JSON_TEXT in result.output

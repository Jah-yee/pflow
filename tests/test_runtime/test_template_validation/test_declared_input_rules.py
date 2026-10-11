"""A declared input is never JSON-parsed, so the validator rejects what the runtime would miss (Task 120 PE).

The resolver never re-parses a reference rooted in a declared non-``any`` input (``templates._declared_typed``,
ADR-0017). These rules make ``--validate-only`` refuse the reads that rule makes certain to fail — a path on a
scalar, a field on an ``array``, an index on an ``object``, a declared ``string`` into a container, a
non-``array`` ``batch.items`` — on every surface the runtime resolves, ``??`` operands included (where the miss
would otherwise be a silent fallback). Each rule is driven through ``WorkflowRunner().validate`` (the call
``--validate-only``, ``save`` and ``analyze-cache`` share); the root's ACTIVE binding decides, as at run time.
"""

from __future__ import annotations

from itertools import pairwise
from typing import Any

import pytest

from pflow.core.diagnostic import Diagnostic
from pflow.execution.result import RunnerConfig
from pflow.execution.runner import WorkflowRunner


def _input(kind: str | None) -> dict[str, Any]:
    spec: dict[str, Any] = {"required": False, "description": "An input."}
    if kind is not None:
        spec["type"] = kind
    return spec


def _shell(node_id: str, env: dict[str, Any], **extra: Any) -> dict[str, Any]:
    return {
        "id": node_id,
        "type": "shell",
        "purpose": "Echo a value.",
        "params": {"env": env, "command": 'printf "%s" "$X"', **extra.pop("params", {})},
        **extra,
    }


def _code(node_id: str, inputs: dict[str, Any], code: str) -> dict[str, Any]:
    return {"id": node_id, "type": "code", "purpose": "Read a value.", "params": {"inputs": inputs, "code": code}}


def _workflow(inputs: dict[str, str | None], *nodes: dict[str, Any], **extra: Any) -> dict[str, Any]:
    edges = [{"from": a["id"], "to": b["id"]} for a, b in pairwise(nodes)]
    return {
        "ir_version": "0.1.0",
        "inputs": {name: _input(kind) for name, kind in inputs.items()},
        "nodes": list(nodes),
        "edges": edges,
        **extra,
    }


def _errors(ir: dict[str, Any]) -> list[Diagnostic]:
    return WorkflowRunner().validate(ir, {}).errors


def _declared_errors(ir: dict[str, Any]) -> list[Diagnostic]:
    """The errors these rules raise (each carries the input's ``declared_type``)."""
    return [d for d in _errors(ir) if "declared_type" in (d.context or {})]


def _one(ir: dict[str, Any]) -> Diagnostic:
    errors = _errors(ir)
    assert len(errors) == 1, [d.message for d in errors]
    return errors[0]


# (b) — a path certain to miss on a declared root ------------------------------------------------

MISSES = [
    pytest.param(
        {"s": "string"},
        "${s.a}",
        "Input 's' is declared `- type: string`, so `${s.a}` cannot read a field of it — a string input is never "
        "JSON-parsed.",
        "Declare `- type: object` if 's' holds a JSON object, or reference `${s}` whole.",
        id="field-on-string",
    ),
    pytest.param(
        {"s": "string"},
        "${s[0]}",
        "Input 's' is declared `- type: string`, so `${s[0]}` cannot index it — a string input is never JSON-parsed.",
        "Declare `- type: array` if 's' holds a JSON array, or reference `${s}` whole.",
        id="index-on-string",
    ),
    pytest.param(
        {"n": "integer"},
        "${n.x}",
        "Input 'n' is declared `- type: integer`; `${n.x}` cannot read a field of a number.",
        "Reference `${n}` whole.",
        id="field-on-integer",
    ),
    pytest.param(
        {"flag": "boolean"},
        "${flag[0]}",
        "Input 'flag' is declared `- type: boolean`; `${flag[0]}` cannot index a boolean.",
        "Reference `${flag}` whole.",
        id="index-on-boolean",
    ),
    pytest.param(
        {"items": "array"},
        "${items.name}",
        "Input 'items' is declared `- type: array`; `${items.name}` names a field, but an array has only indexes "
        "(`${items[0]}`).",
        "Index it first (`${items[0]…}`), or reference `${items}` whole.",
        id="field-on-array",
    ),
    pytest.param(
        {"cfg": "object"},
        "${cfg[0]}",
        "Input 'cfg' is declared `- type: object`; `${cfg[0]}` indexes it, but an object has only fields "
        "(`${cfg.<field>}`).",
        "Read a field (`${cfg.<field>}`), or declare `- type: array` if 'cfg' holds a list.",
        id="index-on-object",
    ),
    pytest.param(
        {"cfg": "object", "i": "integer"},
        "${cfg[${i}]}",
        "Input 'cfg' is declared `- type: object`; `${cfg[${i}]}` indexes it, but an object has only fields "
        "(`${cfg.<field>}`).",
        "Read a field (`${cfg.<field>}`), or declare `- type: array` if 'cfg' holds a list.",
        id="dynamic-index-on-object",
    ),
]


class TestAPathCertainToMiss:
    @pytest.mark.parametrize(("inputs", "template", "message", "fix"), MISSES)
    def test_is_an_error_naming_the_input_and_the_fix(
        self, inputs: dict[str, str], template: str, message: str, fix: str
    ) -> None:
        error = _one(_workflow(inputs, _shell("show", {"X": template})))
        assert error.message == message
        assert error.suggestions == [fix]
        assert error.context is not None
        assert error.context["path"] == "nodes[id=show].params.env.X"
        root = next(iter(inputs))
        assert (error.context["input"], error.context["declared_type"]) == (root, inputs[root])

    @pytest.mark.parametrize(
        ("inputs", "template"),
        [
            pytest.param({"items": "array"}, "${items[0].name}", id="index-on-array"),
            pytest.param({"cfg": "object"}, "${cfg.name}", id="field-on-object"),
            pytest.param({"v": "any"}, "${v.a}", id="any-keeps-the-traversal-parse"),
            pytest.param({"u": None}, "${u.a}", id="untyped-behaves-as-any"),
            pytest.param({"items": "array"}, '${items[0] ?? "x"}', id="index-operand-on-array"),
        ],
    )
    def test_a_read_that_may_resolve_is_valid(self, inputs: dict[str, str | None], template: str) -> None:
        assert _errors(_workflow(inputs, _shell("show", {"X": template}))) == []

    def test_a_coalesce_operand_is_checked_and_says_the_fallback_would_win(self) -> None:
        error = _one(_workflow({"s": "string"}, _shell("show", {"X": '${s.a ?? "x"}'})))
        assert error.message == (
            "Input 's' is declared `- type: string`, so `${s.a}` cannot read a field of it — a string input is "
            "never JSON-parsed. As a ?? operand the fallback would always win."
        )

    def test_a_loop_condition_is_checked(self) -> None:
        loop = {"while": "${s.again}", "max_iterations": 2}
        error = _one(_workflow({"s": "string"}, _shell("show", {"X": "x"}, loop=loop)))
        assert error.context is not None
        assert error.context["path"] == "nodes[id=show].loop.while"
        assert error.context["input"] == "s"

    def test_an_inline_batch_item_is_checked(self) -> None:
        batch = {"items": ["${s.a}", "b"]}
        node = _shell("show", {"X": "${item}"}, batch=batch)
        error = _one(_workflow({"s": "string"}, node))
        assert error.context is not None
        assert error.context["path"] == "nodes[id=show].batch.items[0]"

    def test_an_output_source_is_checked(self) -> None:
        outputs = {"o": {"source": "${s.a}", "description": "out"}}
        error = _one(_workflow({"s": "string"}, _shell("show", {"X": "${s}"}), outputs=outputs))
        assert error.context is not None
        assert error.context["path"] == "outputs.o.source"


class TestReachability:
    """The pass runs before the template validator's early return (no node-param template)."""

    @staticmethod
    def _output_only(kind: str) -> dict[str, Any]:
        node = {"id": "show", "type": "shell", "purpose": "A literal command.", "params": {"command": "echo hi"}}
        outputs = {"o": {"source": '${s.a ?? "x"}', "description": "out"}}
        return _workflow({"s": kind}, node, outputs=outputs)

    def test_an_output_only_coalesce_on_a_string_is_an_error(self) -> None:
        error = _one(self._output_only("string"))
        assert error.context is not None
        assert error.context["path"] == "outputs.o.source"
        assert error.message.endswith("As a ?? operand the fallback would always win.")

    def test_the_same_output_on_an_any_input_is_valid(self) -> None:
        assert _errors(self._output_only("any")) == []


# (c) — a declared string into a container target ------------------------------------------------


class TestAStringIntoAContainer:
    @pytest.mark.parametrize(("annotation", "shape"), [("dict", "object"), ("list", "array")])
    def test_a_code_input_annotated_as_a_container_is_an_error(self, annotation: str, shape: str) -> None:
        ir = _workflow({"s": "string"}, _code("show", {"data": "${s}"}, f"data: {annotation}\nresult: str = str(data)"))
        errors = _declared_errors(ir)
        assert [(e.message, e.suggestions) for e in errors] == [
            (
                f"`${{s}}` feeds inputs.data (annotated {annotation}), but input 's' is declared `- type: string` "
                "and is never JSON-parsed.",
                [f"Declare `- type: {shape}` for 's', or annotate `data: str` to receive the text."],
            )
        ]
        assert errors[0].context is not None
        assert errors[0].context["path"] == "nodes[id=show].params.inputs.data"

    def test_a_registry_container_param_is_an_error(self) -> None:
        node = {
            "id": "call",
            "type": "http",
            "purpose": "Call.",
            "params": {"url": "https://example.com", "headers": "${s}"},
        }
        errors = _declared_errors(_workflow({"s": "string"}, node))
        assert [(e.message, e.suggestions) for e in errors] == [
            (
                "`${s}` feeds param 'headers' (type dict), but input 's' is declared `- type: string` and is never "
                "JSON-parsed.",
                ["Declare `- type: object` for 's'."],
            )
        ]

    def test_a_coalesce_operand_is_an_error(self) -> None:
        ir = _workflow(
            {"s": "string"},
            _shell("up", {"X": "x"}),
            _code("show", {"data": "${up.stdout ?? s}"}, "data: dict\nresult: str = str(data)"),
        )
        assert [e.context["input"] for e in _declared_errors(ir) if e.context] == ["s"]

    def test_upstream_text_into_the_same_targets_is_valid(self) -> None:
        """Presence half: the matrix still lets an upstream output's JSON text into a container (it is parsed)."""
        code = _code("show", {"data": "${up.stdout}"}, "data: dict\nresult: str = str(data)")
        http = {
            "id": "call",
            "type": "http",
            "purpose": "Call.",
            "params": {"url": "https://example.com", "headers": "${up.stdout}"},
        }
        assert _errors(_workflow({}, _shell("up", {"X": "x"}), code, http)) == []

    def test_a_string_into_a_text_annotation_is_valid(self) -> None:
        ir = _workflow({"s": "string"}, _code("show", {"data": "${s}"}, "data: str\nresult: str = data"))
        assert _errors(ir) == []


# (d) — batch.items over a declared root -----------------------------------------------------------


class TestBatchItems:
    def test_a_declared_string_is_an_error(self) -> None:
        node = _shell("show", {"X": "${item}"}, batch={"items": "${s}"})
        error = _one(_workflow({"s": "string"}, node))
        assert (
            error.message
            == "`batch.items` needs a list; input 's' is declared `- type: string` and is never JSON-parsed."
        )
        assert error.suggestions == ["Declare `- type: array` for 's'."]
        assert error.context is not None
        assert error.context["path"] == "nodes[id=show].batch.items"

    @pytest.mark.parametrize("kind", ["array", "any"])
    def test_an_array_or_any_input_is_valid(self, kind: str) -> None:
        node = _shell("show", {"X": "${item}"}, batch={"items": "${v}"})
        assert _errors(_workflow({"v": kind}, node)) == []

    def test_an_upstream_output_is_valid(self) -> None:
        node = _shell("show", {"X": "${item}"}, batch={"items": "${up.stdout}"})
        assert _errors(_workflow({}, _shell("up", {"X": "x"}), node)) == []


# Shadowing — the ACTIVE binding of the root decides ---------------------------------------------


class TestShadowing:
    def test_a_siblings_read_of_a_local_inputs_key_is_not_the_input(self) -> None:
        """``inputs: {s: ${up.stdout}}`` binds ``s`` locally: a sibling's ``${s.a}`` reads upstream text, parsed."""
        local = _shell("show", {"X": "${s.a}"}, params={"inputs": {"s": "${up.stdout}"}})
        ir = _workflow({"s": "string"}, _shell("up", {"X": "${s}"}), local)
        assert _declared_errors(ir) == []

    def test_a_steps_own_inputs_value_reads_the_workflow_input(self) -> None:
        """The ``inputs:`` VALUES resolve before the step binds its keys: ``${s.a}`` there is the input's."""
        own = _code("show", {"s": "${s.a}"}, "s: Any\nresult: str = str(s)")
        error = _one(_workflow({"s": "string"}, own))
        assert error.context is not None
        assert error.context["path"] == "nodes[id=show].params.inputs.s"

    def test_a_same_named_binding_reads_the_input_and_receives_its_text(self) -> None:
        """``inputs: {data: ${data}}``: the value reads the workflow input (D8), so a ``dict`` annotation is the
        container error, and an ``Any`` one validates — and the run hands it the TEXT (#686)."""
        as_dict = _workflow({"data": "string"}, _code("show", {"data": "${data}"}, "data: dict\nresult: Any = data"))
        assert [e.context["path"] for e in _declared_errors(as_dict) if e.context] == [
            "nodes[id=show].params.inputs.data"
        ]

        as_any = _workflow({"data": "string"}, _code("show", {"data": "${data}"}, "data: Any\nresult: Any = data"))
        assert _errors(as_any) == []
        result = WorkflowRunner().run(as_any, {"data": '{"a":1}'}, RunnerConfig())
        assert result.success, [d.message for d in result.errors]
        assert result.shared_after["show"]["result"] == '{"a":1}'

    def test_after_a_whole_map_inputs_a_siblings_root_may_be_local(self) -> None:
        """``inputs: ${bindings}`` binds keys known only at run time, so a sibling's ``${s.a}`` may read a local
        ``s`` — uncertain, not an error. The ``inputs:`` expression itself still reads the input."""
        whole_map = _shell("show", {"X": '${s.a ?? "fallback"}'}, params={"inputs": "${bindings}"})
        ir = _workflow({"s": "string", "bindings": "object"}, _shell("up", {"X": "${s}"}), whole_map)
        assert _declared_errors(ir) == []

        reads_input = _shell("show", {"X": "x"}, params={"inputs": "${s.a}"})  # presence half
        errors = _declared_errors(_workflow({"s": "string"}, reads_input))
        assert [e.context["path"] for e in errors if e.context] == ["nodes[id=show].params.inputs"]


class TestABindingCarriesTheDeclaration:
    """A step ``inputs:`` key or batch alias bound to ONE whole reference of a declared input is that input for
    the rules (D15) — as the runtime binds it — and the message names the input it reads through the binding."""

    @staticmethod
    def _bound(binding: str, read: str, inputs: dict[str, str | None], **extra: Any) -> dict[str, Any]:
        node = _shell("show", {"X": read}, params={"inputs": {"doc": binding}}, **extra)
        return _workflow(inputs, _shell("up", {"X": "x"}), node)

    def test_a_path_on_a_bound_declared_string_is_an_error_naming_the_input(self) -> None:
        error = _one(self._bound("${s}", "${doc.a}", {"s": "string"}))
        assert error.message == (
            "Input 's' (as 'doc') is declared `- type: string`, so `${doc.a}` cannot read a field of it — a string "
            "input is never JSON-parsed."
        )
        assert error.suggestions == [
            "Declare `- type: object` if 's' holds a JSON object, or reference `${doc}` whole."
        ]
        assert error.context is not None
        assert (error.context["input"], error.context["path"]) == ("s", "nodes[id=show].params.env.X")

    @pytest.mark.parametrize(
        ("binding", "inputs"),
        [
            pytest.param("${up.stdout}", {"s": "string"}, id="node-output"),
            pytest.param("${s ?? up.stdout}", {"s": "string"}, id="coalesce"),
            pytest.param("${s}", {"s": "any"}, id="any-input"),
            pytest.param("${d.payload}", {"d": "object"}, id="protection-only"),
        ],
    )
    def test_a_binding_that_carries_no_type_is_not_checked(self, binding: str, inputs: dict[str, str | None]) -> None:
        """A local name, or text inside an input (protected at run time, its type unknown): `${doc[0]}` may resolve.
        The same read through a binding that does carry a type is an error (the presence half)."""
        assert [e.context["input"] for e in _declared_errors(self._bound("${s}", "${doc[0]}", {"s": "string"}))] == [
            "s"
        ]
        assert _declared_errors(self._bound(binding, "${doc[0]}", inputs)) == []

    def test_an_alias_over_inline_elements_of_one_type_is_checked_for_each_input(self) -> None:
        """Every element a declared `string`: `${item.a}` misses for every item — one error per input behind the
        alias, each certain for its items. A local element makes nothing certain."""

        def ir(items: list[str]) -> dict[str, Any]:
            node = _shell("show", {"X": "${item.a}"}, batch={"items": items})
            return _workflow({"s": "string", "t": "string", "n": "integer"}, node)

        (error,) = _declared_errors(ir(["${s}", "${s}"]))
        assert error.message.startswith("Input 's' (as 'item') is declared `- type: string`, so `${item.a}`")
        assert [e.context["input"] for e in _declared_errors(ir(["${s}", "${t}"])) if e.context] == ["s", "t"]
        assert _declared_errors(ir(["${s}", "${n}"])) == []  # two types: no one rule
        assert _declared_errors(ir(["${s}", "x"])) == []  # the literal item is local

    def test_an_alias_over_a_whole_declared_input_is_protection_only(self) -> None:
        node = _shell("show", {"X": "${item.a}"}, batch={"items": "${rows}"})
        assert _declared_errors(_workflow({"rows": "array"}, node)) == []

    def test_a_carried_key_is_checked_only_when_every_round_binds_the_same_input(self) -> None:
        """Round 1 binds `doc` to its `inputs:` value; from round 2 the carry template does (the runtime's
        `apply_carry_overrides`)."""

        def ir(carried: str) -> dict[str, Any]:
            loop = {"carry": {"doc": carried}, "while": "${show.stdout}", "max_iterations": 2}
            return self._bound("${s}", "${doc.a}", {"s": "string"}, loop=loop)

        assert _declared_errors(ir("${show.stdout}")) == []
        assert [e.context["input"] for e in _declared_errors(ir("${s}")) if e.context] == ["s"]

    def test_a_bound_string_into_a_container_param_names_the_input(self) -> None:
        node = {
            "id": "get",
            "type": "http",
            "purpose": "Fetch.",
            "params": {"inputs": {"doc": "${s}"}, "url": "https://example.com", "params": "${doc}"},
        }
        (error,) = _declared_errors(_workflow({"s": "string"}, node))
        assert error.message == (
            "`${doc}` feeds param 'params' (type dict), but input 's' (as 'doc') is declared `- type: string` and is "
            "never JSON-parsed."
        )
        assert error.suggestions == ["Declare `- type: object` for 's'."]

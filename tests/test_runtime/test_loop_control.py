"""Unit coverage for the loop condition/cap runtime belt (issue #445).

These are the belt-and-suspenders guards that prevent an infinite loop when a
workflow slips past validation (programmatic IR, or a dynamic output that turns
out to be a string at runtime). A regression here silently re-opens the
foot-gun, so they get direct unit coverage rather than only integration tests.
"""

import pytest

from pflow.core.exceptions import LoopConditionError
from pflow.runtime.engine import instrumentation
from pflow.runtime.engine.loop_control import (
    _coerce_runtime_cap,
    apply_carry_overrides,
    declared_loop_cap,
    evaluate_loop_condition,
    loop_runtime_scope,
    resolve_loop_cap,
)
from pflow.runtime.engine.types import LoopConfig, NodeConfig, TemplateConfig

# --- evaluate_loop_condition ------------------------------------------------


def test_absent_reference_is_falsy_stop() -> None:
    assert evaluate_loop_condition("${n.x}", {}, "n") is False


def test_empty_list_is_falsy() -> None:
    assert evaluate_loop_condition("${n.x}", {"n": {"x": []}}, "n") is False


def test_nonempty_list_is_truthy() -> None:
    assert evaluate_loop_condition("${n.x}", {"n": {"x": [1]}}, "n") is True


def test_dynamic_index_condition_resolves_through_the_template_walk() -> None:
    """Task 170 R1: a dynamic-index condition is one Reference. Read with the raw
    user-path reader it walked to ``None``, so ``until:`` never stopped (it ran to the
    cap) and ``while:`` never ran twice."""
    shared = {"n": {"done": [False, True]}, "idx": 1}
    assert evaluate_loop_condition("${n.done[${idx}]}", shared, "n", until=True) is False  # stop
    assert evaluate_loop_condition("${n.done[${idx}]}", shared, "n") is True
    # A failed inner index is an absent value: `until` continues, `while` stops (as for any miss).
    assert evaluate_loop_condition("${n.done[${nope}]}", shared, "n", until=True) is True
    assert evaluate_loop_condition("${n.done[${nope}]}", shared, "n") is False


def test_zero_is_falsy_positive_is_truthy() -> None:
    assert evaluate_loop_condition("${n.x}", {"n": {"x": 0}}, "n") is False
    assert evaluate_loop_condition("${n.x}", {"n": {"x": 3}}, "n") is True


def test_false_bool_is_falsy() -> None:
    assert evaluate_loop_condition("${n.x}", {"n": {"x": False}}, "n") is False


def test_string_value_raises_not_loops() -> None:
    # Belt half 2: a string that slipped past validation must RAISE, never bool().
    with pytest.raises(LoopConditionError, match="string"):
        evaluate_loop_condition("${n.x}", {"n": {"x": "0\n"}}, "n")


def test_malformed_template_stops_safely() -> None:
    # Not a single ${...} reference → stop (fail-safe), never loop on garbage.
    assert evaluate_loop_condition("not a template", {}, "n") is False


def test_coalesce_falls_through_to_stop_when_unresolved() -> None:
    assert evaluate_loop_condition("${a.x ?? b.y}", {}, "n") is False


def test_coalesce_resolves_typed_value() -> None:
    assert evaluate_loop_condition("${a.x ?? b.y}", {"b": {"y": 1}}, "n") is True


def test_until_true_stops_false_continues() -> None:
    assert evaluate_loop_condition("${n.done}", {"n": {"done": True}}, "n", until=True) is False
    assert evaluate_loop_condition("${n.done}", {"n": {"done": False}}, "n", until=True) is True


def test_until_absent_reference_continues_to_cap() -> None:
    assert evaluate_loop_condition("${n.done}", {}, "n", until=True) is True


def test_until_string_value_raises() -> None:
    with pytest.raises(LoopConditionError, match="string"):
        evaluate_loop_condition("${n.done}", {"n": {"done": "false"}}, "n", until=True)


def test_until_malformed_template_stops_safely() -> None:
    assert evaluate_loop_condition("not a template", {}, "n", until=True) is False


# --- apply_carry_overrides ---------------------------------------------------


def test_apply_carry_overrides_is_fresh_and_preserves_constants() -> None:
    tc = TemplateConfig(
        template_params={"inputs": {"state": "${seed}", "constant_ref": "${constant}"}},
        static_params={"inputs": {"limit": 3}, "command": "echo ${state}"},
        expected_types={},
        resolution_mode="strict",
    )
    original_template_inputs = tc.template_params["inputs"]
    original_static_inputs = tc.static_params["inputs"]

    effective = apply_carry_overrides(tc, {"state": "${step.next_state}"})

    assert effective is not tc
    assert effective.template_params["inputs"] == {
        "limit": 3,
        "state": "${step.next_state}",
        "constant_ref": "${constant}",
    }
    assert "inputs" not in effective.static_params
    assert tc.template_params["inputs"] is original_template_inputs
    assert tc.static_params["inputs"] is original_static_inputs
    assert tc.template_params["inputs"] == {"state": "${seed}", "constant_ref": "${constant}"}
    assert tc.static_params["inputs"] == {"limit": 3}


def test_apply_carry_overrides_moves_all_static_inputs_to_template_inputs() -> None:
    tc = TemplateConfig(
        template_params={},
        static_params={"inputs": {"state": "seed", "limit": 3}},
        expected_types={},
        resolution_mode="strict",
    )

    effective = apply_carry_overrides(tc, {"state": "${step.next_state}"})

    assert effective.template_params["inputs"] == {"state": "${step.next_state}", "limit": 3}
    assert effective.static_params == {}


# --- resolve_loop_cap / _coerce_runtime_cap ---------------------------------


def test_literal_cap_passthrough() -> None:
    assert resolve_loop_cap(LoopConfig("${n.x}", max_iterations=5), {}, "n") == 5


def test_default_cap_is_max_node_visits() -> None:
    assert resolve_loop_cap(LoopConfig("${n.x}"), {}, "n") == instrumentation.MAX_NODE_VISITS


def test_template_cap_resolves() -> None:
    assert resolve_loop_cap(LoopConfig("${n.x}", max_iterations_template="${cap}"), {"cap": 4}, "n") == 4


def test_template_cap_numeric_string_resolves() -> None:
    assert resolve_loop_cap(LoopConfig("${n.x}", max_iterations_template="${cap}"), {"cap": "7"}, "n") == 7


def test_template_cap_non_int_raises() -> None:
    with pytest.raises(LoopConditionError, match="not a positive integer"):
        resolve_loop_cap(LoopConfig("${n.x}", max_iterations_template="${cap}"), {"cap": "abc"}, "n")


def test_template_cap_unresolved_raises() -> None:
    # Absent ${cap} → resolve_template returns the literal "${cap}" → int() fails.
    with pytest.raises(LoopConditionError):
        resolve_loop_cap(LoopConfig("${n.x}", max_iterations_template="${cap}"), {}, "n")


def test_runtime_cap_zero_raises() -> None:
    with pytest.raises(LoopConditionError, match=">= 1"):
        _coerce_runtime_cap(0, "n", "${cap}")


def test_runtime_cap_negative_raises() -> None:
    with pytest.raises(LoopConditionError, match=">= 1"):
        _coerce_runtime_cap(-2, "n", "${cap}")


def test_runtime_cap_over_max_raises() -> None:
    with pytest.raises(LoopConditionError, match="exceeding the hard visit"):
        _coerce_runtime_cap(instrumentation.MAX_NODE_VISITS + 1, "n", "${cap}")


def test_runtime_cap_non_numeric_type_raises() -> None:
    with pytest.raises(LoopConditionError, match="not a positive integer"):
        _coerce_runtime_cap([1, 2], "n", "${cap}")


def test_runtime_cap_float_truncates() -> None:
    assert _coerce_runtime_cap(3.9, "n", "${cap}") == 3


@pytest.mark.parametrize("raw", [float("nan"), float("inf"), float("-inf")], ids=["nan", "inf", "-inf"])
def test_runtime_cap_non_finite_float_raises_structured(raw: float) -> None:
    # A bare int(raw) raised ValueError (nan) / OverflowError (inf) past every caller's
    # LoopConditionError handling (JSON `Infinity` parses to inf).
    with pytest.raises(LoopConditionError, match="not a positive integer"):
        _coerce_runtime_cap(raw, "n", "${cap}")


def test_runtime_cap_respects_lowered_env(monkeypatch) -> None:
    monkeypatch.setattr(instrumentation, "MAX_NODE_VISITS", 3)
    assert _coerce_runtime_cap(3, "n", "${cap}") == 3
    with pytest.raises(LoopConditionError, match="exceeding the hard visit"):
        _coerce_runtime_cap(4, "n", "${cap}")


# --- declared_loop_cap: the cap a gate shows (display-only) -------------------


def _templated(template: str) -> NodeConfig:
    return NodeConfig(
        node_id="n",
        node_type_name="PythonCodeNode",
        template_config=None,
        batch_config=None,
        namespaced=True,
        interface_metadata=None,
        loop_config=LoopConfig("${n.more}", max_iterations_template=template),
    )


# Literal / uncapped / non-loop: pinned through real runs in test_gate_trace.py::TestGateLoopCap.


def test_declared_cap_resolves_a_template_over_upstream_values() -> None:
    assert declared_loop_cap(_templated("${rounds}"), {"rounds": 4}) == 4
    assert declared_loop_cap(_templated("${cfg.limit}"), {"cfg": {"limit": "6"}}) == 6


@pytest.mark.parametrize(
    ("template", "shared"),
    [
        # Each store holds a value a resolving implementation would show instead of None.
        ("${n.result.n}", {"n": {"result": {"n": 5}}}),
        ("${n.result.n ?? 2}", {}),  # own key absent: `??` falls through to the fallback
        ("${__iteration__}", {"__iteration__": 1}),
        ("${__iteration__ ?? 3}", {}),
        ("${cfg[${n.k}].x}", {"cfg": [{"x": 7}], "n": {"k": 0}}),  # own output as a dynamic index
        ("${rounds ?? n.result.n}", {"rounds": 4}),  # own output in a later operand
    ],
    ids=["own-output", "own-coalesce", "iteration", "iteration-coalesce", "own-index", "own-fallback"],
)
def test_declared_cap_is_unknown_when_the_template_depends_on_the_loop_body(template: str, shared: dict) -> None:
    assert declared_loop_cap(_templated(template), shared) is None


@pytest.mark.parametrize(
    "value", [None, "abc", 0, float("nan"), float("inf"), instrumentation.MAX_NODE_VISITS + 1], ids=repr
)
def test_declared_cap_is_unknown_when_the_template_cannot_be_a_cap(value: object) -> None:
    shared = {} if value is None else {"rounds": value}  # None: the reference is absent
    assert declared_loop_cap(_templated("${rounds}"), shared) is None


# --- loop_runtime_scope: the clear_iteration_on_exit asymmetry ---------------
# Load-bearing and shared by two callers (engine passes False, planner True), so
# it gets direct coverage rather than only the indirect integration path.


def test_scope_keeps_iteration_when_not_clearing() -> None:
    """Engine path: ${__iteration__} survives the scope so it persists across re-entry."""
    shared: dict = {}
    with loop_runtime_scope(shared, True, iteration=2, clear_iteration_on_exit=False):
        assert shared["__iteration__"] == 2
        assert shared["__loop_active__"] == 1
    assert shared["__iteration__"] == 2  # kept
    assert "__loop_active__" not in shared  # depth back to 0 → popped


def test_scope_clears_iteration_when_requested() -> None:
    """Planner path: ${__iteration__} must not leak to later nodes after one pass."""
    shared: dict = {}
    with loop_runtime_scope(shared, True, iteration=2, clear_iteration_on_exit=True):
        assert shared["__iteration__"] == 2
    assert "__iteration__" not in shared  # cleared
    assert "__loop_active__" not in shared


def test_scope_loop_active_is_a_depth_counter() -> None:
    """Nested loops: __loop_active__ counts depth, only popped at depth 0."""
    shared: dict = {}
    with loop_runtime_scope(shared, True, iteration=1, clear_iteration_on_exit=False):
        with loop_runtime_scope(shared, True, iteration=1, clear_iteration_on_exit=False):
            assert shared["__loop_active__"] == 2
        assert shared["__loop_active__"] == 1  # inner exit decrements, doesn't pop
    assert "__loop_active__" not in shared


def test_scope_is_noop_when_inactive() -> None:
    shared: dict = {}
    with loop_runtime_scope(shared, False, iteration=5, clear_iteration_on_exit=False):
        assert "__iteration__" not in shared
        assert "__loop_active__" not in shared
    assert shared == {}

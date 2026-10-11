"""A sub-workflow's inputs are typed by the CHILD's ``## Inputs``, per item, in the host's ``prep`` (Task 120 PD).

The parent hands its ``inputs:`` values on unparsed; ``type_child_inputs`` types each one by the child's
declaration (labelled ``parent``) and resolves every absent input environment → settings → default — per
call, so a batch item never inherits another item's values (#188). A value that does not fit is a
routable failure: ``error_action`` and batch ``continue`` route it, and its Diagnostic rides the
child-failure bundle into the error record. These drive real parent → child runs.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from pflow.cli.main import cli
from pflow.core.diagnostic import Diagnostic, Severity
from pflow.core.workflow.status import WorkflowStatus
from pflow.execution.executor_service import build_subworkflow_diagnostics
from pflow.execution.result import RunnerConfig
from pflow.execution.runner import WorkflowRunner

# A child that shows the types it received; `n` is required unless a test gives it a default.
CHILD = """# Child

A child with typed inputs.

## Inputs

### n

A whole number.

- type: integer
{n_spec}

### limit

A whole number with a default.

- type: integer
- default: 3

## Steps

### show

Show the types.

- type: code
- inputs:
    n: ${{n}}
    limit: ${{limit}}

```python code
n: int
limit: int

result: str = f"{{n!r}} {{limit!r}}"
```

## Outputs

### out

Shown.

- source: ${{show.result}}
"""


def _child(tmp_path: Path, *, n_spec: str = "- required: true") -> Path:
    path = tmp_path / "child.pflow.md"
    path.write_text(CHILD.format(n_spec=n_spec), encoding="utf-8")
    return path


def _parent(tmp_path: Path, *, items: str, inputs: str, batch: str = "") -> Path:
    """A parent whose `emit` step prints ``items`` (JSON) at run time, then calls the child per item."""
    path = tmp_path / "parent.pflow.md"
    path.write_text(
        f"""# Parent

Produce items at run time, then call the child per item.

## Steps

### emit

Emit the items.

- type: shell

```shell command
printf '%s' '{items}'
```

### call

Call the child per item.

- type: workflow
- workflow: ./child.pflow.md
- inputs: {inputs}
- batch:
    items: ${{emit.stdout}}
{batch}
""",
        encoding="utf-8",
    )
    return path


def _run(parent: Path) -> Any:
    return WorkflowRunner().run(str(parent), {}, RunnerConfig(trace_enabled=False, cache_enabled=False))


def _outputs(result: Any) -> dict[int, str]:
    return {r["original_index"]: r["out"] for r in result.shared_after["call"]["results"]}


@pytest.mark.parametrize("parallel", [False, True], ids=["sequential", "parallel"])
class TestABatchOfChildrenTypesEachItem:
    """The spec's named test: a runtime-produced list into a child `integer`, under `continue`."""

    def test_good_items_arrive_typed_and_the_bad_one_is_its_own_routed_error(
        self, tmp_path: Path, parallel: bool
    ) -> None:
        _child(tmp_path)
        parent = _parent(
            tmp_path,
            items='["7","x","9"]',
            inputs="{n: ${item}}",
            batch=f"    error_handling: continue\n    parallel: {str(parallel).lower()}",
        )

        result = _run(parent)

        assert result.status == WorkflowStatus.DEGRADED, result.errors
        assert _outputs(result) == {0: "7 3", 2: "9 3"}  # each item its own int; `limit` its default
        (record,) = result.shared_after["call"]["errors"]
        assert record["index"] == 1
        message = "Step 'call' passes 'x' to input 'n' of ./child.pflow.md, declared `- type: integer`."
        assert record["error"].splitlines()[0] == message
        (diagnostic,) = record["child_failure"]["diagnostics"]
        assert diagnostic["context"]["input"] == "n"
        assert diagnostic["context"]["source"] == "parent"
        assert diagnostic["context"]["sub_workflow_step"] == "call"
        assert diagnostic["context"]["path"] == "nodes[id=call].params.inputs.n"

    def test_absent_inputs_take_their_fallbacks_per_item(
        self, tmp_path: Path, parallel: bool, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Item 1 omits `n` after item 0 supplied it: item 1 gets the child's default, never item 0's
        value and never nothing; settings.env beats the default and the environment beats both (#188, C1)."""
        from pflow.core.settings import SettingsManager

        _child(tmp_path, n_spec="- default: 3")
        batch = f"    error_handling: continue\n    parallel: {str(parallel).lower()}"
        parent = _parent(tmp_path, items='[{"n": "7"}, {}]', inputs="${item}", batch=batch)

        defaulted = _run(parent)
        SettingsManager().set_env("n", "6")  # the test's isolated settings file
        from_settings = _run(parent)
        monkeypatch.setenv("n", "5")
        from_env = _run(parent)

        assert _outputs(defaulted) == {0: "7 3", 1: "3 3"}
        assert _outputs(from_settings) == {0: "7 3", 1: "6 3"}
        assert _outputs(from_env) == {0: "7 3", 1: "5 3"}


def test_fail_fast_stops_at_the_bad_item_with_the_same_message(tmp_path: Path) -> None:
    """Without `continue`, the first bad item ends the batch: item 0's child ran (its marker exists),
    item 2's never did."""
    markers = tmp_path / "ran"
    markers.mkdir()
    (tmp_path / "child.pflow.md").write_text(
        f"""# Child

Leave a marker per n.

## Inputs

### n

A whole number.

- type: integer

## Steps

### mark

Touch a file named n.

- type: code
- inputs:
    n: ${{n}}

```python code
from pathlib import Path

n: int

Path({str(markers)!r}, str(n)).touch()
result: str = "ok"
```
""",
        encoding="utf-8",
    )
    parent = _parent(tmp_path, items='["7","x","9"]', inputs="{n: ${item}}")

    result = _run(parent)

    assert result.status == WorkflowStatus.FAILED
    message = "Step 'call' passes 'x' to input 'n' of ./child.pflow.md, declared `- type: integer`."
    assert any(message in d.message for d in result.errors), [d.message for d in result.errors]
    assert sorted(path.name for path in markers.iterdir()) == ["7"]


class TestOneChildCall:
    """Non-batch: the same boundary, routed by `error_action`; its Diagnostic reaches the run's errors."""

    @staticmethod
    def _parent(tmp_path: Path, value: str, extra: str = "") -> Path:
        _child(tmp_path)
        path = tmp_path / "parent.pflow.md"
        path.write_text(
            f"""# Parent

Produce a value, then call the child with it.

## Steps

### up

Emit the value.

- type: shell

```shell command
printf '%s' '{value}'
```

### call

Call the child.

- type: workflow
- workflow: ./child.pflow.md
- inputs:
    n: ${{up.stdout}}
{extra}
""",
            encoding="utf-8",
        )
        return path

    def test_text_that_fits_the_childs_declaration_arrives_typed(self, tmp_path: Path) -> None:
        result = _run(self._parent(tmp_path, "42"))
        assert result.success, result.errors
        assert result.shared_after["call"]["out"] == "42 3"

    def test_error_action_routes_the_failure(self, tmp_path: Path) -> None:
        result = _run(self._parent(tmp_path, "x", extra="- error_action: continue\n- next: end"))
        assert result.success, result.errors  # routed on, not a failed run
        assert "Step 'call' passes 'x' to input 'n'" in result.shared_after["call"]["error"]

    @pytest.mark.trace_files
    def test_default_routing_fails_the_run_with_the_placed_diagnostic(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Text and JSON carry the Diagnostic placed at the step; a step ran, so resuming with an
        override is a real remedy and the hint stays."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")
        (tmp_path / "home" / ".pflow" / "debug").mkdir(parents=True)
        parent = str(self._parent(tmp_path, "x"))

        as_json = CliRunner(mix_stderr=False).invoke(cli, ["--output-format", "json", parent])
        as_text = CliRunner(mix_stderr=False).invoke(cli, [parent])

        payload = json.loads(as_json.stdout)
        (error,) = payload["errors"]
        assert (
            error["message"] == "Step 'call' passes 'x' to input 'n' of ./child.pflow.md, declared `- type: integer`."
        )
        assert error["context"]["path"] == "nodes[id=call].params.inputs.n"
        assert error["context"]["sub_workflow_path"] == "./child.pflow.md"
        assert error["suggestions"] == ["Pass a whole number from the parent."]
        assert payload["resume_command"].startswith("pflow resume ")
        assert as_text.exit_code == 1
        assert "At: nodes[id=call].params.inputs.n" in as_text.stderr
        assert "In step 'call' sub-workflow:" not in as_text.stderr  # placed at the step, not re-wrapped
        assert "To resume from the failed step: pflow resume " in as_text.stderr


def test_a_parent_string_reaches_a_child_object_parsed_and_a_child_string_as_text(tmp_path: Path) -> None:
    """Ruling (ii) and #686's child half (break 10): the child's declaration decides."""
    (tmp_path / "child.pflow.md").write_text(
        """# Child

Show what arrived.

## Inputs

### obj

An object.

- type: object

### s

Text.

- type: string

## Steps

### show

Show the types.

- type: code
- inputs:
    obj: ${obj}
    s: ${s}

```python code
from typing import Any

obj: Any
s: Any

result: str = f"{type(obj).__name__} {type(s).__name__}:{s}"
```

## Outputs

### out

Shown.

- source: ${show.result}
""",
        encoding="utf-8",
    )
    parent = tmp_path / "parent.pflow.md"
    parent.write_text(
        """# Parent

Pass one declared string twice.

## Inputs

### text

JSON text.

- type: string

## Steps

### call

Call the child.

- type: workflow
- workflow: ./child.pflow.md
- inputs:
    obj: ${text}
    s: ${text}
""",
        encoding="utf-8",
    )

    result = WorkflowRunner().run(str(parent), {"text": '{"a":1}'}, RunnerConfig(trace_enabled=False))

    assert result.success, result.errors
    assert result.shared_after["call"]["out"] == 'dict str:{"a":1}'


def test_a_none_from_the_parent_is_absence(tmp_path: Path) -> None:
    """A parent value that resolves to None means "not provided": an optional child input takes its
    fallback; a required one is the routable "requires input" problem."""
    _child(tmp_path, n_spec="- default: 3")
    optional = _parent(tmp_path, items="[null]", inputs="{n: ${item}, limit: ${item}}")
    assert _outputs(_run(optional)) == {0: "3 3"}

    _child(tmp_path)
    required = _parent(tmp_path, items='[null, "4"]', inputs="{n: ${item}}", batch="    error_handling: continue")
    result = _run(required)
    assert _outputs(result) == {1: "4 3"}
    (record,) = result.shared_after["call"]["errors"]
    (diagnostic,) = record["child_failure"]["diagnostics"]
    assert diagnostic["message"] == "./child.pflow.md requires input 'n': A whole number."
    assert diagnostic["context"]["path"] == "nodes[id=call].params.inputs.n"


class TestTheLegacyBundleKey:
    """`build_subworkflow_diagnostics` still reads the bundle a trace recorded before the input
    boundary existed carries (`template_diagnostic`), as a resume restores it."""

    @staticmethod
    def _template_diagnostic() -> Diagnostic:
        return Diagnostic(
            severity=Severity.ERROR,
            message="Unresolved variables in parameter 'env': ${producer.stdout}",
            title="Template Resolution Failed",
            node_id="consumer",
            source="runtime",
            context={"category": "template_error", "unresolved_references": [{"template": "${producer.stdout}"}]},
        )

    def test_a_legacy_bundle_keeps_its_rich_template_fields(self) -> None:
        """Only a hand-written bundle has the legacy shape (the writer emits `diagnostics`, pinned
        end-to-end by `test_failed_node_invariant`): a resumed pre-120 trace restores it."""
        bundle: dict[str, Any] = {
            "workflow_path": "/w/child.pflow.md",
            "failed_node": "consumer",
            "failures": {},
            "template_diagnostic": self._template_diagnostic().to_dict(),
        }

        (diagnostic,) = build_subworkflow_diagnostics(bundle, "sub")

        assert (
            diagnostic.message
            == "In step 'sub' sub-workflow: Unresolved variables in parameter 'env': ${producer.stdout}"
        )
        assert diagnostic.context is not None
        assert diagnostic.context["unresolved_references"] == [{"template": "${producer.stdout}"}]
        assert diagnostic.context["sub_workflow_step"] == "sub"


def test_a_batch_record_states_the_input_sentence_once_and_other_child_failures_keep_their_lines(
    tmp_path: Path,
) -> None:
    """Checkpoint §1.5: the item headline IS the placed sentence, so its detail lines (`At:`, the fix)
    follow without repeating it. A failure INSIDE the child keeps its own provenance-wrapped lines."""
    (tmp_path / "child.pflow.md").write_text(
        """# Child

Fail inside for 8.

## Inputs

### n

A whole number.

- type: integer

## Steps

### check

Refuse 8.

- type: shell
- env:
    N: ${n}

```shell command
test "$N" != 8
```
""",
        encoding="utf-8",
    )
    parent = _parent(tmp_path, items='["7","x","8"]', inputs="{n: ${item}}", batch="    error_handling: continue")

    result = CliRunner(mix_stderr=False).invoke(cli, [str(parent)])

    sentence = "Step 'call' passes 'x' to input 'n' of ./child.pflow.md, declared `- type: integer`."
    assert result.exit_code == 0, result.stderr
    assert result.stderr.count(sentence) == 1
    assert f"  [1] {sentence}\n      item: 'x'\n      At: nodes[id=call].params.inputs.n\n" in result.stderr
    assert "      → Pass a whole number from the parent." in result.stderr
    assert "      In step 'call' sub-workflow: Command failed with exit code 1" in result.stderr  # item 2, inside


def test_a_childs_fallback_inputs_are_inputs_not_outputs(tmp_path: Path) -> None:
    """Without declared `## Outputs` the child's store is mirrored back minus its inputs — and an
    input resolved from its default is an input like a supplied one (both run and plan read the
    typed, complete per-call inputs). Presence half: the child's own step output IS exposed."""
    (tmp_path / "child.pflow.md").write_text(
        CHILD.format(n_spec="- required: true").split("## Outputs")[0], encoding="utf-8"
    )
    parent = _parent(tmp_path, items='["7"]', inputs="{n: ${item}}")

    (exposed,) = _run(parent).shared_after["call"]["results"]

    assert exposed["show"]["result"] == "7 3"
    assert "limit" not in exposed and "n" not in exposed

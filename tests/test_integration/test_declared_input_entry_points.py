"""Every entry path types a workflow input by its declaration — once, where the value enters (Task 120 PB).

The CLI argument, piped stdin, the environment, a declared default, a resumed run's recorded inputs, an MCP
call and the analyzer all reach the one input boundary (``prepare_inputs``) with the value's SOURCE, so a
value that does not fit fails with an error naming where it came from, and a value that fits arrives typed
— never guessed by the CLI parser, never re-typed downstream. The coercer's own tables live in
``tests/test_core/test_param_coercion.py``; this file drives the real surfaces.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import yaml
from click.testing import CliRunner

from pflow.cli.main import cli
from pflow.core.exceptions import WorkflowValidationError
from pflow.core.prompt_cache_analysis import analyze
from pflow.core.workflow.manager import WorkflowManager
from pflow.execution.result import RunnerConfig
from pflow.execution.runner import WorkflowRunner
from pflow.mcp_server.services.execution_service import ExecutionService
from tests.conftest import set_isolated_home

# A string input into a shell `env:` — the bytes the command sees are the bytes typed (#687).
ECHO_WF = """# Echo

A string input echoed by a shell step.

## Inputs

### text

The text.

- type: string
- required: true
- stdin: true

## Steps

### echo

Echo it.

- type: shell
- env:
    TEXT: ${text}

```shell command
printf '%s' "$TEXT"
```

## Outputs

### out

The echoed text.

- source: ${echo.stdout}
"""

# One input per declared type; `ratio` reaches only a shell `env:` — no annotated consumer would catch it.
TYPED_WF = """# Typed

One input of each declared type.

## Inputs

### topics

Topics.

- type: array
- required: true

### count

Count.

- type: integer
- default: 3

### flag

Flag.

- type: boolean
- default: false

### ratio

Ratio.

- type: number
- required: false

### cfg

Config.

- type: object
- required: false

## Steps

### show

Show the types.

- type: code
- inputs:
    topics: ${topics}
    count: ${count}
    flag: ${flag}

```python code
topics: list
count: int
flag: bool

result: str = f"{topics!r} {count!r} {flag!r}"
```

### ratio_env

Bind the ratio and the config as text.

- type: shell
- env:
    R: ${ratio}
    C: ${cfg}

```shell command
printf 'ratio=%s cfg=%s' "$R" "$C"
```

## Outputs

### out

Shown.

- source: ${show.result}
"""

# An env-or-default integer (f2): the environment variable must win over the default.
PORT_WF = """# Port

An integer with a default.

## Inputs

### port

Port.

- type: integer
- required: false
- default: 8080

## Steps

### show

Show the port and its type.

- type: code
- inputs:
    port: ${port}

```python code
port: int

result: str = f"{port!r}"
```

## Outputs

### out

Shown.

- source: ${show.result}
"""

# A resumable failure at step 2: `mode` gates it; `count`/`zip` are replayed from the recorded run.
RESUME_WF = """# Resume

A step that fails until mode is ok, reading two recorded inputs.

## Inputs

### count

Count.

- type: integer
- required: true

### zip

Zip code.

- type: string
- required: false

### mode

Gate.

- type: string
- required: true

## Steps

### first

Upstream.

- type: shell

```shell command
printf 'up'
```

### second

Fails unless mode is ok; shows the types it received.

- type: code
- inputs:
    count: ${count}
    zip: ${zip}
    mode: ${mode}

```python code
count: int
zip: str | None
mode: str

if mode != "ok":
    raise ValueError("not yet")
result: str = f"{count!r} {zip!r}"
```

## Outputs

### out

Shown.

- source: ${second.result}
"""

# `any` and an optional untyped value — MCP passes typed JSON through untouched.
ANY_WF = """# Any

An any input and an optional string.

## Inputs

### data

Anything.

- type: any
- required: true

### opt

Optional text.

- type: string
- required: false

## Steps

### show

Show the types.

- type: code
- inputs:
    data: ${data}
    opt: ${opt}

```python code
from typing import Any

data: Any
opt: str | None

result: str = f"{type(data).__name__}:{data!r} {opt!r}"
```

## Outputs

### out

Shown.

- source: ${show.result}
"""


def _write(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / f"{name}.pflow.md"
    path.write_text(text, encoding="utf-8")
    return path


def _invoke(*args: str, stdin: str | None = None) -> Any:
    return CliRunner(mix_stderr=False).invoke(cli, list(args), input=stdin)


def _json_errors(result: Any) -> list[dict[str, Any]]:
    payload = json.loads(result.stdout)
    assert payload["success"] is False, payload
    return payload["errors"]  # type: ignore[no-any-return]


def _input_error(error: dict[str, Any]) -> tuple[str, str, str, str]:
    context = error["context"]
    return context["input"], context["declared_type"], context["received"], context["source"]


class TestTheCliPassesTextTheDeclarationTypes:
    """#687: the CLI parser no longer guesses; a `string` input arrives byte-identical."""

    @pytest.mark.parametrize("text", ["02134", "1.10", "TRUE", "1e3", '{"a":1,"b":[1,2]}', " 42"])
    def test_an_argument_reaches_the_command_byte_identical(self, tmp_path: Path, text: str) -> None:
        result = _invoke("-p", str(_write(tmp_path, "echo", ECHO_WF)), f"text={text}")
        assert result.exit_code == 0, result.stderr
        assert result.stdout.rstrip("\n") == text

    @pytest.mark.parametrize("text", ["02134", '{"a":1,"b":[1,2]}'])
    def test_piped_stdin_delivers_the_same_bytes_as_the_argument(self, tmp_path: Path, text: str) -> None:
        workflow = str(_write(tmp_path, "echo", ECHO_WF))
        with patch("pflow.core.shell_integration.stdin_has_data", return_value=True):
            piped = _invoke("-p", workflow, stdin=text)
        argument = _invoke("-p", workflow, f"text={text}")
        assert piped.exit_code == argument.exit_code == 0, piped.stderr
        assert piped.stdout == argument.stdout
        assert piped.stdout.rstrip("\n") == text

    def test_stdin_that_fails_its_type_is_named_as_stdin(self, tmp_path: Path) -> None:
        workflow = str(_write(tmp_path, "count", ECHO_WF.replace("- type: string", "- type: integer")))
        with patch("pflow.core.shell_integration.stdin_has_data", return_value=True):
            refused = _invoke("--output-format", "json", workflow, stdin="abc\n")
            accepted = _invoke("-p", workflow, stdin="42\n")  # surrounding whitespace is not the value
        assert refused.exit_code == 1
        (error,) = _json_errors(refused)
        assert _input_error(error)[0] == "text"
        assert error["context"]["source"] == "stdin"
        assert error["suggestions"] == ["Pipe a whole number (e.g. 3), or pass text=3 on the command line"]
        assert accepted.exit_code == 0, accepted.stderr
        assert accepted.stdout.rstrip("\n") == "42"

    def test_an_argument_beats_stdin_and_is_labelled_an_argument(self, tmp_path: Path) -> None:
        workflow = str(_write(tmp_path, "count", ECHO_WF.replace("- type: string", "- type: integer")))
        with patch("pflow.core.shell_integration.stdin_has_data", return_value=True):
            refused = _invoke("--output-format", "json", workflow, "text=abc", stdin="42\n")
        (error,) = _json_errors(refused)
        assert _input_error(error) == ("text", "integer", "abc", "argument")

    def test_any_input_from_the_command_line_types_only_what_reads_back(self, tmp_path: Path) -> None:
        workflow = str(_write(tmp_path, "any", ANY_WF))
        shown = {token: _invoke("-p", workflow, f"data={token}").stdout.rstrip("\n") for token in ["02134", "42"]}
        assert shown == {"02134": "str:'02134' None", "42": "int:42 None"}


class TestAValueThatDoesNotFitFailsAtTheBoundary:
    """Breaks 1, 4, 5, 6, 7: a wrong-typed value is an error naming the input, never a warning or a pass."""

    @pytest.mark.parametrize(
        ("token", "expected"),
        [
            ("topics=tea", ("topics", "array", "tea", "argument")),
            ("count=3.0", ("count", "integer", "3.0", "argument")),
            ("count=1e3", ("count", "integer", "1e3", "argument")),
            ("count=true", ("count", "integer", "true", "argument")),
            ("flag=maybe", ("flag", "boolean", "maybe", "argument")),
            ("cfg=[1,2]", ("cfg", "object", "[1,2]", "argument")),
            # No annotated consumer reads `ratio` — before, this exited 0 with the string flowing on.
            ("ratio=abc", ("ratio", "number", "abc", "argument")),
        ],
    )
    def test_the_run_exits_1_with_the_typed_input_error(
        self, tmp_path: Path, token: str, expected: tuple[str, ...]
    ) -> None:
        workflow = str(_write(tmp_path, "typed", TYPED_WF))
        topics = [] if token.startswith("topics=") else ['topics=["a"]']
        result = _invoke("--output-format", "json", workflow, *topics, token)
        assert result.exit_code == 1
        (error,) = _json_errors(result)
        assert _input_error(error) == expected
        assert error["title"] == "Invalid input value"
        assert error["context"]["path"] == f"inputs.{expected[0]}"
        declared, received = expected[1], expected[2]
        assert error["message"] == (
            f"Input '{expected[0]}' is declared `- type: {declared}` but received '{received}' from the command line."
        )

    def test_values_that_fit_arrive_typed(self, tmp_path: Path) -> None:
        workflow = str(_write(tmp_path, "typed", TYPED_WF))
        result = _invoke("-p", workflow, 'topics=["a"]', "count=007", "flag=YES", "ratio=2.5", 'cfg={"k":1}')
        assert result.exit_code == 0, result.stderr
        assert result.stdout.rstrip("\n") == "['a'] 7 True"


@pytest.fixture
def pflow_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Traces land under ``Path.home()`` — the resume hint and ``pflow resume`` read them there."""
    home = tmp_path / "home"
    (home / ".pflow" / "debug").mkdir(parents=True)
    monkeypatch.setattr(Path, "home", lambda: home)
    return home


@pytest.mark.trace_files
class TestSeveralBadInputsAndNoResumeHint:
    """Each bad input is its own error; a failure before any step offers no resume (traces ARE written here,
    so the hint's absence is not an artefact — the presence row proves the medium shows it)."""

    @pytest.mark.usefixtures("pflow_home")
    def test_two_bad_inputs_are_two_errors_each_with_its_own_path_and_fix(self, tmp_path: Path) -> None:
        workflow = str(_write(tmp_path, "typed", TYPED_WF))
        as_json = _invoke("--output-format", "json", workflow, 'topics=["a"]', "count=3.0", "flag=maybe")
        as_text = _invoke(workflow, 'topics=["a"]', "count=3.0", "flag=maybe")

        errors = _json_errors(as_json)
        assert [(e["context"]["path"], e["suggestions"]) for e in errors] == [
            ("inputs.count", ["Pass a whole number (e.g. 3): count=3"]),
            ("inputs.flag", ["Pass true or false (also yes/no, 1/0): flag=true"]),
        ]
        assert "resume_command" not in json.loads(as_json.stdout)  # nothing ran: nothing to resume
        assert as_text.exit_code == 1
        assert "Error 1: Invalid input value" in as_text.stderr
        assert "Error 2: Invalid input value" in as_text.stderr
        assert "pflow resume" not in as_text.stderr

    @pytest.mark.usefixtures("pflow_home")
    def test_a_failure_after_a_step_ran_does_offer_the_resume(self, tmp_path: Path) -> None:
        workflow = str(_write(tmp_path, "resume", RESUME_WF))
        as_json = _invoke("--output-format", "json", workflow, "count=3", "mode=no")
        as_text = _invoke(workflow, "count=3", "mode=no")
        assert json.loads(as_json.stdout)["resume_command"].startswith("pflow resume ")
        assert "To resume from the failed step: pflow resume " in as_text.stderr


class TestEnvironmentAndDefaults:
    """f2: the environment beats the declared default, and an env value that does not fit names the variable."""

    def test_the_environment_wins_over_the_default(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        workflow = str(_write(tmp_path, "port", PORT_WF))
        default = _invoke("-p", workflow)
        monkeypatch.setenv("port", "9090")
        from_env = _invoke("-p", workflow)
        assert default.stdout.rstrip("\n") == "8080"
        assert from_env.stdout.rstrip("\n") == "9090"

    def test_a_bad_environment_value_names_the_variable_and_an_argument_beats_it(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        workflow = str(_write(tmp_path, "port", PORT_WF))
        monkeypatch.setenv("port", "abc")
        refused = _invoke("--output-format", "json", workflow)
        argument = _invoke("-p", workflow, "port=1")

        (error,) = _json_errors(refused)
        assert _input_error(error) == ("port", "integer", "abc", "env")
        assert "from the environment variable port" in error["message"]
        assert error["suggestions"] == ["export port=3, or pass port=3 (an argument wins over the environment)"]
        assert argument.exit_code == 0, argument.stderr
        assert argument.stdout.rstrip("\n") == "1"


@pytest.mark.e2e
class TestASettingsValueIsLabelledSettings:
    """`pflow run` copies settings.env into the process environment at startup (`inject_settings_env_vars`), so
    the boundary must still name settings — not "the environment variable" — for a value that lives there.
    Real subprocesses: the copy is skipped under `PYTEST_CURRENT_TEST`, which the child must not inherit."""

    @pytest.fixture
    def cli_env(self, tmp_path: Path, prepared_subprocess_env: dict[str, str]) -> dict[str, str]:
        home = tmp_path / "home"
        (home / ".pflow").mkdir(parents=True)
        registry = Path(prepared_subprocess_env["HOME"]) / ".pflow" / "registry.json"
        (home / ".pflow" / "registry.json").write_text(registry.read_text(encoding="utf-8"), encoding="utf-8")
        env = {k: v for k, v in prepared_subprocess_env.items() if k not in ("PYTEST_CURRENT_TEST", "port")}
        set_isolated_home(env, home)
        return env

    @staticmethod
    def _pflow(env: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(  # noqa: S603
            [sys.executable, "-m", "pflow.cli", *args], capture_output=True, text=True, encoding="utf-8", env=env
        )

    def test_a_bad_settings_value_names_settings_and_the_settings_fix(
        self, tmp_path: Path, cli_env: dict[str, str]
    ) -> None:
        workflow = str(_write(tmp_path, "port", PORT_WF))
        assert self._pflow(cli_env, "settings", "set-env", "port", "abc").returncode == 0
        result = self._pflow(cli_env, workflow)
        assert result.returncode == 1
        assert "Input 'port' is declared `- type: integer` but received 'abc' from settings.env." in result.stderr
        assert "→ pflow settings set-env port 3, or pass port=3" in result.stderr

    def test_an_exported_variable_is_still_the_environment_even_with_a_setting(
        self, tmp_path: Path, cli_env: dict[str, str]
    ) -> None:
        workflow = str(_write(tmp_path, "port", PORT_WF))
        assert self._pflow(cli_env, "settings", "set-env", "port", "abc").returncode == 0
        result = self._pflow({**cli_env, "port": "xyz"}, workflow)
        assert result.returncode == 1
        assert "received 'xyz' from the environment variable port." in result.stderr
        assert "from settings.env" not in result.stderr


class TestValidateOnlyChecksTheSuppliedValues:
    """#297's type/extras half: `--validate-only` with values refuses what the run refuses, in the same words."""

    def test_bad_values_fail_validation_with_the_runs_own_diagnostics(self, tmp_path: Path) -> None:
        workflow = str(_write(tmp_path, "typed", TYPED_WF))
        validated = _invoke("--validate-only", "--output-format", "json", workflow, "topics=tea", "count=abc")
        ran = _invoke("--output-format", "json", workflow, "topics=tea", "count=abc")

        assert validated.exit_code == ran.exit_code == 1
        validated_errors = [(e["message"], e["context"]["path"]) for e in _json_errors(validated)]
        assert validated_errors == [(e["message"], e["context"]["path"]) for e in _json_errors(ran)]
        assert [path for _, path in validated_errors] == ["inputs.topics", "inputs.count"]

    def test_missing_inputs_are_tolerated_and_undeclared_ones_are_not(self, tmp_path: Path) -> None:
        workflow = str(_write(tmp_path, "typed", TYPED_WF))
        nothing = _invoke("--validate-only", workflow)
        good = _invoke("--validate-only", workflow, 'topics=["a"]')
        bogus = _invoke("--validate-only", "--output-format", "json", workflow, "BOGUS=x")

        assert nothing.exit_code == 0, nothing.stdout
        assert good.exit_code == 0, good.stdout
        assert bogus.exit_code == 1
        assert [e["context"]["path"] for e in _json_errors(bogus)] == ["inputs.BOGUS"]

    def test_each_declared_input_reports_before_the_undeclared_ones(self, tmp_path: Path) -> None:
        workflow = str(_write(tmp_path, "typed", TYPED_WF))
        result = _invoke("--validate-only", "--output-format", "json", workflow, "BOGUS=x", "topics=tea")
        assert [e["context"]["path"] for e in _json_errors(result)] == ["inputs.topics", "inputs.BOGUS"]

    def test_a_declaration_problem_is_reported_once_by_the_validator(self) -> None:
        """Two `stdin: true` inputs are the validator's finding; checking the supplied values must not
        report the same problem a second time in other words."""
        both_stdin = {"type": "string", "required": False, "stdin": True}
        ir = {
            "inputs": {"a": both_stdin, "b": both_stdin},
            "nodes": [{"id": "s", "type": "shell", "params": {"command": "true", "env": {"A": "${a}", "B": "${b}"}}}],
            "edges": [],
        }
        result = WorkflowRunner().validate(ir, {"a": "x"})
        stdin_errors = [d.message for d in result.errors if "`- stdin: true`" in d.message]
        assert len(stdin_errors) == 1, stdin_errors
        assert stdin_errors[0].startswith("Multiple inputs marked `- stdin: true`: a, b")


def _failed_run(workflow: Path, *args: str) -> tuple[str, Path]:
    """Run ``workflow`` to a failure at a later step; return its execution id and trace file."""
    result = _invoke(str(workflow), *args)
    assert result.exit_code == 1, result.stderr
    run_id = result.stderr.split("pflow resume ", 1)[1].split()[0]
    (trace,) = (Path.home() / ".pflow" / "debug").glob("workflow-trace-*.json")
    return run_id, trace


def _record(trace: Path, **inputs: Any) -> None:
    """Rewrite the trace's recorded inputs — the shape a lenient-era run left behind."""
    meta, *rest = trace.read_text(encoding="utf-8").splitlines()
    record = json.loads(meta)
    record["inputs"] = {**record["inputs"], **inputs}
    trace.write_text("\n".join([json.dumps(record), *rest]) + "\n", encoding="utf-8")


@pytest.mark.trace_files
class TestResumeReplaysThroughTheBoundary:
    """A resumed run's recorded inputs are typed again (idempotent); a lenient-era value names the override."""

    @pytest.fixture(autouse=True)
    def _home(self, pflow_home: Path) -> None:
        """Every resume test reads the traces its failed run wrote."""

    def test_a_lenient_era_value_fails_naming_the_run_to_resume(self, tmp_path: Path) -> None:
        run_id, trace = _failed_run(_write(tmp_path, "resume", RESUME_WF), "count=3", "mode=no")
        _record(trace, count="abc")

        refused = _invoke("resume", run_id, "mode=ok", "--force", "--output-format", "json")
        overridden = _invoke("resume", run_id, "mode=ok", "count=4", "--force", "-p")

        (error,) = _json_errors(refused)
        assert _input_error(error) == ("count", "integer", "abc", "recorded")
        assert "recorded by the run being resumed" in error["message"]
        assert error["suggestions"] == [f"Override it: pflow resume {run_id} count=3"]
        assert overridden.exit_code == 0, overridden.stderr  # the fix line's remedy works
        assert overridden.stdout.rstrip("\n") == "4 None"

    def test_an_override_is_a_command_line_argument_not_a_recorded_value(self, tmp_path: Path) -> None:
        run_id, _trace = _failed_run(_write(tmp_path, "resume", RESUME_WF), "count=3", "mode=no")
        refused = _invoke("resume", run_id, "mode=ok", "count=abc", "--force", "--output-format", "json")
        (error,) = _json_errors(refused)
        assert _input_error(error) == ("count", "integer", "abc", "argument")

    def test_recorded_values_that_fit_replay_typed(self, tmp_path: Path) -> None:
        run_id, trace = _failed_run(_write(tmp_path, "resume", RESUME_WF), "count=3", "mode=no")
        _record(trace, count="7", zip=99)  # integer text → 7; a scalar for a string → its text

        result = _invoke("resume", run_id, "mode=ok", "--force", "-p")
        assert result.exit_code == 0, result.stderr
        assert result.stdout.rstrip("\n") == "7 '99'"

    def test_a_resume_override_arrives_byte_identical(self, tmp_path: Path) -> None:
        run_id, _trace = _failed_run(_write(tmp_path, "resume", RESUME_WF), "count=3", "mode=no")
        result = _invoke("resume", run_id, "mode=ok", "zip=0099", "--force", "-p")
        assert result.exit_code == 0, result.stderr
        assert result.stdout.rstrip("\n") == "3 '0099'"

    def test_an_only_run_delivers_the_override_byte_identical(self, tmp_path: Path) -> None:
        workflow = str(_write(tmp_path, "resume", RESUME_WF))
        assert _invoke(workflow, "count=3", "mode=ok").exit_code == 0
        result = _invoke("-p", workflow, "--only", "second", "count=3", "mode=ok", "zip=0099")
        assert result.exit_code == 0, result.stderr
        assert result.stdout.rstrip("\n") == "3 '0099'"


class TestMcpCallsPassTypedJson:
    """MCP values arrive as typed JSON: checked by the declaration, labelled `call`, never inferred."""

    def test_a_float_for_an_integer_is_refused_with_the_json_shaped_fix(self, tmp_path: Path) -> None:
        workflow = str(_write(tmp_path, "typed", TYPED_WF))
        with pytest.raises(RuntimeError) as refused:
            ExecutionService.execute_workflow(workflow, {"topics": ["a"], "count": 3.0})
        text = str(refused.value)
        assert "Input 'count' is declared `- type: integer` but received 3.0 in the call's parameters." in text
        assert 'Pass a whole number: "count": 3' in text

    def test_null_is_absence(self, tmp_path: Path) -> None:
        workflow = str(_write(tmp_path, "typed", TYPED_WF))
        with pytest.raises(RuntimeError, match="Workflow requires input 'topics'"):
            ExecutionService.execute_workflow(workflow, {"topics": None})
        ran = ExecutionService.execute_workflow(workflow, {"topics": ["a"], "flag": None, "count": "7"})
        assert "['a'] 7 False" in ran  # flag: its default; count: integer text typed

    def test_an_any_value_is_left_as_sent(self, tmp_path: Path) -> None:
        workflow = str(_write(tmp_path, "any", ANY_WF))
        ran = ExecutionService.execute_workflow(workflow, {"data": "42", "opt": None})
        assert "str:'42' None" in ran  # the CLI would infer 42 (presence half: TestTheCliPassesText…)

    def test_json_text_for_a_declared_string_reaches_the_step_as_text(self, tmp_path: Path) -> None:
        """#686 through MCP `workflow_execute`: a declared `string` holding JSON text is never parsed on the way
        to a step; the same text for an `any` input is (the presence half — the resolver's parse still exists)."""
        as_string = str(_write(tmp_path, "s", ANY_WF.replace("- type: any", "- type: string")))
        assert "str:'{\"a\":1}' None" in ExecutionService.execute_workflow(as_string, {"data": '{"a":1}'})
        as_any = str(_write(tmp_path, "a", ANY_WF))
        assert "dict:{'a': 1} None" in ExecutionService.execute_workflow(as_any, {"data": '{"a":1}'})


class TestAnalysisTypesTheSuppliedValuesFirst:
    """`analyze-cache` checks supplied values loudly before prediction; omitted inputs stay legal (DD#35)."""

    def test_the_cli_fails_in_text_and_in_the_json_envelope(self, tmp_path: Path) -> None:
        workflow = str(_write(tmp_path, "typed", TYPED_WF))
        as_text = _invoke("analyze-cache", workflow, "count=abc")
        as_json = _invoke("analyze-cache", workflow, "count=abc", "--format=json")
        omitted = _invoke("analyze-cache", workflow, "--no-trace-autoload")

        message = "Input 'count' is declared `- type: integer` but received 'abc' from the command line."
        assert as_text.exit_code == as_json.exit_code == 1
        assert message in as_text.stderr
        assert as_text.stderr.count("count=3") == 1  # the fix line once, not echoed again as "Suggestion:"
        envelope = json.loads(as_json.stdout)["error"]
        assert envelope == {
            "id": "analyze-cache.invalid-parameters",
            "message": message,
            "suggestion": "Pass a whole number (e.g. 3): count=3",
        }
        assert omitted.exit_code == 0, omitted.stderr  # `topics` is required and omitted

    def test_mcp_analysis_raises_the_structured_diagnostic(self, tmp_path: Path) -> None:
        workflow = str(_write(tmp_path, "typed", TYPED_WF))
        with pytest.raises(WorkflowValidationError) as refused:
            ExecutionService.analyze_cache(workflow, {"count": "abc"})
        (diagnostic,) = refused.value.validation_errors
        assert diagnostic.context is not None
        assert (diagnostic.context["input"], diagnostic.context["source"]) == ("count", "call")

    @staticmethod
    def _prompt_tokens(prompt: str, declared: str, value: str) -> int:
        ir = {
            "inputs": {"data": {"type": declared}},
            "nodes": [
                {"id": "ask", "type": "llm", "params": {"model": "anthropic/claude-sonnet-4-5", "prompt": prompt}}
            ],
        }
        result = analyze(ir, parameters={"data": value}, auto_load_trace=False, memo_cache=None)
        (row,) = result.per_call
        assert row.input_tokens_estimated is not None
        return row.input_tokens_estimated

    # Long enough that a resolved reference dominates the estimate; an unresolved one counts only "Say".
    _WORDS = "word " * 300

    def test_a_supplied_value_is_typed_before_its_references_resolve(self) -> None:
        """CLI text for an `object` becomes a dict, so `${data.k}` reads a field; JSON text in a declared
        `object` is never parsed, so the same reference would stay unresolved if the value stayed text."""
        typed = self._prompt_tokens("Say ${data.k}", "object", json.dumps({"k": self._WORDS}))
        unresolved = self._prompt_tokens("Say ${data.nope}", "object", json.dumps({"k": self._WORDS}))
        assert typed > 250 > unresolved

    def test_a_json_text_descendant_of_a_declared_object_is_unresolved_as_at_run_time(self) -> None:
        value = json.dumps({"payload": json.dumps({"a": self._WORDS})})
        protected = self._prompt_tokens("Say ${data.payload.a}", "object", value)
        whole_text = self._prompt_tokens("Say ${data.payload}", "object", value)  # the text itself resolves
        walked = self._prompt_tokens("Say ${data.payload.a}", "any", value)  # `any` keeps the walk parse
        assert whole_text > 250 and walked > 250
        assert protected < 10

    @pytest.mark.parametrize("scoped", [False, True], ids=["root", "workflow-scoped"])
    def test_a_ref_resolved_from_parameters_never_parses_a_declared_inputs_text(self, scoped: bool) -> None:
        """The per-ref resolvers token estimates read (``resolve_ref_value`` and its workflow-scoped twin)
        carry the declarations too: the protected ref is a miss, its text and an `any` twin resolve."""
        from pflow.core.prompt_cache_analysis.context import AnalysisContext

        value = {"payload": json.dumps({"a": "word"})}

        def resolve(declared: str, ref: str) -> Any:
            ctx = AnalysisContext.build(
                workflow_ir={"inputs": {"data": {"type": declared}}, "nodes": []},
                parameters={"data": value},
                workflow_path="wf.pflow.md",
            )
            if scoped:
                return ctx.resolve_ref_value_in_workflow(ref, workflow_path="wf.pflow.md")
            return ctx.resolve_ref_value(ref)

        assert resolve("object", "data.payload.a") is None
        assert resolve("object", "data.payload") == value["payload"]
        assert resolve("any", "data.payload.a") == "word"


def test_last_execution_params_records_the_typed_values(tmp_path: Path) -> None:
    manager = WorkflowManager(workflows_dir=tmp_path / "workflows")
    manager.save("typed", TYPED_WF)
    path = manager.get_path("typed")

    result = WorkflowRunner().run(
        path,
        {"topics": '["a"]', "count": "3"},
        RunnerConfig(trace_enabled=False),
        workflow_manager=manager,
        workflow_name="typed",
    )

    assert result.success, result.errors
    frontmatter = yaml.safe_load(Path(path).read_text(encoding="utf-8").split("---", 2)[1])
    recorded = frontmatter["last_execution_params"]
    assert (recorded["topics"], recorded["count"], recorded["flag"]) == (["a"], 3, False)


@pytest.mark.e2e
@pytest.mark.skipif(sys.platform == "win32", reason="Unix pipe")
def test_a_real_pipe_delivers_the_bytes_typed(tmp_path: Path, prepared_subprocess_env: dict[str, str]) -> None:
    workflow = _write(tmp_path, "echo", ECHO_WF)
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "pflow.cli", "-p", str(workflow)],
        input='{"a":1,"b":[1,2]}',
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=prepared_subprocess_env,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.rstrip("\n") == '{"a":1,"b":[1,2]}'

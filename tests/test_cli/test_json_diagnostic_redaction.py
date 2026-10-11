"""Sensitive-named values never reach a `--output-format json` document (#776, #781).

A real local HTTP server answers 401 with a `Set-Cookie` header and an `access_token` body; the
workflow runs through the CLI entry point. Absence is checked against the WHOLE stdout (every
path, however deep), presence against the specific fields an agent reads.
"""

from __future__ import annotations

import ast
import json
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from pflow.cli.main import main

SECRET_TOKEN = "SECRET-TOKEN-456"  # noqa: S105 — test fixture value
SECRET_COOKIE = "session=SECRET-COOKIE-123; HttpOnly"  # noqa: S105 — test fixture value
JSON_BODY = json.dumps({"access_token": SECRET_TOKEN, "error": "nope"}).encode()
TEXT_BODY = b"Unauthorized: sign in first"


OK_BODY = json.dumps({"ok": True}).encode()


class _AuthFailureHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/ok":
            self._answer(200, OK_BODY, "application/json")
            return
        body, content_type = (TEXT_BODY, "text/plain") if self.path == "/text" else (JSON_BODY, "application/json")
        self._answer(401, body, content_type)

    def _answer(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        if status == 401:  # a successful item's response is the workflow's own output, shown in full
            self.send_header("Set-Cookie", SECRET_COOKIE)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 — stdlib signature
        pass


@pytest.fixture
def auth_server() -> Iterator[str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _AuthFailureHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


def _fetch_step(url: str, extra: str = "") -> str:
    return f"### fetch\n\nFetch the endpoint.\n\n- type: http\n- url: {url}\n{extra}"


def _run_json(tmp_path: Path, steps: str) -> tuple[int, str, dict[str, Any]]:
    workflow = tmp_path / "leak.pflow.md"
    workflow.write_text(f"# Leak\n\nRedaction probe.\n\n## Steps\n\n{steps}", encoding="utf-8")
    result = CliRunner(mix_stderr=False).invoke(main, ["--output-format", "json", str(workflow)])
    return result.exit_code, result.stdout, json.loads(result.stdout)


def _assert_no_secret(stdout: str) -> None:
    assert SECRET_TOKEN not in stdout
    assert "SECRET-COOKIE-123" not in stdout


def _assert_one_representation(entry: dict[str, Any]) -> None:
    """Context stays nested; no context key is copied to the top level."""
    assert "context" in entry
    assert not set(entry["context"]) & set(entry), f"context keys duplicated at top level: {sorted(entry)}"


_REF_HANDLER = (
    "### handle\n\nUse a missing field of the failed fetch.\n\n- type: shell\n- next: end\n"
    '- env: {X: ${fetch.response.nope}}\n\n```shell command\necho "$X"\n```\n'
)


class TestFailureDocument:
    def test_http_401_json_body_is_redacted_everywhere(self, tmp_path: Path, auth_server: str) -> None:
        exit_code, stdout, doc = _run_json(tmp_path, _fetch_step(f"{auth_server}/json"))

        assert exit_code == 1
        _assert_no_secret(stdout)
        error = doc["errors"][0]
        assert doc["error"] == "HTTP 401"
        _assert_one_representation(error)
        assert error == doc["diagnostics"][0]
        context = error["context"]
        assert context["status_code"] == 401
        assert context["raw_response"] == {"access_token": "<REDACTED>", "error": "nope"}
        assert context["response_headers"]["Set-Cookie"] == "<REDACTED>"
        assert context["response_headers"]["Content-Type"] == "application/json"
        assert doc["resume_command"].startswith("pflow resume ")

    def test_http_401_text_body_reports_the_http_failure(self, tmp_path: Path, auth_server: str) -> None:
        # A non-dict body used to crash the named-key sanitizer, replacing "HTTP 401" with an AttributeError.
        exit_code, stdout, doc = _run_json(tmp_path, _fetch_step(f"{auth_server}/text"))

        assert exit_code == 1
        _assert_no_secret(stdout)
        assert doc["error"] == "HTTP 401"
        context = doc["errors"][0]["context"]
        assert context["raw_response"] == TEXT_BODY.decode()
        assert context["response_headers"]["Set-Cookie"] == "<REDACTED>"
        assert "execution" in doc

    def test_failed_reference_carries_redacted_failure_data(self, tmp_path: Path, auth_server: str) -> None:
        # The template-error diagnostic nests the failed fetch's body and headers several levels deep.
        steps = _fetch_step(f"{auth_server}/json", "- on-error: handle\n") + "\n" + _REF_HANDLER
        exit_code, stdout, doc = _run_json(tmp_path, steps)

        assert exit_code == 1
        _assert_no_secret(stdout)
        error = doc["errors"][0]
        assert error["context"]["category"] == "template_error"
        _assert_one_representation(error)
        failure = error["context"]["unresolved_references"][0]["failure"]
        assert failure["data"]["response"] == {"access_token": "<REDACTED>", "error": "nope"}
        assert failure["data"]["response_headers"]["Set-Cookie"] == "<REDACTED>"


class TestDegradedSuccessDocument:
    def test_permissive_warning_is_redacted_and_nested(
        self, tmp_path: Path, auth_server: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PFLOW_TEMPLATE_RESOLUTION_MODE", "permissive")
        steps = _fetch_step(f"{auth_server}/json", "- on-error: handle\n") + "\n" + _REF_HANDLER
        exit_code, stdout, doc = _run_json(tmp_path, steps)

        assert exit_code == 0
        assert doc["status"] == "degraded"
        _assert_no_secret(stdout)
        template_warnings = [w for w in doc["warnings"] if w.get("context", {}).get("category") == "template_error"]
        assert len(template_warnings) == 1
        warning = template_warnings[0]
        _assert_one_representation(warning)
        assert warning in doc["diagnostics"]
        failure = warning["context"]["unresolved_references"][0]["failure"]
        assert failure["data"]["response"] == {"access_token": "<REDACTED>", "error": "nope"}


# A batched sub-workflow step: each item runs `child.pflow.md`, whose fetch hits `${url}`.
_BATCH_PARENT = """### each

Run the child workflow for every URL.

- type: workflow
- workflow: ./child.pflow.md
- inputs:
    url: ${item}

```yaml batch
items: ITEMS
error_handling: continue
```
"""

_CHILD_FETCH = """# Child

Fetch one URL.

## Inputs

### url

The URL to fetch.

- type: string

## Steps

### fetch

Fetch the URL.

- type: http
- url: ${url}
"""


def _write_child(tmp_path: Path, extra_steps: str = "") -> None:
    fetch_extra = "- on-error: handle\n" if extra_steps else ""
    (tmp_path / "child.pflow.md").write_text(_CHILD_FETCH + fetch_extra + extra_steps, encoding="utf-8")


def _batch_parent(*urls: str) -> str:
    return _BATCH_PARENT.replace("ITEMS", json.dumps(list(urls)))


def _child_failure(batch_error: dict[str, Any]) -> dict[str, Any]:
    child_failure = batch_error["child_failure"]
    assert child_failure["failed_node"] == "fetch"
    return child_failure


class TestBatchedSubWorkflowDocument:
    """A failed batch item's `child_failure` carries the child's failure data and diagnostics (#799)."""

    def test_failed_run_redacts_the_child_failure_data(self, tmp_path: Path, auth_server: str) -> None:
        _write_child(tmp_path)
        exit_code, stdout, doc = _run_json(tmp_path, _batch_parent(f"{auth_server}/json", f"{auth_server}/json"))

        assert exit_code == 1
        _assert_no_secret(stdout)
        details = doc["execution"]["steps"][0]["batch_error_details"]
        assert len(details) == 2
        for detail in details:
            data = _child_failure(detail)["failures"]["fetch"]["data"]
            assert data["response"] == {"access_token": "<REDACTED>", "error": "nope"}
            assert data["response_headers"]["Set-Cookie"] == "<REDACTED>"

    def test_failed_run_redacts_the_child_template_diagnostic(self, tmp_path: Path, auth_server: str) -> None:
        # The child's handler quotes the failed fetch, so the bundle also carries a template diagnostic.
        _write_child(tmp_path, "\n" + _REF_HANDLER)
        exit_code, stdout, doc = _run_json(tmp_path, _batch_parent(f"{auth_server}/json"))

        assert exit_code == 1
        _assert_no_secret(stdout)
        child_failure = doc["execution"]["steps"][0]["batch_error_details"][0]["child_failure"]
        diagnostic = child_failure["diagnostics"][0]
        assert diagnostic["context"]["category"] == "template_error"
        failure = diagnostic["context"]["unresolved_references"][0]["failure"]
        assert failure["data"]["response"] == {"access_token": "<REDACTED>", "error": "nope"}
        assert failure["data"]["response_headers"]["Set-Cookie"] == "<REDACTED>"

    def test_partially_failed_run_redacts_result_and_execution(self, tmp_path: Path, auth_server: str) -> None:
        _write_child(tmp_path)
        exit_code, stdout, doc = _run_json(tmp_path, _batch_parent(f"{auth_server}/json", f"{auth_server}/ok"))

        assert exit_code == 0
        _assert_no_secret(stdout)
        detail = doc["execution"]["steps"][0]["batch_error_details"][0]
        assert detail["index"] == 0
        assert _child_failure(detail)["failures"]["fetch"]["data"]["response"]["access_token"] == "<REDACTED>"
        result_error = doc["result"]["each"]["errors"][0]
        assert _child_failure(result_error)["failures"]["fetch"]["data"]["response"]["access_token"] == "<REDACTED>"

    def test_mcp_success_text_redacts_the_child_failure_data(self, tmp_path: Path, auth_server: str) -> None:
        from pflow.mcp_server.services.execution_service import ExecutionService

        _write_child(tmp_path)
        workflow = tmp_path / "leak.pflow.md"
        steps = _batch_parent(f"{auth_server}/json", f"{auth_server}/ok")
        workflow.write_text(f"# Leak\n\nRedaction probe.\n\n## Steps\n\n{steps}", encoding="utf-8")

        text = ExecutionService.execute_workflow(str(workflow))

        _assert_no_secret(text)
        assert '"child_failure"' in text
        assert '"access_token": "<REDACTED>"' in text


_GATED_FINALIZE = (
    "### finalize\n\nA step that needs a human's approval.\n\n- type: shell\n- approval: required\n\n"
    "```shell command\necho done\n```\n"
)
# A permissive run carries the failed fetch's body and headers in a template warning up to the gate.
_LEAK_THEN_GATE = (
    _fetch_step("AUTH_SERVER/json", "- on-error: handle\n")
    + "\n"
    + _REF_HANDLER.replace("- next: end", "- next: finalize")
    + "\n"
    + _GATED_FINALIZE
)


@pytest.fixture
def gated_leak(tmp_path: Path, auth_server: str, monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")  # a paused run persists its trace
    (tmp_path / "home" / ".pflow" / "debug").mkdir(parents=True)
    monkeypatch.setenv("PFLOW_TEMPLATE_RESOLUTION_MODE", "permissive")
    return _LEAK_THEN_GATE.replace("AUTH_SERVER", auth_server)


def _assert_template_warning_redacted(diagnostics: list[dict[str, Any]]) -> None:
    template_warnings = [d for d in diagnostics if d.get("context", {}).get("category") == "template_error"]
    assert len(template_warnings) == 1
    warning = template_warnings[0]
    _assert_one_representation(warning)
    failure = warning["context"]["unresolved_references"][0]["failure"]
    assert failure["data"]["response"] == {"access_token": "<REDACTED>", "error": "nope"}
    assert failure["data"]["response_headers"]["Set-Cookie"] == "<REDACTED>"


@pytest.mark.trace_files
class TestGateDocuments:
    def test_paused_document_is_redacted_everywhere(self, tmp_path: Path, gated_leak: str) -> None:
        # CliRunner stdin is never a TTY, so the gate pauses durably (exit 4).
        exit_code, stdout, doc = _run_json(tmp_path, gated_leak)

        assert exit_code == 4
        assert doc["status"] == "paused"
        _assert_no_secret(stdout)
        _assert_template_warning_redacted(doc["diagnostics"])

    def test_denied_document_is_redacted_everywhere(
        self, tmp_path: Path, gated_leak: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("pflow.execution.gate_prompt.can_prompt", lambda oc: True)
        monkeypatch.setattr("pflow.execution.gate_prompt.click.confirm", lambda *a, **k: False)
        exit_code, stdout, doc = _run_json(tmp_path, gated_leak)

        assert exit_code == 3
        assert doc["status"] == "denied"
        _assert_no_secret(stdout)
        _assert_template_warning_redacted(doc["diagnostics"])
        assert doc["errors"][0]["context"]["category"] == "gate"


_INPUT_AS_INDEX_WORKFLOW = """# Dry leak

An input's value used as a list index.

## Inputs

### items

A list.

- type: array

### api_key

A secret.

- type: string

## Steps

### use

Use an indexed item.

- type: shell
- env: {X: ${items[${api_key}]}}

```shell command
echo "$X"
```
"""


class TestDryRunDocument:
    def test_index_value_from_a_sensitive_input_is_redacted(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # A non-integer index fails in planning; its diagnostic records the index source's value by name.
        monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")
        workflow = tmp_path / "dry.pflow.md"
        workflow.write_text(_INPUT_AS_INDEX_WORKFLOW, encoding="utf-8")
        args = ["--dry-run", "--output-format", "json", str(workflow), "items=[1,2]", "api_key=SECRET-KEY-789"]
        result = CliRunner(mix_stderr=False).invoke(main, args)

        assert "SECRET-KEY-789" not in result.stdout
        doc = json.loads(result.stdout)
        entry = next(e for e in doc["plan"] if e["node_id"] == "use")
        reference = entry["diagnostic"]["context"]["unresolved_references"][0]
        assert reference["index_values"] == {"api_key": "<REDACTED>"}


# The trees that build printed documents. `ui/server.py` answers the web UI's HTTP API, not a printed document.
_PRINTING_TREES = ("cli", "execution/formatters", "mcp_server")
_RAW_SERIALIZERS = frozenset({"to_dict", "to_display_dict"})


def test_printed_documents_never_serialize_a_diagnostic_raw() -> None:
    """Ratchet (#781): a printed document carries `Diagnostic.to_output_dict()`.

    Flags every `.to_dict()` / `.to_display_dict()` call in the printing trees. Only `Diagnostic`
    defines `to_display_dict`; the one other `to_dict` in `src/pflow` is `GateRequest`'s, whose
    printed form is `masked_gate_dict`. The scan reads the AST, so docstrings and comments
    don't trip it.
    """
    src_root = Path(__file__).resolve().parents[2] / "src" / "pflow"
    hits: list[str] = []
    for tree_name in _PRINTING_TREES:
        tree_root = src_root / tree_name
        assert tree_root.is_dir(), f"expected {tree_root}"
        for path in sorted(tree_root.rglob("*.py")):
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                func = getattr(node, "func", None)
                if isinstance(node, ast.Call) and isinstance(func, ast.Attribute) and func.attr in _RAW_SERIALIZERS:
                    hits.append(f"{path.relative_to(src_root)}:{node.lineno}: .{func.attr}()")
    assert not hits, "a printed document serializes raw — use Diagnostic.to_output_dict():\n" + "\n".join(hits)

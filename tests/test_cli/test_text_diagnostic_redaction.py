"""Sensitive-named values never reach a failed reference's TEXT diagnostic (#788).

The JSON half is ``test_json_diagnostic_redaction.py`` (#776). Here a real local HTTP server
answers 401 with an ``access_token`` body and a ``Set-Cookie`` header; a recovery step then
references a field of the failed fetch. Every text surface that renders the resulting
diagnostic is checked whole: CLI stderr (strict and permissive), the MCP ``workflow_execute``
text, and every file ``pflow report`` writes from the run's trace.
"""

from __future__ import annotations

import json
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from pflow.cli.main import main
from pflow.mcp_server.services.execution_service import ExecutionService

SECRET_TOKEN = "SECRET-TOKEN-456"  # noqa: S105 — test fixture value
SECRET_COOKIE = "SECRET-COOKIE-123"  # noqa: S105 — test fixture value
BODY = json.dumps({"access_token": SECRET_TOKEN, "error": "nope"}).encode()
MASKED_RESPONSE = "Response: {'access_token': '<REDACTED>', 'error': 'nope'}"


class _AuthFailureHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self.send_response(401)
        self.send_header("Set-Cookie", f"session={SECRET_COOKIE}; HttpOnly")
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(BODY)))
        self.end_headers()
        self.wfile.write(BODY)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 — stdlib signature
        pass


@pytest.fixture
def workflow(tmp_path: Path) -> Iterator[Path]:
    """A fetch that fails 401 and routes to a step referencing a missing field of its output."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), _AuthFailureHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    path = tmp_path / "leak.pflow.md"
    path.write_text(
        "# Leak\n\nRedaction probe.\n\n## Steps\n\n"
        f"### fetch\n\nFetch the endpoint.\n\n- type: http\n- url: http://127.0.0.1:{server.server_address[1]}/\n"
        "- on-error: rescue\n\n"
        "### rescue\n\nUse a missing field of the failed fetch.\n\n- type: shell\n- next: end\n"
        '- env: {X: ${fetch.response.nope}}\n\n```shell command\necho "$X"\n```\n',
        encoding="utf-8",
    )
    try:
        yield path
    finally:
        server.shutdown()
        server.server_close()


def _assert_masked(text: str) -> None:
    assert SECRET_TOKEN not in text
    assert SECRET_COOKIE not in text
    assert MASKED_RESPONSE in text


@pytest.mark.trace_files
def test_strict_run_stderr_and_every_report_file_are_masked(workflow: Path, tmp_path: Path) -> None:
    report_dir = tmp_path / "report"

    result = CliRunner(mix_stderr=False).invoke(main, [str(workflow), "--report-dir", str(report_dir)])

    assert result.exit_code == 1
    _assert_masked(result.stderr)
    assert SECRET_TOKEN not in result.stdout
    # The strict-mode exception message is the rendered diagnostic; the trace keeps it as the
    # step's free-text ``error``, which the report prints verbatim.
    report_files = {path.name: path.read_text(encoding="utf-8") for path in report_dir.iterdir()}
    for name, text in report_files.items():
        assert SECRET_TOKEN not in text, name
        assert SECRET_COOKIE not in text, name
    rescue_reports = [text for name, text in report_files.items() if name.endswith("-rescue.md")]
    assert len(rescue_reports) == 1
    assert MASKED_RESPONSE in rescue_reports[0]


def test_permissive_run_warning_is_masked(workflow: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PFLOW_TEMPLATE_RESOLUTION_MODE", "permissive")

    result = CliRunner(mix_stderr=False).invoke(main, [str(workflow)])

    assert result.exit_code == 0
    _assert_masked(result.stderr)
    assert SECRET_TOKEN not in result.stdout


def test_mcp_workflow_execute_error_text_is_masked(workflow: Path) -> None:
    with pytest.raises(RuntimeError) as excinfo:
        ExecutionService.execute_workflow(str(workflow))

    _assert_masked(str(excinfo.value))

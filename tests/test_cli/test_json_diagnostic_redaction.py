"""Sensitive-named values never reach a `--output-format json` document (#776).

A real local HTTP server answers 401 with a `Set-Cookie` header and an `access_token` body; the
workflow runs through the CLI entry point. Absence is checked against the WHOLE stdout (every
path, however deep), presence against the specific fields an agent reads.
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

SECRET_TOKEN = "SECRET-TOKEN-456"  # noqa: S105 — test fixture value
SECRET_COOKIE = "session=SECRET-COOKIE-123; HttpOnly"  # noqa: S105 — test fixture value
JSON_BODY = json.dumps({"access_token": SECRET_TOKEN, "error": "nope"}).encode()
TEXT_BODY = b"Unauthorized: sign in first"


class _AuthFailureHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        body, content_type = (TEXT_BODY, "text/plain") if self.path == "/text" else (JSON_BODY, "application/json")
        self.send_response(401)
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

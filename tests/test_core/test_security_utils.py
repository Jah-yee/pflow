"""Word-aware sensitive-parameter detection — the single source of truth all redaction sites defer to.

The earlier raw-substring rule redacted innocent names that merely CONTAINED a sensitive word (``author``
→ matched ``auth``); these pin the word-boundary behavior so real secrets still redact while innocent
look-alikes don't.
"""

from __future__ import annotations

from pathlib import Path

from pflow.core.security_utils import (
    is_sensitive_parameter,
    mask_sensitive_value,
    redact_sensitive,
    sanitize_parameters,
)
from pflow.core.trace_report import generate_report
from tests.shared.trace_jsonl import write_trace_jsonl


class TestIsSensitiveParameter:
    def test_redacts_standard_secret_names(self) -> None:
        for key in (
            "password",
            "passwd",
            "api_key",
            "apikey",
            "api-key",
            "access_token",
            "client_secret",
            "authorization",
            "private_key",
            "secret",
            "token",
            "auth_token",
            "credentials",
        ):
            assert is_sensitive_parameter(key), key

    def test_is_case_insensitive(self) -> None:
        assert is_sensitive_parameter("API_KEY")
        assert is_sensitive_parameter("Password")
        assert is_sensitive_parameter("TOKEN")

    def test_matches_across_delimiters_and_camelcase(self) -> None:
        """A sensitive word as a WHOLE word in any casing/delimiter style — including variants the old
        exact-match in rerun display missed (``my_api_key``)."""
        for key in ("my_api_key", "X-API-Key", "apiKey", "accessToken", "clientSecret", "user.password"):
            assert is_sensitive_parameter(key), key

    def test_redacts_credential_bearing_http_header_names(self) -> None:
        """A session cookie is a credential (#716): ``Cookie`` / ``Set-Cookie`` and cookie-named params match,
        beside the other credential headers the existing words already cover."""
        for key in (
            "Cookie",
            "cookie",
            "COOKIE",
            "Set-Cookie",
            "set-cookie",
            "set_cookie",
            "session_cookie",
            "sessionCookie",
            "cookies",
            "Proxy-Authorization",
            "X-Auth-Token",
            "X-CSRF-Token",
        ):
            assert is_sensitive_parameter(key), key

    def test_does_not_false_positive_on_innocent_words(self) -> None:
        """The bug this fixes: a sensitive word embedded in a LARGER word must not match."""
        for key in (
            "author",
            "authority",
            "authentic",
            "secretary",
            "cookiecutter",
            "tokens",
            "tokenizer",
            "username",
            "name",
            "model",
            "command",
        ):
            assert not is_sensitive_parameter(key), key


class TestSanitizeParameters:
    def test_redacts_nested_and_list_sensitive_keys(self) -> None:
        out = sanitize_parameters({
            "headers": {"Authorization": "Bearer x", "X-Trace": "ok"},
            "accounts": [{"api_key": "AKIA", "name": "prod"}],
            "author": "Ada",
        })
        assert out["headers"]["Authorization"] == "<REDACTED>"
        assert out["headers"]["X-Trace"] == "ok"
        assert out["accounts"][0]["api_key"] == "<REDACTED>"
        assert out["accounts"][0]["name"] == "prod"
        assert out["author"] == "Ada"  # the false-positive fix — no longer redacted

    def test_always_redact_keys_override(self) -> None:
        out = sanitize_parameters({"channel": "C09"}, always_redact_keys={"channel"})
        assert out["channel"] == "<REDACTED>"

    def test_truncates_long_non_secret_strings(self) -> None:
        out = sanitize_parameters({"note": "x" * 200})
        assert out["note"].endswith("...<truncated>")


def test_redact_sensitive_redacts_at_any_depth_without_truncating_or_mutating() -> None:
    """The display redactor for trace content: key-name redaction only — unlike sanitize_parameters it
    keeps long values whole (a debugging view shows the full realized value) and returns a copy."""
    raw = {
        "headers": {"Authorization": "Bearer x", "X-Trace": "ok"},
        "accounts": [{"api_key": "AKIA", "name": "prod"}],
        "note": "x" * 200,
    }
    out = redact_sensitive(raw)
    assert out == {
        "headers": {"Authorization": "<REDACTED>", "X-Trace": "ok"},
        "accounts": [{"api_key": "<REDACTED>", "name": "prod"}],
        "note": "x" * 200,
    }
    assert raw["headers"]["Authorization"] == "Bearer x"  # the caller's (resume-faithful) data is untouched


def test_mask_sensitive_value_defers_to_the_shared_rule() -> None:
    assert mask_sensitive_value("api_key", "sk-123") == "<REDACTED>"
    assert mask_sensitive_value("author", "Ada") == "Ada"  # the false-positive fix


def test_report_masks_cookie_headers_of_an_http_step(tmp_path: Path) -> None:
    """``pflow report`` hides an http step's request ``Cookie`` and response ``Set-Cookie`` values while
    the ordinary headers beside them stay readable (#716). The event mirrors what a real HttpNode run
    records: resolved request headers in ``template_resolutions`` and ``response_headers`` in the output."""
    request_cookie = "sid=REQUEST-COOKIE-999"
    response_cookie = "sid=RESPONSE-COOKIE-777; HttpOnly"
    event = {
        "node_id": "fetch",
        "node_type": "HttpNode",
        "duration_ms": 4.0,
        "status": "success",
        "timestamp": "2026-10-11T11:19:14",
        "template_resolutions": {
            "headers": {
                "template": {"Cookie": "${cookie_value}", "Accept": "application/json"},
                "resolved": {"Cookie": request_cookie, "Accept": "application/json"},
            }
        },
        "node_output": {
            "response": {"ok": True},
            "status_code": 200,
            "response_headers": {"Set-Cookie": response_cookie, "X-Request-Id": "req-123"},
        },
    }
    trace_file = write_trace_jsonl(
        tmp_path / "trace.json",
        {
            "format_version": "2.0.0",
            "execution_id": "cookie-exec",
            "workflow_name": "cookie",
            "start_time": "2026-10-11T11:19:14",
            "final_status": "success",
            "nodes": [event],
        },
    )

    report_dir = generate_report(trace_file, str(tmp_path / "report"))

    assert report_dir is not None
    step = (report_dir / "01-fetch.md").read_text(encoding="utf-8")
    assert request_cookie not in step
    assert response_cookie not in step
    assert '"Cookie": "<REDACTED>"' in step
    assert '"Set-Cookie": "<REDACTED>"' in step
    assert '"Accept": "application/json"' in step
    assert '"X-Request-Id": "req-123"' in step

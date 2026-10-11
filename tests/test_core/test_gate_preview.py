"""#746 — an approval preview shows a shell step's ``env:`` values as the text the command receives.

The preview is built once (``build_approval_request``) and feeds every pause surface (ADR-0009), so
the bound-text rule is pinned here against the shell node's own binding function: if the two ever
disagree, the approver consents to text the step never receives.
"""

from __future__ import annotations

from pflow.core.gate import build_approval_request
from pflow.nodes.shell.env_binding import bind_env

_TYPED_ENV = {
    "FLAG": True,
    "OFF": False,
    "NOTHING": None,
    "COUNT": 3,
    "ZERO_FLOAT": 0.0,
    "OBJ": {"a": True, "b": [1, None]},
    "TEXT": "line1\nline2",
    "LONG": "x" * 290 + "END_MARKER",
}


def test_shell_env_preview_is_exactly_what_the_step_binds():
    request = build_approval_request("deploy", "ShellNode", {"command": "run", "env": dict(_TYPED_ENV)})

    assert request.preview["env"] == bind_env(_TYPED_ENV)
    assert request.preview["env"]["FLAG"] == "True"  # never the JSON literal true
    assert request.preview["env"]["NOTHING"] == ""  # null binds as empty text, never null
    assert request.preview["env"]["LONG"].endswith("END_MARKER")  # built in full
    assert request.preview["command"] == "run"  # other params are untouched


def test_env_is_bound_text_only_on_a_shell_step():
    # Another node type with an `env` param receives typed values — its preview keeps them.
    request = build_approval_request("child", "WorkflowExecutor", {"env": {"FLAG": True}})

    assert request.preview["env"] == {"FLAG": True}


def test_non_map_env_is_previewed_as_resolved():
    # A non-map env fails binding at prep; the preview shows what the author wrote.
    request = build_approval_request("deploy", "ShellNode", {"env": "FLAG=1"})

    assert request.preview["env"] == "FLAG=1"

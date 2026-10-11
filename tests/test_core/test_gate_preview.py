"""#746 — every gate render surface shows a shell step's ``env:`` values as the text the command receives.

``masked_preview`` is THE display policy (TTY prompt, pause output, JSON documents, the web panel all
reach it), so the bound-text rule is pinned here against the shell node's own binding function: if
the two ever disagree, the approver consents to text the step never receives.
"""

from __future__ import annotations

from pflow.core.gate import build_approval_request, masked_gate_dict, masked_preview
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


def _shown_env(env: dict, node_type: str = "ShellNode") -> object:
    request = build_approval_request("deploy", node_type, {"command": "run", "env": env})
    return masked_gate_dict(request.to_dict())["preview"]["env"]


def test_shell_env_is_shown_exactly_as_the_step_binds_it():
    shown = _shown_env(dict(_TYPED_ENV))

    assert shown == bind_env(_TYPED_ENV)
    assert shown["FLAG"] == "True"  # never the JSON literal true
    assert shown["NOTHING"] == ""  # null binds as empty text, never null
    assert shown["LONG"].endswith("END_MARKER")  # in full


def test_a_secret_nested_in_an_env_object_stays_redacted_in_its_text():
    # Masked before it becomes text: the object's JSON would otherwise carry the secret verbatim.
    shown = _shown_env({"CONFIG": {"api_key": "sk-example", "region": "eu"}, "ITEMS": [{"token": "tk-1"}]})

    assert shown == {
        "CONFIG": '{"api_key": "<REDACTED>", "region": "eu"}',
        "ITEMS": '[{"token": "<REDACTED>"}]',
    }


def test_the_payload_keeps_the_raw_resolved_values():
    # The trace's gate event records the resolved params, like template_resolutions; only display converts.
    request = build_approval_request("deploy", "ShellNode", {"env": {"FLAG": True, "API_KEY": "sk-1"}})

    assert request.preview["env"] == {"FLAG": True, "API_KEY": "sk-1"}


def test_env_is_bound_text_only_on_a_shell_step():
    # Another node type with an `env` param receives typed values — its preview keeps them.
    assert _shown_env({"FLAG": True}, node_type="WorkflowExecutor") == {"FLAG": True}


def test_non_map_env_is_shown_as_resolved():
    # A non-map env fails binding at prep; the preview shows what the author wrote.
    assert masked_preview({"env": "FLAG=1"}, "ShellNode") == {"env": "FLAG=1"}

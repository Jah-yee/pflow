"""The compiler hands a file-loaded code body its resolved path (issue #813).

``_resolved_files["code"]`` (recorded by the file resolver) becomes the code node's ``source_file``
attribute — never a param, so the absolute path stays out of the config hash, memo cache key and
trace params. An IR without the key (hand-built MCP IR, inline code) compiles and runs as before.
"""

from __future__ import annotations

from typing import Any

from pflow.core.ir_schema import validate_ir
from pflow.runtime import compile_workflow
from pflow.runtime.engine import WorkflowEngine
from tests.shared.registry_utils import ensure_test_registry

LOCATE = 'result: dict = {"file": globals().get("__file__"), "name": __name__}'


def _run(node: dict[str, Any]) -> tuple[Any, dict[str, Any]]:
    ir = {"ir_version": "0.1.0", "nodes": [node], "edges": []}
    validate_ir(ir)
    workflow = compile_workflow(ir, ensure_test_registry())
    shared: dict[str, Any] = dict(workflow.resolved_defaults)
    WorkflowEngine().run(workflow, shared)
    return workflow.start_node, shared["run"]["result"]


def test_resolved_code_path_reaches_the_body_but_not_the_params() -> None:
    path = "/workflows/lib/body.py"
    node, result = _run({
        "id": "run",
        "type": "code",
        "params": {"code": LOCATE},
        "_source_files": {"code": "./lib/body.py"},
        "_resolved_files": {"code": path},
    })

    assert result == {"file": path, "name": "__main__"}
    assert node.source_file == path
    assert path not in repr(node.params)


def test_ir_without_resolved_files_runs_as_before() -> None:
    node, result = _run({
        "id": "run",
        "type": "code",
        "params": {"code": LOCATE},
        "_source_files": {"code": "./lib/body.py"},
    })

    assert node.source_file is None
    assert result == {"file": None, "name": "__main__"}

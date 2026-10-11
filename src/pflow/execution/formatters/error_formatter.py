"""Error formatting for the CLI's JSON failure document (``cli/error_output.py``)."""

import logging
from typing import Any

from pflow.execution.execution_state import build_execution_steps
from pflow.execution.formatters.batch_errors import compact_batch_error_detail
from pflow.execution.result import ExecutionResult

logger = logging.getLogger(__name__)


def format_execution_errors(
    result: ExecutionResult,
    shared_storage: dict[str, Any] | None = None,
    ir_data: dict[str, Any] | None = None,
    metrics_collector: Any | None = None,
) -> dict[str, Any]:
    """Extract the failure document's errors, checkpoint, execution state, and metrics from a result.

    Args:
        result: ExecutionResult from execute_workflow()
        shared_storage: Optional shared store for execution state building
        ir_data: Optional workflow IR for execution state building
        metrics_collector: Optional metrics collector for timing and cost data

    Returns:
        Dictionary with:
        - errors: Error diagnostics in their printed form (``Diagnostic.to_output_dict``)
        - checkpoint: Execution checkpoint data
        - execution: Execution state with per-node status (if ir_data provided)
        - metrics: Metrics summary (if metrics_collector provided)

    Example::

        result = execute_workflow(...)
        formatted = format_execution_errors(result)
        formatted["errors"][0]["context"]["status_code"]   # e.g. 422
        formatted["execution"]["steps"]                    # per-node execution state
    """
    checkpoint = result.shared_after.get("__execution__", {})
    formatted_errors = [error.to_output_dict() for error in result.errors]

    result_dict: dict[str, Any] = {
        "errors": formatted_errors,
        "checkpoint": checkpoint,
    }

    metrics_summary = None
    if metrics_collector and shared_storage:
        trace = shared_storage.get("__trace_collector__")
        llm_calls = trace.collect_llm_calls() if trace else []
        metrics_summary = metrics_collector.get_summary(llm_calls)

    if ir_data and shared_storage:
        steps = build_execution_steps(ir_data, shared_storage, metrics_summary)
        if steps:
            steps = _compact_batch_error_details(steps)
            completed_count = sum(1 for s in steps if s["status"] == "completed")
            nodes_total = len(steps)

            result_dict["execution"] = {
                "duration_ms": metrics_summary.get("duration_ms") if metrics_summary else None,
                "nodes_executed": completed_count,
                "nodes_total": nodes_total,
                "steps": steps,
            }

    if metrics_summary:
        workflow_metrics = metrics_summary.get("metrics", {}).get("workflow", {})
        node_count = workflow_metrics.get("nodes_executed", 0)

        result_dict["metrics"] = {
            "duration_ms": metrics_summary.get("duration_ms"),
            "total_cost_usd": metrics_summary.get("total_cost_usd"),
            "nodes_executed": int(node_count),  # Ensure we return an int
            "metrics": metrics_summary.get("metrics", {}),
        }

    return result_dict


def _compact_batch_error_details(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    compact_steps: list[dict[str, Any]] = []
    for step in steps:
        step_copy = dict(step)
        details = step_copy.get("batch_error_details")
        if isinstance(details, list):
            step_copy["batch_error_details"] = [
                compact_batch_error_detail(detail) if isinstance(detail, dict) else detail for detail in details
            ]
        compact_steps.append(step_copy)
    return compact_steps

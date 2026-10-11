"""Unified workflow resolution for CLI and MCP entry points.

Merges CLI (cli/workflow_resolution.py) and MCP (mcp_server/utils/resolver.py)
resolvers into a single function that returns ResolvedWorkflow.

External file references (``- prompt: ./file.prompt.md``, ``- code: ./script.py``,
etc.) are resolved at this boundary for file-loaded and library-loaded workflows.
The returned ``ResolvedWorkflow.ir`` is the canonical fully-resolved IR — every
downstream consumer (analyzer, runner, mermaid, validator) operates on it
without needing to call ``resolve_file_references`` itself.

Two other IR-construction boundaries exist by design and have their own
resolution calls:

- ``runtime/compilation/compiler.py`` resolves child IR loaded by
  ``WorkflowExecutor`` for sub-workflow execution. The compiler's call is
  idempotent on already-resolved parent IR (``is_file_reference`` returns
  False for the inlined content).
- ``core/workflow/validator.py`` resolves child IR loaded fresh from disk
  during sub-workflow validation recursion.

If a future consumer needs to call ``resolve_file_references`` on a
``ResolvedWorkflow.ir``, that's a regression — file the issue against this
boundary instead of duplicating resolution downstream. See GH #321 / #334
for related boundary-vs-consumer architectural threads.
"""

import logging
import os
from pathlib import Path
from typing import Any

import yaml

from pflow.core.diagnostic import Diagnostic
from pflow.core.exceptions import CompilationError, WorkflowFileNotFoundError, WorkflowNotFoundError
from pflow.core.suggestion_utils import find_similar_items
from pflow.core.workflow.manager import WorkflowManager

from .result import ResolvedWorkflow

logger = logging.getLogger(__name__)


def _resolve_file_refs_at_boundary(ir: dict[str, Any], base_dir: Path) -> None:
    """Resolve external file references in IR at a load boundary.

    Wraps ``core.file_resolver.resolve_file_references`` to re-raise as
    ``CompilationError`` (consistent with the compiler's wrapping at
    ``runtime/compilation/compiler.py:570-581`` so existing exception-handling
    catches keep working).
    """
    from pflow.core.file_resolver import resolve_file_references

    try:
        resolve_file_references(ir, base_dir)
    except (FileNotFoundError, yaml.YAMLError) as e:
        raise CompilationError(
            message=str(e),
            phase="file_resolution",
            details={"error": str(e)},
            suggestion="Check that the file path is correct and relative to the workflow file.",
        ) from e


def resolve_workflow(
    identifier: str | dict[str, Any],
    wm: WorkflowManager | None = None,
) -> ResolvedWorkflow:
    """Resolve a workflow identifier to IR + metadata.

    Args:
        identifier: File path, saved name, raw markdown string, or IR dict.
        wm: WorkflowManager instance. Created internally if None.

    Returns:
        ResolvedWorkflow with ir, source, and file_path.

    Raises:
        WorkflowNotFoundError: Workflow not found (with similar_names for suggestions).
        WorkflowFileNotFoundError: A path-like identifier names no file.
        MarkdownParseError: Invalid markdown content.
        PermissionError: File access denied.
        ValueError: Inline workflow contains file references.
    """
    # Dict input — passthrough (MCP sends pre-parsed IR)
    if isinstance(identifier, dict):
        _check_inline_file_references(identifier, "direct")
        return ResolvedWorkflow(ir=identifier, source="direct", file_path=None)

    if not isinstance(identifier, str):
        raise WorkflowNotFoundError(
            workflow_name=str(identifier),
            similar_names=[],
            hint="Workflow must be a file path, saved name, markdown string, or IR dict.",
        )

    # Raw markdown content — contains newlines (MCP sends inline workflows)
    if "\n" in identifier:
        ir, diagnostics = _parse_markdown_content(identifier)
        _check_inline_file_references(ir, "content")
        return ResolvedWorkflow(ir=ir, source="content", file_path=None, diagnostics=diagnostics)

    # File path — contains path separator or ends with known extension.
    # A path is always a file: it never falls through to the saved-name lookup.
    if _is_path_like(identifier):
        return _load_from_file(identifier, wm)

    if wm is None:
        wm = WorkflowManager()

    if wm.exists(identifier):
        return _load_library_workflow(identifier, wm)

    # Not found — build suggestions and raise
    similar = _find_suggestions(identifier, wm)
    raise WorkflowNotFoundError(
        workflow_name=identifier,
        similar_names=similar,
    )


def _is_path_like(identifier: str) -> bool:
    """Check if identifier looks like a file path."""
    return (
        os.sep in identifier
        or (os.altsep is not None and os.altsep in identifier)
        or identifier.endswith(".pflow.md")
        or identifier.endswith(".json")
        or identifier.endswith(".md")
    )


def _file_exists(path: Path) -> bool:
    """``Path.exists`` without its OSError swallowing: on Python 3.14 an unreadable
    path reads as missing, so a permission error would be reported as "No file at"."""
    try:
        path.stat()
    except (FileNotFoundError, NotADirectoryError):
        return False
    return True


def _load_from_file(identifier: str, wm: WorkflowManager | None) -> ResolvedWorkflow:
    """Load a workflow from a file path; a missing file raises ``WorkflowFileNotFoundError``.

    One alias survives: a bare ``my-flow.pflow.md`` with no file behind it runs
    the saved workflow ``my-flow`` (saved names cannot contain ``.`` or a separator).
    """
    from pflow.core import normalize_ir
    from pflow.core.markdown_parser import parse_markdown

    path = Path(identifier).expanduser().resolve()

    # Reject .json files with migration hint
    if path.suffix == ".json":
        raise WorkflowNotFoundError(
            workflow_name=identifier,
            similar_names=[],
            hint="JSON workflow format is no longer supported. Convert to .pflow.md format.",
        )

    # Reject .md files that aren't .pflow.md with rename suggestion
    if path.suffix == ".md" and not str(path).endswith(".pflow.md"):
        pflow_path = path.with_suffix(".pflow.md")
        if pflow_path.exists():
            raise WorkflowNotFoundError(
                workflow_name=identifier,
                similar_names=[str(pflow_path)],
                hint=f"Did you mean '{pflow_path}'? Workflow files use the .pflow.md extension.",
            )
        raise WorkflowNotFoundError(
            workflow_name=identifier,
            similar_names=[],
            hint="Workflow files use the .pflow.md extension, not .md.",
        )

    if not _file_exists(path):
        saved_name = identifier.removesuffix(".pflow.md")
        if saved_name != identifier and Path(identifier).name == identifier:
            wm = wm or WorkflowManager()
            if wm.exists(saved_name):
                return _load_library_workflow(saved_name, wm)
        cwd = None if Path(identifier).expanduser().is_absolute() else Path.cwd()
        raise WorkflowFileNotFoundError(workflow_name=identifier, path=path, cwd=cwd)

    content = path.read_text(encoding="utf-8")
    result = parse_markdown(content)
    normalize_ir(result.ir)
    # Resolve external file references at the IR-load boundary so every
    # downstream consumer sees a fully-resolved IR. See module docstring.
    _resolve_file_refs_at_boundary(result.ir, path.parent)
    return ResolvedWorkflow(
        ir=result.ir,
        source="file",
        file_path=str(path),
        title=result.title,
        description=result.description,
        diagnostics=tuple(result.warnings),
    )


def _load_library_workflow(name: str, wm: WorkflowManager) -> ResolvedWorkflow:
    """Load a saved workflow, preserving parser diagnostics when possible.

    Parses the entry-point file directly so parser warnings survive.
    Falls back to ``load_ir()`` when the file isn't readable (e.g. mocked
    WorkflowManager in tests with fake paths).
    """
    from pflow.core import normalize_ir
    from pflow.core.markdown_parser import parse_markdown

    file_path = wm.get_path(name)
    diagnostics: tuple[Diagnostic, ...] = ()
    path = Path(file_path)
    title: str | None = None
    description: str | None = None
    if path.exists():
        content = path.read_text(encoding="utf-8")
        result = parse_markdown(content)
        ir = result.ir
        title = result.title
        description = result.description
        diagnostics = tuple(result.warnings)
    else:
        # Mocked WorkflowManager path (test isolation). No real file on disk
        # means no relative paths to resolve from — file resolution is skipped.
        # Tests that exercise file-resolution behavior must use a real path.
        ir = wm.load_ir(name)
    normalize_ir(ir)
    # Resolve external file references at the IR-load boundary, but only
    # when the file actually exists on disk. The mocked-load fallback above
    # has no on-disk anchor for relative paths.
    if path.exists():
        _resolve_file_refs_at_boundary(ir, path.parent)
    return ResolvedWorkflow(
        ir=ir,
        source="library",
        file_path=file_path,
        title=title,
        description=description,
        diagnostics=diagnostics,
    )


def _parse_markdown_content(content: str) -> tuple[dict[str, Any], tuple[Diagnostic, ...]]:
    """Parse raw markdown string into IR dict and parser diagnostics."""
    from pflow.core import normalize_ir
    from pflow.core.markdown_parser import parse_markdown

    result = parse_markdown(content)
    normalize_ir(result.ir)
    return result.ir, tuple(result.warnings)


def _check_inline_file_references(workflow_ir: dict[str, Any], source: str) -> None:
    """Raise ValueError if inline workflow contains file references."""
    if source not in ("content", "direct"):
        return
    from pflow.core.file_resolver import has_file_references

    file_refs = has_file_references(workflow_ir)
    if file_refs:
        examples = ", ".join(file_refs[:3])
        raise ValueError(
            f"Workflow contains file references ({examples}) but was provided as inline content. "
            f"File references require a workflow file path to resolve relative paths from. "
            f"Save the workflow to a file and reference it by path or saved name."
        )


def _find_suggestions(query: str, wm: WorkflowManager) -> list[str]:
    """Find similar workflow names for error suggestions."""
    all_names = wm.list_names()
    if not all_names:
        return []
    return find_similar_items(query, all_names, max_results=5, method="substring", sort_by_length=True)

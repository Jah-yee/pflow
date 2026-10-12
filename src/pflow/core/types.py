"""Canonical workflow input/output type vocabulary for authored workflows.

This module defines the Surface 1 (S1) type system for workflow-authored
``## Inputs`` / ``## Outputs`` declarations. It intentionally differs from the
Python annotation vocabulary used inside code blocks and node Interface
docstrings.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Final, NoReturn

from pflow.core.suggestion_utils import find_similar_items

CANONICAL_TYPES: Final[tuple[str, ...]] = (
    "string",
    "number",
    "integer",
    "boolean",
    "array",
    "object",
    "any",
)

PYTHON_ALIASES_AT_S1: Final[dict[str, str]] = {
    "str": "string",
    "int": "integer",
    "float": "number",
    "bool": "boolean",
    "dict": "object",
    "list": "array",
}


# Decision (b)'s accepted text — strict ASCII, matched whole (callers strip surrounding whitespace first).
_INTEGER_TEXT: Final = re.compile(r"-?[0-9]+")
_NUMBER_TEXT: Final = re.compile(r"-?(0|[1-9][0-9]*)(\.[0-9]+)?([eE][-+]?[0-9]+)?")  # a JSON number
_BOOLEAN_TEXT: Final[dict[str, bool]] = {"true": True, "false": False, "yes": True, "no": False, "1": True, "0": False}
_NO_FIT: Final[tuple[bool, Any]] = (False, None)

# Per type, for messages: (what it accepts, the aside shown with it, a canonical example as typed on a command
# line, the placeholder an example command shows after ``name=``).
_ACCEPTED: Final[dict[str, tuple[str, str, str, str]]] = {
    "string": ("text", "", "text", "<string>"),
    "integer": ("a whole number", "e.g. 3", "3", "<integer>"),
    "number": ("a number", "e.g. 3, 2.5, 1e3", "3", "<number>"),
    "boolean": ("true or false", "also yes/no, 1/0", "true", "<true/false>"),
    "object": ("a JSON object", 'e.g. {"a": 1}', '{"a": 1}', "'{...}'"),
    "array": ("a JSON array", 'e.g. ["a", "b"]', '["a", "b"]', "'[...]'"),
    "any": ("any value", "", "", "<value>"),
}


def _reject_constant(name: str) -> NoReturn:
    raise ValueError(f"{name} is not JSON")


def _read_number(read: Callable[[str], Any], text: str) -> tuple[bool, Any]:
    """``read(text)`` for grammar-matched digits: an int, or a finite float (``1e999`` overflows to inf)."""
    try:
        value = read(text)
    except ValueError:  # beyond Python's int digit limit
        return _NO_FIT
    return (True, value) if isinstance(value, int) or math.isfinite(value) else _NO_FIT


def outer_base_type(type_str: str) -> str:
    """Strip a parameterized generic to its outer base name (``list[str]`` -> ``list``).

    The element type is discarded: ``dict[str, int]`` -> ``dict``,
    ``list[dict]`` -> ``list``. Bare names pass through unchanged. Used wherever a
    type string must be compared against the bare type vocabulary.
    """
    return type_str.split("[", 1)[0].strip()


@dataclass
class TypeVocabularyError(ValueError):
    """Raised when an authored workflow uses an invalid S1 type name."""

    message: str
    offending: str
    similar_names: list[str] = field(default_factory=list)
    available_fields: list[str] = field(default_factory=lambda: list(CANONICAL_TYPES))
    available_fields_label: str = "types"
    suggestions_list: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        super().__init__(self.message)

    def __str__(self) -> str:
        return self.message


@dataclass(frozen=True)
class TypeSpec:
    """Canonical representation of a workflow-authored S1 type.

    ``accepts()`` follows strict JSON-Schema-style semantics for future callers:
    ``integer`` rejects ``True`` even though Python treats ``bool`` as an
    ``int`` subclass. This intentionally differs from the Python-side code-node
    annotation semantics.
    """

    name: str

    def __post_init__(self) -> None:
        if self.name not in CANONICAL_TYPES:
            raise ValueError(f"TypeSpec.name must be in {CANONICAL_TYPES}, got {self.name!r}")

    @classmethod
    def parse(cls, raw: str) -> TypeSpec:
        """Parse an authored workflow type string into a canonical TypeSpec."""
        if not isinstance(raw, str):
            raise TypeVocabularyError("Type must be a non-empty string", offending=repr(raw))

        stripped = raw.strip()
        if not stripped:
            raise TypeVocabularyError("Type must be a non-empty string", offending=raw)

        if "[" in stripped:
            _raise_parameterized_generic_error(raw, stripped)

        if any(char.isspace() for char in stripped):
            raise TypeVocabularyError(
                "Whitespace not allowed inside type names.",
                offending=raw,
            )

        if stripped in CANONICAL_TYPES:
            return cls(stripped)

        if stripped in PYTHON_ALIASES_AT_S1:
            _raise_alias_error(raw, stripped)

        if stripped == "null":
            raise TypeVocabularyError(
                "Use 'any' if the value may be None — it accepts null alongside other values. "
                "(Nullable-only types require union syntax, which pflow does not yet support.)",
                offending=raw,
                suggestions_list=["Use 'any' if the value may be None"],
            )

        _raise_unknown_type_error(raw, stripped)

    def accepts(self, value: Any) -> bool:
        """Return whether a Python value satisfies this type."""
        if self.name == "any":
            return True
        if self.name == "string":
            return isinstance(value, str)
        if self.name == "integer":
            return isinstance(value, int) and not isinstance(value, bool)
        if self.name == "number":
            return isinstance(value, (int, float)) and not isinstance(value, bool)
        if self.name == "boolean":
            return isinstance(value, bool)
        if self.name == "array":
            return isinstance(value, list)
        if self.name == "object":
            return isinstance(value, dict)
        return False

    def parse_text(self, text: str) -> tuple[bool, Any]:
        """Read ``text`` as this type under decision (b)'s strict ASCII grammar.

        integer ``-?[0-9]+`` (``007`` → 7); number = a JSON number, an ``int`` without
        fraction or exponent, else a finite ``float`` (``007``, ``nan``, ``inf``, ``1_000``
        do not fit); boolean = true/false/yes/no/1/0, case-insensitive; object/array =
        JSON text of that shape; string and any = the text itself. ``(False, None)``
        when the text does not fit. Callers strip surrounding whitespace first for
        every type but string.
        """
        match self.name:
            case "string" | "any":
                return True, text
            case "integer":
                return _read_number(int, text) if _INTEGER_TEXT.fullmatch(text) else _NO_FIT
            case "number":
                return _read_number(json.loads, text) if _NUMBER_TEXT.fullmatch(text) else _NO_FIT
            case "boolean":
                key = text.lower()
                return (True, _BOOLEAN_TEXT[key]) if key in _BOOLEAN_TEXT else _NO_FIT
            case _:  # object, array
                try:
                    parsed = json.loads(text, parse_constant=_reject_constant)
                except ValueError:  # JSONDecodeError, NaN/Infinity, int digit limit
                    return _NO_FIT
                return (True, parsed) if self.accepts(parsed) else _NO_FIT

    @property
    def accepted_noun(self) -> str:
        """What this type accepts, for messages: ``"a whole number"``."""
        return _ACCEPTED[self.name][0]

    @property
    def accepted_text(self) -> str:
        """The noun with its aside: ``"a whole number (e.g. 3)"``, ``"true or false (also yes/no, 1/0)"``."""
        noun, aside, _, _ = _ACCEPTED[self.name]
        return f"{noun} ({aside})" if aside else noun

    @property
    def example_text(self) -> str:
        """A canonical accepted value as typed on a command line: ``"3"``, ``'["a", "b"]'``."""
        return _ACCEPTED[self.name][2]

    @property
    def placeholder(self) -> str:
        """What an example command shows after ``name=``: ``"<integer>"``, ``"'[...]'"`` (shell-quoted JSON)."""
        return _ACCEPTED[self.name][3]

    def is_wildcard(self) -> bool:
        """Return True only for the explicit wildcard type."""
        return self.name == "any"

    def to_json_schema(self) -> dict[str, str]:
        """Return a minimal JSON Schema representation for this type."""
        if self.name == "any":
            return {}
        return {"type": self.name}

    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True)
class InputUsage:
    """How a caller supplies one declared workflow input — what every surface that describes or
    exemplifies an input reads (``describe``, ``save``, skills, discovery, LLM context, the graph)."""

    type: TypeSpec
    required: bool  # a run that omits it fails
    default: str | None  # the default as a caller would type it; None when there is none
    stdin: bool

    def argument(self, name: str) -> str:
        """``name=<placeholder>``, as an example command shows it."""
        return f"{name}={self.type.placeholder}"


def input_usage(spec: Mapping[str, Any]) -> InputUsage:
    """Read one ``## Inputs`` declaration the way a run treats it (``ir_preparation.prepare_inputs``).

    Required unless ``required`` is false or a default fills it — a ``default: null`` is no
    default, and a ``default: ""`` still fails a required input as empty, so neither makes it
    optional. Untyped (or a type outside the vocabulary) is ``any``.
    """
    declared = spec.get("type")
    default = spec.get("default")
    return InputUsage(
        type=TypeSpec(declared if isinstance(declared, str) and declared in CANONICAL_TYPES else "any"),
        required=bool(spec.get("required", True)) and default in (None, ""),
        default=None if default is None else _typed_text(default),
        stdin=spec.get("stdin") is True,
    )


def usage_arguments(inputs: Mapping[str, Mapping[str, Any]], *, include_optional: bool = False) -> list[str]:
    """The ``name=<placeholder>`` arguments of an example command: the required inputs in
    declaration order, then — with ``include_optional`` — the optional ones."""
    usages = {name: input_usage(spec) for name, spec in inputs.items()}
    required = [usage.argument(name) for name, usage in usages.items() if usage.required]
    optional = [usage.argument(name) for name, usage in usages.items() if not usage.required]
    return required + optional if include_optional else required


def _typed_text(value: Any) -> str:
    """A value as a caller types it: text as is (empty text as ``""``), anything else as JSON."""
    if isinstance(value, str):
        return value or '""'
    return json.dumps(value, ensure_ascii=False)


def _raise_parameterized_generic_error(raw: str, stripped: str) -> NoReturn:
    """Raise the canonical error for unsupported parameterized generics."""
    base = outer_base_type(stripped)
    if base in PYTHON_ALIASES_AT_S1:
        canonical = PYTHON_ALIASES_AT_S1[base]
        suggestion = (
            f"Use '{canonical}' — parameterized generics not supported at `## Inputs` / `## Outputs` (got {raw!r})"
        )
    elif base in CANONICAL_TYPES:
        suggestion = f"Use '{base}' — parameterized generics not supported at `## Inputs` / `## Outputs` (got {raw!r})"
    else:
        suggestion = (
            f"Use the base type — parameterized generics not supported at `## Inputs` / `## Outputs` (got {raw!r})"
        )

    raise TypeVocabularyError(
        f"Parameterized generics not supported in `## Inputs` / `## Outputs`. Got: {raw!r}. {suggestion}.",
        offending=raw,
        suggestions_list=[suggestion],
    )


def _raise_alias_error(raw: str, stripped: str) -> NoReturn:
    """Raise the canonical error for deprecated Python aliases at S1.

    Alias errors carry the canonical replacement via ``suggestions_list`` — the
    "known fix" channel. ``similar_names`` is reserved for genuinely uncertain
    typo cases (fuzzy match on unknown names) where "Did you mean" framing fits.
    """
    canonical = PYTHON_ALIASES_AT_S1[stripped]
    if stripped == "dict":
        raise TypeVocabularyError(
            "Use 'object' instead of 'dict'. Use 'any' if the value can be any type.",
            offending=raw,
            suggestions_list=[
                "Use 'object' if the value is a dict: - type: object",
                "Use 'any' if the value can be any type: - type: any",
            ],
        )

    suggestion = f"Use '{canonical}' instead of '{stripped}'"
    raise TypeVocabularyError(
        suggestion,
        offending=raw,
        suggestions_list=[suggestion],
    )


def _raise_unknown_type_error(raw: str, stripped: str) -> NoReturn:
    """Raise the canonical error for unknown S1 types."""
    similar_names = find_similar_items(
        stripped,
        list(CANONICAL_TYPES),
        method="fuzzy",
        cutoff=0.6,
        max_results=1,
    )
    if similar_names:
        closest = similar_names[0]
        raise TypeVocabularyError(
            f"Unknown type '{stripped}'. Did you mean '{closest}'? Valid types: {', '.join(CANONICAL_TYPES)}",
            offending=raw,
            similar_names=similar_names,
        )

    raise TypeVocabularyError(
        f"Unknown type '{stripped}'. Valid types: {', '.join(CANONICAL_TYPES)}",
        offending=raw,
    )


def is_template_reserved_internal_key(root: str) -> bool:
    """Whether a template root identifier is a reserved pflow internal key
    that cannot be referenced from ``.pflow.md`` templates.

    Catches ``__execution__``, ``__failures__``, ``__cache_hits__``,
    ``__warnings__``, ``__memoization_cache__``, etc. Excludes the two
    template-accessible reserved keys: ``__index__`` (current batch item index)
    and ``__iteration__`` (1-based loop iteration count, issue #445).
    """
    return root.startswith("__") and root.endswith("__") and root not in ("__index__", "__iteration__")

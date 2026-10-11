# MCP Server Utilities

`validation.py:validate_execution_parameters` checks parameter names, JSON
serializability, and serialized size at the MCP boundary — structure only, never
value content (why: its module docstring); an injection risk is fixed at its sink,
not by pattern-matching values. Callers live
in `../services/execution_service.py`; new execution entry points must consider this
boundary explicitly rather than assume validation is automatic.

Shared implementations live in core:

- `core/validation_utils.py` owns parameter-name rules and `generate_dummy_parameters`.
- `core/security_utils.py:sanitize_parameters` owns redaction; `errors.py` is a
  compatibility re-export of it.

Change shared behavior at its core owner.

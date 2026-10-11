"""Compilation package — transforms workflow IR into CompiledWorkflow objects."""

from .compiler import CompilationError, compile_workflow, inject_special_parameters, is_side_effecting
from .ir_preparation import check_supplied_inputs, prepare_inputs, validate_ir_structure
from .node_loader import import_node_class

__all__ = [
    "CompilationError",
    "check_supplied_inputs",
    "compile_workflow",
    "import_node_class",
    "inject_special_parameters",
    "is_side_effecting",
    "prepare_inputs",
    "validate_ir_structure",
]

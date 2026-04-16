"""Completion prompts and guidelines for different file types."""

from .completion_prompts import (
    LAYER_RULES,
    DELEGATED_TODOS,
    get_file_context,
    get_todo_guidelines,
    is_delegated_todo,
)

__all__ = [
    "LAYER_RULES",
    "DELEGATED_TODOS",
    "get_file_context",
    "get_todo_guidelines",
    "is_delegated_todo",
]

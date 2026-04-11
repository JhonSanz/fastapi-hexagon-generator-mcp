"""Completion prompts for different file types."""

from .completion_prompts import (
    get_domain_dto_prompt,
    get_domain_model_prompt,
    get_schema_prompt,
    get_repository_prompt,
    get_use_case_prompt,
)

__all__ = [
    "get_domain_dto_prompt",
    "get_domain_model_prompt",
    "get_schema_prompt",
    "get_repository_prompt",
    "get_use_case_prompt",
]

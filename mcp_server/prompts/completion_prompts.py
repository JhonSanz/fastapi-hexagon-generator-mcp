"""Specialized prompts for completing TODOs in different file types."""

from typing import Any


# Base architecture guidelines (shared across all prompts)
BASE_GUIDELINES = {
    "domain_dto": "Pure dataclasses, no external deps, Python built-in types only",
    "domain_model": "SQLAlchemy 2.0 with Mapped[] types, id/created_at/updated_at required",
    "schema": "Pydantic v2, Field() for validation, separate Request/Response schemas",
    "repository": "SQLAlchemy 2.0 select(), handle DTOs not schemas",
    "use_case": "Business logic, use UnitOfWork, mappers between layers",
}


def _get_file_context(file_content: str, todos: list[dict[str, Any]]) -> str:
    """Extract only relevant context around TODOs instead of full file.

    Args:
        file_content: Full file content
        todos: List of TODO items

    Returns:
        Minimal context string
    """
    lines = file_content.split("\n")
    context_lines = []

    for todo in todos:
        line_num = todo["line_number"] - 1  # 0-indexed
        start = max(0, line_num - 3)  # 3 lines before
        end = min(len(lines), line_num + 3)  # 3 lines after

        context_lines.append(f"--- Line {todo['line_number']} ---")
        context_lines.extend(lines[start:end])

    return "\n".join(context_lines)


def get_domain_dto_prompt(
    file_path: str, file_content: str, context: str, todos: list[dict[str, Any]]
) -> str:
    """Generate prompt for completing Domain DTOs."""
    entity_name = file_path.split("/")[-2]  # Extract module name

    return f"""Complete {len(todos)} TODO(s) in Domain DTO: {entity_name}
Context: {context or 'N/A'}
Rules: {BASE_GUIDELINES['domain_dto']}

TODOs:
{_format_todos(todos)}

Code context:
```python
{_get_file_context(file_content, todos)}
```

Delete any existing TODO comments after completion.
Return ONLY the completed field definitions (not full file)."""


def get_domain_model_prompt(
    file_path: str, file_content: str, context: str, todos: list[dict[str, Any]]
) -> str:
    """Generate prompt for completing Domain Models (SQLAlchemy)."""
    entity_name = file_path.split("/")[-2]

    return f"""Complete {len(todos)} TODO(s) in Domain Model: {entity_name}
Context: {context or 'N/A'}
Rules: {BASE_GUIDELINES['domain_model']}

TODOs:
{_format_todos(todos)}

Code context:
```python
{_get_file_context(file_content, todos)}
```

Delete any existing TODO comments after completion.
Return ONLY the completed column definitions using Mapped[] syntax."""


def get_schema_prompt(
    file_path: str, file_content: str, context: str, todos: list[dict[str, Any]]
) -> str:
    """Generate prompt for completing Pydantic Schemas."""
    entity_name = file_path.split("/")[-2]

    return f"""Complete {len(todos)} TODO(s) in Pydantic Schema: {entity_name}
Context: {context or 'N/A'}
Rules: {BASE_GUIDELINES['schema']}

TODOs:
{_format_todos(todos)}

Code context:
```python
{_get_file_context(file_content, todos)}
```

Delete any existing TODO comments after completion.
Return ONLY the completed field definitions with Field() validations."""


def get_repository_prompt(
    file_path: str, file_content: str, context: str, todos: list[dict[str, Any]]
) -> str:
    """Generate prompt for completing Repository implementations."""
    entity_name = file_path.split("/")[-2]

    return f"""Complete {len(todos)} TODO(s) in Repository: {entity_name}
Context: {context or 'N/A'}
Rules: {BASE_GUIDELINES['repository']}

TODOs:
{_format_todos(todos)}

Code context:
```python
{_get_file_context(file_content, todos)}
```

Delete any existing TODO comments after completion.
Return ONLY the completed implementation code (filters, queries, etc.)."""


def get_use_case_prompt(
    file_path: str, file_content: str, context: str, todos: list[dict[str, Any]]
) -> str:
    """Generate prompt for completing Use Case implementations."""
    entity_name = file_path.split("/")[-2]

    return f"""Complete {len(todos)} TODO(s) in Use Case: {entity_name}
Context: {context or 'N/A'}
Rules: {BASE_GUIDELINES['use_case']}

TODOs:
{_format_todos(todos)}

Code context:
```python
{_get_file_context(file_content, todos)}
```

Delete any existing TODO comments after completion.
Return ONLY the completed business logic (validations, error handling, etc.)."""


def _format_todos(todos: list[dict[str, Any]]) -> str:
    """Format TODO list for display in prompt.

    Args:
        todos: List of TODO items

    Returns:
        Formatted string
    """
    if not todos:
        return "No TODOs found"

    formatted = []
    for i, todo in enumerate(todos, 1):
        formatted.append(f"{i}. Line {todo['line_number']}: {todo['content']}")

    return "\n".join(formatted)

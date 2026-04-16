"""Structured guidelines for completing TODOs in different file types."""

from typing import Any


LAYER_RULES = {
    "domain": {
        "allowed_imports": ["dataclasses", "datetime", "typing", "abc"],
        "forbidden_imports": ["sqlalchemy", "pydantic", "fastapi"],
        "principle": "Pure domain logic. No external dependencies.",
    },
    "application": {
        "allowed_imports": ["domain.*", "pydantic"],
        "forbidden_imports": ["sqlalchemy", "fastapi", "infrastructure.*"],
        "principle": "Business logic and orchestration. Use UnitOfWork for transactions.",
    },
    "infrastructure": {
        "allowed_imports": ["domain.*", "application.*", "sqlalchemy", "fastapi"],
        "forbidden_imports": [],
        "principle": "Technical implementation details. Adapters to external systems.",
    },
}


TODO_GUIDELINES = {
    # Use case business logic TODOs
    "create": {
        "category": "business_logic",
        "guideline": "Add pre-creation validation and data transformations.",
        "suggestion": "Validate uniqueness, normalize data, check business rules before persisting.",
    },
    "update": {
        "category": "business_logic",
        "guideline": "Add pre-update validation and authorization.",
        "suggestion": "Validate field constraints, check ownership/permissions, apply business rules.",
    },
    "list": {
        "category": "business_logic",
        "guideline": "Add filtering logic and authorization.",
        "suggestion": "Apply role-based filtering, scope queries, validate filter params.",
    },
    "retrieve": {
        "category": "business_logic",
        "guideline": "Add authorization and data enrichment.",
        "suggestion": "Check access permissions, enrich with related data if needed.",
    },
    "delete": {
        "category": "business_logic",
        "guideline": "Add authorization and cascading logic.",
        "suggestion": "Check permissions, handle dependent records, soft-delete if applicable.",
    },
}

# TODOs that are handled by define_fields or wire_module, not complete_todos
DELEGATED_TODOS = {
    "Add your domain fields here": "define_fields",
    "Add your fields here": "define_fields",
    "Add your fields here (all Optional)": "define_fields",
    "Add your model columns here": "define_fields",
    "Add your model fields here": "define_fields",
    "Add example data": "define_fields",
    "Add fields that can be updated": "define_fields",
    "Add your fields": "define_fields",
    "Add main fields for list view": "define_fields",
    "Add specific filters for your model": "define_fields",
    "Map your fields here": "define_fields",
    "Customize search fields based on your model": "define_fields",
    "Apply custom filters": "define_fields",
    "Register your module routers here": "wire_module",
    "Import your module exception mappings here": "wire_module",
    "Append your module exception mappings here": "wire_module",
}


def get_file_context(file_content: str, todos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Extract structured context around each TODO.

    Returns a list of context dicts with before/after lines for each TODO.
    """
    lines = file_content.split("\n")
    contexts = []

    for todo in todos:
        line_num = todo["line_number"] - 1  # 0-indexed
        start = max(0, line_num - 3)
        end = min(len(lines), line_num + 4)

        contexts.append({
            "line_number": todo["line_number"],
            "todo_text": todo["content"],
            "before": lines[start:line_num],
            "after": lines[line_num + 1 : end],
        })

    return contexts


def get_todo_guidelines(file_type: str) -> dict[str, Any]:
    """Get structured guidelines for a file type.

    Args:
        file_type: File stem (e.g., 'create', 'update', 'entities')

    Returns:
        Dict with category, guideline, and suggestion. Empty dict if not applicable.
    """
    return TODO_GUIDELINES.get(file_type, {})


def is_delegated_todo(todo_content: str) -> str | None:
    """Check if a TODO should be handled by another tool.

    Returns the tool name if delegated, None otherwise.
    """
    for marker, tool in DELEGATED_TODOS.items():
        if marker in todo_content:
            return tool
    return None

"""Field propagation for the ORM models layer."""

import re

from .field import FieldDefinition, SQLALCHEMY_TYPE_MAP
from .todo_blocks import apply_todo


def apply(content: str, fields: list[FieldDefinition]) -> tuple[str, int]:
    """Apply field definitions to an infrastructure/models.py file."""
    columns = [_model_column(f) for f in fields]
    content, n = apply_todo(content, "Add your model columns here", columns)
    if n:
        content = _merge_sqlalchemy_imports(content, fields)
    return content, n


def _model_column(f: FieldDefinition) -> str:
    if not f.is_known_type:
        return f"# TODO: Define column for '{f.name}' (type: {f.type})"

    sa_type_expr, _ = SQLALCHEMY_TYPE_MAP[f.type]
    if f.type == "str":
        sa_type_expr = f"String({f.max_length})" if f.max_length else "Text"

    mapped_type = f"{f.type} | None" if f.nullable else f.type
    parts = [sa_type_expr, f"nullable={'True' if f.nullable else 'False'}"]
    if f.searchable and f.type == "str":
        parts.append("index=True")

    return f"{f.name}: Mapped[{mapped_type}] = mapped_column({', '.join(parts)})"


def _merge_sqlalchemy_imports(content: str, fields: list[FieldDefinition]) -> str:
    needed = _imports_needed(fields)
    match = re.search(r"^from sqlalchemy import (.+)$", content, re.MULTILINE)
    if not match:
        return content
    existing = {t.strip() for t in match.group(1).split(",")}
    merged = sorted(existing | needed)
    return (
        content[: match.start()]
        + f"from sqlalchemy import {', '.join(merged)}"
        + content[match.end() :]
    )


def _imports_needed(fields: list[FieldDefinition]) -> set[str]:
    """SQLAlchemy types that must be imported for these fields."""
    needed: set[str] = set()
    for f in fields:
        if not f.is_known_type:
            continue
        _, import_name = SQLALCHEMY_TYPE_MAP[f.type]
        needed.add(import_name)
        if f.type == "str" and not f.max_length:
            needed.add("Text")
    return needed

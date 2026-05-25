"""Field propagation for the domain entities layer."""

from .field import FieldDefinition
from .todo_blocks import apply_todo, get_indent


def apply(content: str, fields: list[FieldDefinition]) -> tuple[str, int]:
    """Apply field definitions to a domain/entities.py file. Returns (new_content, todos_completed)."""
    count = 0
    required = [f for f in fields if not f.nullable]
    nullable = [f for f in fields if f.nullable]

    # Main entity: required fields fill the TODO between `id` and `created_at`.
    # Nullable fields carry defaults, so they must go AFTER `updated_at: datetime`
    # to satisfy dataclass ordering (non-default fields cannot follow defaulted ones).
    content, n = apply_todo(
        content,
        "Add your domain fields here",
        [_entity_field(f) for f in required],
    )
    count += n
    if n and nullable:
        content = _insert_after_updated_at(
            content, [_entity_field(f) for f in nullable]
        )

    # CreateData: required first, nullable last → safe ordering.
    ordered = sorted(fields, key=lambda f: f.nullable)
    content, n = apply_todo(
        content,
        "Add your fields here",
        [_entity_field(f) for f in ordered],
    )
    count += n

    # UpdateData: every field optional.
    content, n = apply_todo(
        content,
        "Add your fields here (all Optional)",
        [_entity_field(f, optional_all=True) for f in fields],
    )
    count += n

    return content, count


def _entity_field(f: FieldDefinition, optional_all: bool = False) -> str:
    if not f.is_known_type:
        return f"{f.name}: ...  # TODO: Define type for '{f.type}' field"
    if f.nullable or optional_all:
        return f"{f.name}: Optional[{f.type}] = None"
    return f"{f.name}: {f.type}"


def _insert_after_updated_at(content: str, inserted: list[str]) -> str:
    lines = content.split("\n")
    for i, line in enumerate(lines):
        if line.strip() == "updated_at: datetime":
            indent = get_indent(line)
            indented = [f"{indent}{ln}" for ln in inserted]
            return "\n".join(lines[: i + 1] + indented + lines[i + 1 :])
    return content

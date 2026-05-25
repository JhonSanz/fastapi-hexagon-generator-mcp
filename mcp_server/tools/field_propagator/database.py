"""Field propagation for the database/repository layer."""

from .field import FieldDefinition
from .todo_blocks import apply_todo, get_indent


def apply(
    content: str, fields: list[FieldDefinition], pascal_name: str
) -> tuple[str, int]:
    """Apply field definitions to an infrastructure/database.py file."""
    count = 0

    content, n = apply_todo(
        content,
        "Map your fields here",
        [_mapper_line(f) for f in fields],
    )
    count += n

    # The search TODO sits above the or_() block, with a commented example
    # inside it. Remove the TODO and rewrite the example separately.
    content, n = apply_todo(content, "Customize search fields based on your model", [])
    count += n
    content = _rewrite_search_example(content, fields, pascal_name)

    filterable = [f for f in fields if f.searchable]
    if filterable:
        filter_lines: list[str] = []
        for f in filterable:
            filter_lines.extend(_filter_block(pascal_name, f))
    else:
        filter_lines = ["# No custom filters defined"]
    content, n = apply_todo(content, "Apply custom filters", filter_lines)
    count += n

    return content, count


def _mapper_line(f: FieldDefinition) -> str:
    return f"{f.name}=orm_obj.{f.name},"


def _search_line(pascal_name: str, f: FieldDefinition) -> str:
    return f"{pascal_name}ORM.{f.name}.ilike(search_pattern),"


def _filter_block(pascal_name: str, f: FieldDefinition) -> list[str]:
    return [
        f'if {f.name}_val := filters.get("{f.name}"):',
        f"    stmt = stmt.where({pascal_name}ORM.{f.name} == {f.name}_val)",
    ]


def _rewrite_search_example(
    content: str, fields: list[FieldDefinition], pascal_name: str
) -> str:
    searchable = [f for f in fields if f.searchable and f.type == "str"]
    out: list[str] = []
    for line in content.split("\n"):
        stripped = line.strip()
        if stripped.startswith("#") and "ORM." in stripped and "ilike(search_pattern)" in stripped:
            if searchable:
                indent = get_indent(line)
                out.extend(
                    f"{indent}{_search_line(pascal_name, f)}" for f in searchable
                )
            continue
        out.append(line)
    return "\n".join(out)

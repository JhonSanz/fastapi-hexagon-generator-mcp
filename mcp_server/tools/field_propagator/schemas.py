"""Field propagation for the Pydantic schemas layer."""

from .field import FieldDefinition
from .todo_blocks import apply_todo


EXAMPLE_VALUES = {
    "str": '"Example {name}"',
    "int": "1",
    "float": "1.0",
    "bool": "True",
    "datetime": '"2024-01-15T10:30:00"',
    "date": '"2024-01-15"',
    "Decimal": '"10.50"',
}


def apply(content: str, fields: list[FieldDefinition]) -> tuple[str, int]:
    """Apply field definitions to an application/schemas.py file.

    NOTE: the markers "Add example data" and "Add your fields" each appear
    TWICE in the template. apply_todo matches the first unconsumed occurrence,
    so the order of calls below is load-bearing — do not reorder.
    """
    count = 0

    content, n = apply_todo(
        content,
        "Add your model fields here",
        [_schema_field(f) for f in fields],
    )
    count += n

    content, n = apply_todo(
        content,
        "Add example data",
        [_example_value(f) for f in fields if not f.nullable],
    )
    count += n

    content, n = apply_todo(
        content,
        "Add fields that can be updated",
        [_schema_field(f, optional=True) for f in fields],
    )
    count += n

    content, n = apply_todo(
        content,
        "Add example data",
        [_example_value(f) for f in fields[:1]],
    )
    count += n

    content, n = apply_todo(
        content,
        "Add your fields",
        [_example_value(f) for f in fields],
    )
    count += n

    content, n = apply_todo(
        content,
        "Add main fields for list view",
        [f"{f.name}: {f.type}" for f in fields if not f.nullable],
    )
    count += n

    content, n = apply_todo(
        content,
        "Add your fields",
        [_example_value(f) for f in fields if not f.nullable],
    )
    count += n

    searchable = [f for f in fields if f.searchable]
    content, n = apply_todo(
        content,
        "Add specific filters for your model",
        [_filter_field(f) for f in searchable],
    )
    count += n

    return content, count


def _schema_field(f: FieldDefinition, optional: bool = False) -> str:
    if not f.is_known_type:
        return f"# TODO: Define schema field for '{f.name}' (type: {f.type})"

    is_optional = optional or f.nullable
    py_type = f"Optional[{f.type}]" if is_optional else f.type
    kwargs: list[str] = ["None"] if is_optional else ["..."]

    if f.type == "str":
        if f.min_length is not None:
            kwargs.append(f"min_length={f.min_length}")
        elif not is_optional:
            kwargs.append("min_length=1")
        if f.max_length is not None:
            kwargs.append(f"max_length={f.max_length}")

    for constraint in ("gt", "ge", "lt", "le"):
        val = getattr(f, constraint)
        if val is not None:
            kwargs.append(f"{constraint}={val}")

    if f.description:
        kwargs.append(f'description="{f.description}"')

    return f'{f.name}: {py_type} = Field({", ".join(kwargs)})'


def _example_value(f: FieldDefinition) -> str:
    if not f.is_known_type:
        return f"# TODO: Add example for '{f.name}' (type: {f.type})"
    template = EXAMPLE_VALUES.get(f.type, "None")
    return f'"{f.name}": {template.format(name=f.name)},'


def _filter_field(f: FieldDefinition) -> str:
    return f'{f.name}: Optional[{f.type}] = Field(None, description="Filter by {f.name}")'

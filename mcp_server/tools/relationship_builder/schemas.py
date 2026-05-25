"""Atomic FK operations on application/schemas.py.

Inserts the FK as a scalar column in `<Pascal>Base`, `Update<Pascal>Request`,
and `<Pascal>ListResponse`, plus the three `json_schema_extra` examples.
Nested relationship shape (embedded vs. ID-only) is intentionally left to the
LLM — this only wires the scalar FK column.
"""

from .class_ops import append_to_class_body, insert_before_model_config, insert_in_example


def add_fk_to_schemas(
    content: str, target_pascal: str, fk_name: str, nullable: bool
) -> tuple[str, bool, str]:
    if f"{fk_name}:" in content:
        return content, False, f"{fk_name} already in schemas"

    required_token = "None" if nullable else "..."
    py_type = "Optional[int]" if nullable else "int"

    base_line = f"{fk_name}: {py_type} = Field({required_token}, gt=0)"
    content, base_ok = append_to_class_body(content, f"{target_pascal}Base", base_line)

    update_line = f"{fk_name}: Optional[int] = Field(None, gt=0)"
    content, update_ok = insert_before_model_config(
        content, f"Update{target_pascal}Request", update_line
    )

    list_line = f"{fk_name}: {py_type}"
    content, list_ok = insert_before_model_config(
        content, f"{target_pascal}ListResponse", list_line
    )

    example_entry = f'"{fk_name}": 1,'
    ex_results: list[bool] = []
    for cls in (
        f"Create{target_pascal}Request",
        f"{target_pascal}Response",
        f"{target_pascal}ListResponse",
    ):
        content, ok = insert_in_example(content, cls, example_entry)
        ex_results.append(ok)

    any_ok = base_ok or update_ok or list_ok or any(ex_results)
    desc = (
        f"Added {fk_name} to schemas "
        f"(base={base_ok}, update={update_ok}, list={list_ok}, examples={sum(ex_results)}/3)"
    )
    return content, any_ok, desc

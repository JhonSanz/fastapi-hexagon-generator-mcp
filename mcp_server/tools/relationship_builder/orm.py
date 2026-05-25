"""Atomic FK operations on infrastructure/models.py (SQLAlchemy ORM models)."""

from typing import Optional

from .insertion import add_to_import, insert_after, insert_before


def add_fk_column(
    content: str, fk_table: str, *, nullable: bool, unique: bool = False
) -> tuple[str, bool, str]:
    """Insert a ForeignKey column before `created_at: Mapped`."""
    col_name = f"{fk_table}_id"

    if f"{col_name}: Mapped" in content:
        return content, False, f"{col_name} column already exists"

    nullable_str = "True" if nullable else "False"
    mapped_type = "Optional[int]" if nullable else "int"
    unique_part = ", unique=True" if unique else ""

    fk_line = (
        f"{col_name}: Mapped[{mapped_type}] = mapped_column("
        f'ForeignKey("{fk_table}.id"), nullable={nullable_str}{unique_part})'
    )

    content, ok = insert_before(content, "created_at: Mapped", [fk_line, ""])
    content = add_to_import(content, "sqlalchemy", "ForeignKey")
    return content, ok, f"Added {col_name} FK column"


def add_relationship(
    content: str,
    attr_name: str,
    target_orm_class: str,
    back_populates: str,
    *,
    is_list: bool = True,
    uselist: Optional[bool] = None,
    secondary: Optional[str] = None,
) -> tuple[str, bool, str]:
    """Insert a SQLAlchemy `relationship()` declaration after `updated_at: Mapped`."""
    if f"{attr_name}: Mapped" in content and "relationship" in content:
        return content, False, f"{attr_name} relationship already exists"

    mapped = (
        f'Mapped[list["{target_orm_class}"]]'
        if is_list
        else f'Mapped["{target_orm_class}"]'
    )

    kwargs = [f'back_populates="{back_populates}"']
    if uselist is not None:
        kwargs.append(f"uselist={uselist}")
    if secondary:
        kwargs.append(f'secondary="{secondary}"')

    rel_line = f'{attr_name}: {mapped} = relationship({", ".join(kwargs)})'

    content, ok = insert_after(content, "updated_at: Mapped", ["", rel_line])
    content = add_to_import(content, "sqlalchemy.orm", "relationship")
    return content, ok, f"Added {attr_name} relationship"

"""Atomic FK operations on infrastructure/database.py (entity mapper)."""

from .insertion import insert_before


def add_fk_to_mapper(content: str, fk_name: str) -> tuple[str, bool, str]:
    """Add FK assignment to the `_to_entity` mapper, just before `created_at=...`."""
    if f"{fk_name}=orm_obj" in content:
        return content, False, f"{fk_name} already in mapper"

    mapper_line = f"{fk_name}=orm_obj.{fk_name},"
    content, ok = insert_before(content, "created_at=orm_obj.created_at", [mapper_line])
    return content, ok, f"Added {fk_name} to mapper"

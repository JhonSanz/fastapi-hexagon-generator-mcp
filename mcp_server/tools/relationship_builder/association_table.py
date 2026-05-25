"""Many-to-many association table creation in src/common/association_tables.py."""

from pathlib import Path


def ensure_association_table(
    path: Path, assoc_name: str, source_snake: str, target_snake: str
) -> tuple[bool, str]:
    """Create or append an association table definition.

    Creates the file with its imports if it doesn't exist. Returns (modified, description).
    """
    table_def = (
        f"\n\n{assoc_name} = Table(\n"
        f'    "{assoc_name}",\n'
        f"    Base.metadata,\n"
        f'    Column("{source_snake}_id", ForeignKey("{source_snake}.id"), primary_key=True),\n'
        f'    Column("{target_snake}_id", ForeignKey("{target_snake}.id"), primary_key=True),\n'
        f")"
    )

    if path.exists():
        content = path.read_text(encoding="utf-8")
        if assoc_name in content:
            return False, "Association table already exists"
        path.write_text(content + table_def, encoding="utf-8")
        return True, f"Added {assoc_name} table"

    content = (
        "from sqlalchemy import Column, ForeignKey, Table\n\n"
        "from src.common.db import Base\n"
        + table_def
        + "\n"
    )
    path.write_text(content, encoding="utf-8")
    return True, f"Created file with {assoc_name} table"

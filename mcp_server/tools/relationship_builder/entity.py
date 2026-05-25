"""Atomic FK operations on domain/entities.py."""

from .class_ops import append_to_class_body, insert_before_first_default
from .insertion import insert_before


def add_fk_to_entity(
    content: str, target_pascal: str, fk_name: str, nullable: bool
) -> tuple[str, bool, str]:
    """Add the FK field to the main entity, CreateData, and UpdateData.

    - Main entity: required FK goes before `created_at`; nullable FK is
      appended at end of the class (after `updated_at`) to avoid dataclass
      TypeError (required-after-default).
    - CreateData: required FK is inserted before the first defaulted field
      (or appended if none); nullable FK is appended at the end.
    - UpdateData: always Optional, appended at the end.
    """
    if f"{fk_name}:" in content:
        return content, False, f"{fk_name} already exists"

    main_line = (
        f"{fk_name}: Optional[int] = None" if nullable else f"{fk_name}: int"
    )

    if nullable:
        content, main_ok = append_to_class_body(content, target_pascal, main_line)
    else:
        content, main_ok = insert_before(content, "created_at: datetime", [main_line])

    if nullable:
        content, create_ok = append_to_class_body(content, f"Create{target_pascal}Data", main_line)
    else:
        content, create_ok = insert_before_first_default(content, f"Create{target_pascal}Data", main_line)

    update_line = f"{fk_name}: Optional[int] = None"
    content, update_ok = append_to_class_body(content, f"Update{target_pascal}Data", update_line)

    parts = []
    if main_ok:
        parts.append("entity")
    if create_ok:
        parts.append(f"Create{target_pascal}Data")
    if update_ok:
        parts.append(f"Update{target_pascal}Data")

    if parts:
        return content, True, f"Added {fk_name} to {', '.join(parts)}"
    return content, False, f"Failed to add {fk_name}"

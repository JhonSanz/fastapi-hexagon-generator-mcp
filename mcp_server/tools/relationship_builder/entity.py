"""Atomic FK operations on domain/entities.py."""

import re

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
        f"{fk_name}: int | None = None" if nullable else f"{fk_name}: int"
    )

    if nullable:
        content, main_ok = append_to_class_body(content, target_pascal, main_line)
    else:
        content, main_ok = insert_before(content, "created_at: datetime", [main_line])

    if nullable:
        content, create_ok = append_to_class_body(content, f"Create{target_pascal}Data", main_line)
    else:
        content, create_ok = insert_before_first_default(content, f"Create{target_pascal}Data", main_line)

    update_line = f"{fk_name}: int | None = None"
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


def add_reverse_to_source_entity(
    content: str,
    source_pascal: str,
    field_name: str,
    related_snake: str,
    related_pascal: str,
    is_list: bool,
) -> tuple[str, bool, str]:
    """Add the inverse-side field to the source's main entity.

    For one_to_many: `products: list[Product] = field(default_factory=list)`.
    For one_to_one:  `product: Product | None = None`.

    Always appended at the end of the class (after `updated_at`), since the
    field carries a default and would otherwise break dataclass ordering.
    Inserts the related-entity import and, for the list case, the `field`
    import, if not already present.
    """
    if re.search(rf"^\s+{re.escape(field_name)}\s*:", content, re.MULTILINE):
        return content, False, f"{field_name} already exists on {source_pascal}"

    if is_list:
        field_line = f"{field_name}: list[{related_pascal}] = field(default_factory=list)"
    else:
        field_line = f"{field_name}: {related_pascal} | None = None"

    content = _ensure_dataclass_import(content, "field") if is_list else content
    content = _ensure_related_import(content, related_snake, related_pascal)

    content, ok = append_to_class_body(content, source_pascal, field_line)
    if not ok:
        return content, False, f"Failed to add {field_name} to {source_pascal}"
    return content, True, f"Added {field_name} to {source_pascal}"


def _ensure_dataclass_import(content: str, name: str) -> str:
    pattern = re.compile(r"^from\s+dataclasses\s+import\s+([^\n]+)$", re.MULTILINE)
    match = pattern.search(content)
    if not match:
        return f"from dataclasses import {name}\n" + content
    names = [n.strip() for n in match.group(1).split(",")]
    if name in names:
        return content
    new_line = f"from dataclasses import {', '.join(names + [name])}"
    return content[: match.start()] + new_line + content[match.end():]


def _ensure_related_import(content: str, related_snake: str, related_pascal: str) -> str:
    import_line = f"from src.{related_snake}.domain.entities import {related_pascal}"
    if import_line in content:
        return content
    last_import = 0
    for match in re.finditer(r"^(from\s+\S+\s+import\s+[^\n]+|import\s+[^\n]+)$", content, re.MULTILINE):
        last_import = match.end()
    if last_import == 0:
        return import_line + "\n" + content
    return content[:last_import] + "\n" + import_line + content[last_import:]

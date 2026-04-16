"""Build relationships between hexagonal modules."""

import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _to_pascal(name: str) -> str:
    if "_" in name:
        return "".join(w.capitalize() for w in name.split("_"))
    return name[0].upper() + name[1:] if name else name


def _to_snake(name: str) -> str:
    s = re.sub(r"([A-Z])", r"_\1", name).lower().lstrip("_")
    return s.replace("__", "_")


def _pluralize(name: str) -> str:
    if name.endswith(("s", "x", "z")):
        return name + "es"
    if name.endswith("sh") or name.endswith("ch"):
        return name + "es"
    if name.endswith("y") and len(name) > 1 and name[-2] not in "aeiou":
        return name[:-1] + "ies"
    return name + "s"


# ── Insertion helpers ────────────────────────────────────────────


def _insert_before(content: str, marker: str, new_lines: list[str]) -> tuple[str, bool]:
    """Insert lines before the first line containing *marker*, matching its indent."""
    lines = content.split("\n")
    for i, line in enumerate(lines):
        if marker in line:
            indent = line[: len(line) - len(line.lstrip())]
            indented = [f"{indent}{l}" for l in new_lines]
            return "\n".join(lines[:i] + indented + lines[i:]), True
    return content, False


def _insert_after(content: str, marker: str, new_lines: list[str]) -> tuple[str, bool]:
    """Insert lines after the **last** line containing *marker*, matching its indent."""
    lines = content.split("\n")
    last = -1
    for i, line in enumerate(lines):
        if marker in line:
            last = i
    if last == -1:
        return content, False
    indent = lines[last][: len(lines[last]) - len(lines[last].lstrip())]
    indented = [f"{indent}{l}" if l.strip() else "" for l in new_lines]
    return "\n".join(lines[: last + 1] + indented + lines[last + 1 :]), True


# ── Import helpers ───────────────────────────────────────────────


def _add_to_sqlalchemy_import(content: str, *type_names: str) -> str:
    """Add types to the ``from sqlalchemy import ...`` line."""
    match = re.search(r"^from sqlalchemy import (.+)$", content, re.MULTILINE)
    if not match:
        return content
    existing = {t.strip() for t in match.group(1).split(",")}
    if set(type_names).issubset(existing):
        return content
    all_types = sorted(existing | set(type_names))
    return (
        content[: match.start()]
        + f"from sqlalchemy import {', '.join(all_types)}"
        + content[match.end() :]
    )


def _add_to_orm_import(content: str, *names: str) -> str:
    """Add names to the ``from sqlalchemy.orm import ...`` line."""
    match = re.search(r"^from sqlalchemy\.orm import (.+)$", content, re.MULTILINE)
    if not match:
        return content
    existing = {t.strip() for t in match.group(1).split(",")}
    if set(names).issubset(existing):
        return content
    all_names = sorted(existing | set(names))
    return (
        content[: match.start()]
        + f"from sqlalchemy.orm import {', '.join(all_names)}"
        + content[match.end() :]
    )


# ── Builder ──────────────────────────────────────────────────────


class RelationshipBuilder:
    """Builds relationships between two hexagonal modules."""

    VALID_TYPES = ("one_to_many", "many_to_many", "one_to_one")

    def __init__(
        self,
        *,
        source_module: str,
        target_module: str,
        relation_type: str,
        project_path: str,
        nullable: bool = False,
    ):
        self.source_snake = _to_snake(source_module)
        self.target_snake = _to_snake(target_module)
        self.source_pascal = _to_pascal(source_module)
        self.target_pascal = _to_pascal(target_module)
        self.relation_type = relation_type
        self.project_path = Path(project_path)
        self.nullable = nullable
        self._mods: list[dict[str, Any]] = []

    def _src(self, module: str, *parts: str) -> Path:
        return self.project_path / "src" / module / Path(*parts)

    def _record(self, path: str, modified: bool, desc: str):
        self._mods.append({"file": path, "modified": modified, "description": desc})

    # ── Atomic operations ────────────────────────────────────────

    def _add_fk_column(self, orm_module: str, fk_table: str, *, unique: bool = False):
        """Add a ForeignKey column to an ORM model file."""
        path = self._src(orm_module, "infrastructure", "models.py")
        if not path.exists():
            self._record(str(path), False, "File not found")
            return

        content = path.read_text(encoding="utf-8")
        col_name = f"{fk_table}_id"

        if f"{col_name}: Mapped" in content:
            self._record(str(path), False, f"{col_name} column already exists")
            return

        nullable_str = "True" if self.nullable else "False"
        mapped_type = "Optional[int]" if self.nullable else "int"
        unique_part = ", unique=True" if unique else ""

        fk_line = (
            f"{col_name}: Mapped[{mapped_type}] = mapped_column("
            f'ForeignKey("{fk_table}.id"), nullable={nullable_str}{unique_part})'
        )

        content, ok = _insert_before(content, "created_at: Mapped", [fk_line])
        content = _add_to_sqlalchemy_import(content, "ForeignKey")

        if ok:
            path.write_text(content, encoding="utf-8")
        self._record(str(path), ok, f"Added {col_name} FK column")

    def _add_orm_relationship(
        self,
        orm_module: str,
        attr_name: str,
        target_orm_class: str,
        back_populates: str,
        *,
        is_list: bool = True,
        uselist: bool | None = None,
        secondary: str | None = None,
    ):
        """Add a relationship() declaration to an ORM model file."""
        path = self._src(orm_module, "infrastructure", "models.py")
        if not path.exists():
            self._record(str(path), False, "File not found")
            return

        content = path.read_text(encoding="utf-8")

        if f"{attr_name}: Mapped" in content and "relationship" in content:
            self._record(str(path), False, f"{attr_name} relationship already exists")
            return

        mapped = f'Mapped[list["{target_orm_class}"]]' if is_list else f'Mapped["{target_orm_class}"]'

        kwargs = [f'back_populates="{back_populates}"']
        if uselist is not None:
            kwargs.append(f"uselist={uselist}")
        if secondary:
            kwargs.append(f'secondary="{secondary}"')

        rel_line = f'{attr_name}: {mapped} = relationship({", ".join(kwargs)})'

        content, ok = _insert_after(content, "updated_at: Mapped", ["", rel_line])
        content = _add_to_orm_import(content, "relationship")

        if ok:
            path.write_text(content, encoding="utf-8")
        self._record(str(path), ok, f"Added {attr_name} relationship")

    def _add_fk_to_entity(self, entity_module: str, fk_name: str):
        """Add FK field to the main domain entity (before created_at)."""
        path = self._src(entity_module, "domain", "entities.py")
        if not path.exists():
            self._record(str(path), False, "File not found")
            return

        content = path.read_text(encoding="utf-8")

        if f"{fk_name}:" in content:
            self._record(str(path), False, f"{fk_name} already exists")
            return

        field_line = f"{fk_name}: Optional[int] = None" if self.nullable else f"{fk_name}: int"
        content, ok = _insert_before(content, "created_at: datetime", [field_line])

        if ok:
            path.write_text(content, encoding="utf-8")
        self._record(str(path), ok, f"Added {fk_name} to entity")

    def _add_fk_to_mapper(self, mapper_module: str, fk_name: str):
        """Add FK field to the _to_entity mapper in database.py."""
        path = self._src(mapper_module, "infrastructure", "database.py")
        if not path.exists():
            self._record(str(path), False, "File not found")
            return

        content = path.read_text(encoding="utf-8")

        if f"{fk_name}=orm_obj" in content:
            self._record(str(path), False, f"{fk_name} already in mapper")
            return

        mapper_line = f"{fk_name}=orm_obj.{fk_name},"
        content, ok = _insert_before(content, "created_at=orm_obj.created_at", [mapper_line])

        if ok:
            path.write_text(content, encoding="utf-8")
        self._record(str(path), ok, f"Added {fk_name} to mapper")

    # ── Relationship strategies ──────────────────────────────────

    def _build_one_to_many(self):
        """Source has many targets. FK on target side."""
        plural_target = _pluralize(self.target_snake)
        fk_name = f"{self.source_snake}_id"

        # Target ORM: FK column + relationship back to source
        self._add_fk_column(self.target_snake, self.source_snake)
        self._add_orm_relationship(
            self.target_snake, self.source_snake, f"{self.source_pascal}ORM",
            back_populates=plural_target, is_list=False,
        )

        # Source ORM: list relationship to targets
        self._add_orm_relationship(
            self.source_snake, plural_target, f"{self.target_pascal}ORM",
            back_populates=self.source_snake, is_list=True,
        )

        # Target entity + mapper
        self._add_fk_to_entity(self.target_snake, fk_name)
        self._add_fk_to_mapper(self.target_snake, fk_name)

    def _build_one_to_one(self):
        """Source has one target. FK on target side with unique constraint."""
        fk_name = f"{self.source_snake}_id"

        # Target ORM: unique FK + relationship
        self._add_fk_column(self.target_snake, self.source_snake, unique=True)
        self._add_orm_relationship(
            self.target_snake, self.source_snake, f"{self.source_pascal}ORM",
            back_populates=self.target_snake, is_list=False,
        )

        # Source ORM: relationship with uselist=False
        self._add_orm_relationship(
            self.source_snake, self.target_snake, f"{self.target_pascal}ORM",
            back_populates=self.source_snake, is_list=False, uselist=False,
        )

        # Target entity + mapper
        self._add_fk_to_entity(self.target_snake, fk_name)
        self._add_fk_to_mapper(self.target_snake, fk_name)

    def _build_many_to_many(self):
        """Both sides have many. Creates association table."""
        plural_target = _pluralize(self.target_snake)
        plural_source = _pluralize(self.source_snake)
        assoc_name = f"{self.source_snake}_{self.target_snake}"

        # Association table
        assoc_path = self.project_path / "src" / "common" / "association_tables.py"
        table_def = (
            f"\n\n{assoc_name} = Table(\n"
            f'    "{assoc_name}",\n'
            f"    Base.metadata,\n"
            f'    Column("{self.source_snake}_id", ForeignKey("{self.source_snake}.id"), primary_key=True),\n'
            f'    Column("{self.target_snake}_id", ForeignKey("{self.target_snake}.id"), primary_key=True),\n'
            f")"
        )

        if assoc_path.exists():
            content = assoc_path.read_text(encoding="utf-8")
            if assoc_name in content:
                self._record(str(assoc_path), False, "Association table already exists")
            else:
                content += table_def
                assoc_path.write_text(content, encoding="utf-8")
                self._record(str(assoc_path), True, f"Added {assoc_name} table")
        else:
            content = (
                "from sqlalchemy import Column, ForeignKey, Table\n\n"
                "from src.common.db import Base\n"
                + table_def
                + "\n"
            )
            assoc_path.write_text(content, encoding="utf-8")
            self._record(str(assoc_path), True, f"Created file with {assoc_name} table")

        # Source ORM: relationship with secondary
        self._add_orm_relationship(
            self.source_snake, plural_target, f"{self.target_pascal}ORM",
            back_populates=plural_source, is_list=True, secondary=assoc_name,
        )

        # Target ORM: relationship with secondary
        self._add_orm_relationship(
            self.target_snake, plural_source, f"{self.source_pascal}ORM",
            back_populates=plural_target, is_list=True, secondary=assoc_name,
        )

    # ── Main entry point ─────────────────────────────────────────

    def build(self) -> dict[str, Any]:
        builders = {
            "one_to_many": self._build_one_to_many,
            "many_to_many": self._build_many_to_many,
            "one_to_one": self._build_one_to_one,
        }
        builder = builders.get(self.relation_type)
        if not builder:
            valid = ", ".join(self.VALID_TYPES)
            return {
                "success": False,
                "error": f"Unknown relation_type '{self.relation_type}'. Use: {valid}",
            }

        builder()

        files_modified = [m["file"] for m in self._mods if m["modified"]]
        plural_target = _pluralize(self.target_snake)

        remaining_todos = [
            "Configure cascade and lazy loading in relationship() declarations",
            f"Update {self.target_pascal} schemas (Create/Update/Response) to include {self.source_snake}_id",
            f"Update {self.source_pascal} Response schema if nested {plural_target} should be included",
        ]

        return {
            "success": True,
            "relation": f"{self.source_snake} -> {self.target_snake} ({self.relation_type})",
            "files_modified": files_modified,
            "details": self._mods,
            "remaining_todos": remaining_todos,
        }

"""Propagate field definitions across all hexagonal architecture layers."""

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

RESERVED_NAMES = {"id", "created_at", "updated_at"}

# Python type -> (SQLAlchemy type constructor, extra imports needed)
SQLALCHEMY_TYPE_MAP = {
    "str": ("String", "String"),
    "int": ("Integer", "Integer"),
    "float": ("Float", "Float"),
    "bool": ("Boolean", "Boolean"),
    "datetime": ("DateTime(timezone=True)", "DateTime"),
    "date": ("Date", "Date"),
    "Decimal": ("Numeric", "Numeric"),
}

KNOWN_TYPES = set(SQLALCHEMY_TYPE_MAP.keys())


@dataclass
class FieldDefinition:
    """Validated field specification."""

    name: str
    type: str
    max_length: Optional[int] = None
    min_length: Optional[int] = None
    nullable: bool = False
    description: Optional[str] = None
    searchable: bool = False
    gt: Optional[float] = None
    ge: Optional[float] = None
    lt: Optional[float] = None
    le: Optional[float] = None

    def __post_init__(self):
        if self.name in RESERVED_NAMES:
            raise ValueError(f"Field name '{self.name}' is reserved (used by base template)")

    @property
    def is_known_type(self) -> bool:
        return self.type in KNOWN_TYPES


def _find_todo_block(lines: list[str], todo_substring: str) -> tuple[int, int]:
    """Find a TODO comment block: the TODO line + following comment/pass lines.

    Returns (start, end) line indices. end is exclusive.
    Returns (-1, -1) if not found.
    """
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("#") and "TODO" in stripped and todo_substring in stripped:
            # Found the TODO line, now consume comment block + optional pass
            end = i + 1
            while end < len(lines):
                next_stripped = lines[end].strip()
                if next_stripped.startswith("#"):
                    end += 1
                elif next_stripped == "pass":
                    end += 1
                    break
                else:
                    break
            return i, end
    return -1, -1


def _get_indent(line: str) -> str:
    """Extract leading whitespace from a line."""
    return line[: len(line) - len(line.lstrip())]


def _replace_todo_block(
    content: str, todo_substring: str, replacement_lines: list[str]
) -> tuple[str, bool]:
    """Replace a TODO block in file content with generated code.

    Returns (new_content, was_replaced).
    """
    lines = content.split("\n")
    start, end = _find_todo_block(lines, todo_substring)

    if start == -1:
        return content, False

    indent = _get_indent(lines[start])
    indented = [f"{indent}{line}" if line else "" for line in replacement_lines]

    new_lines = lines[:start] + indented + lines[end:]
    return "\n".join(new_lines), True


def _find_class_bounds(lines: list[str], class_name: str) -> tuple[int, int]:
    """Return (start, end_exclusive) line indices for a class definition."""
    start = -1
    for i, line in enumerate(lines):
        if re.match(rf"^class\s+{re.escape(class_name)}\b", line):
            start = i
            break
    if start == -1:
        return -1, -1
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if re.match(r"^class\s+\w+", lines[j]):
            end = j
            break
    return start, end


class FieldPropagator:
    """Propagates field definitions to all hexagonal layers."""

    def __init__(
        self,
        *,
        module_name: str,
        project_path: str,
        fields: list[dict[str, Any]],
    ):
        self.module_name = module_name
        self.project_path = Path(project_path)
        self.fields = [FieldDefinition(**f) for f in fields]
        self.pascal_name = self._to_pascal(module_name)
        self.snake_name = self._to_snake(module_name)

    @staticmethod
    def _to_pascal(name: str) -> str:
        if "_" in name:
            return "".join(w.capitalize() for w in name.split("_"))
        return name[0].upper() + name[1:] if name else name

    @staticmethod
    def _to_snake(name: str) -> str:
        s = re.sub(r"([A-Z])", r"_\1", name).lower().lstrip("_")
        return s.replace("__", "_")

    def _module_src(self, *parts: str) -> Path:
        return self.project_path / "src" / self.snake_name / Path(*parts)

    # ── Entity generation ─────────────────────────────────────────

    def _entity_field(self, f: FieldDefinition, optional_all: bool = False) -> str:
        """Generate a dataclass field line."""
        if not f.is_known_type:
            return f"{f.name}: ...  # TODO: Define type for '{f.type}' field"
        py_type = f.type
        if f.nullable or optional_all:
            return f"{f.name}: Optional[{py_type}] = None"
        return f"{f.name}: {py_type}"

    def _update_entities(self) -> tuple[str, bool, int]:
        """Update domain/entities.py with field definitions."""
        path = self._module_src("domain", "entities.py")
        if not path.exists():
            return str(path), False, 0

        content = path.read_text(encoding="utf-8")
        replaced_count = 0

        # Main entity: required fields go in the TODO block; nullable fields are
        # appended AFTER the class (after created_at/updated_at) to respect
        # dataclass ordering — the template has non-default fields after the TODO.
        required_fields = [f for f in self.fields if not f.nullable]
        nullable_fields = [f for f in self.fields if f.nullable]

        main_required = [self._entity_field(f) for f in required_fields]
        content, ok = _replace_todo_block(content, "Add your domain fields here", main_required)
        if ok:
            replaced_count += 1

        # CreateData: required first, nullable last (no trailing non-default → safe)
        sorted_fields = sorted(self.fields, key=lambda f: f.nullable)
        create_fields = [self._entity_field(f) for f in sorted_fields]
        content, ok = _replace_todo_block(content, "Add your fields here", create_fields)
        if ok:
            replaced_count += 1

        # UpdateData fields (all Optional)
        update_fields = [self._entity_field(f, optional_all=True) for f in self.fields]
        content, ok = _replace_todo_block(content, "Add your fields here (all Optional)", update_fields)
        if ok:
            replaced_count += 1

        # Add Decimal import if needed
        if any(f.type == "Decimal" for f in self.fields) and "from decimal import Decimal" not in content:
            content = "from decimal import Decimal\n" + content

        if replaced_count > 0:
            path.write_text(content, encoding="utf-8")

        return str(path), replaced_count > 0, replaced_count

    # ── ORM Models generation ─────────────────────────────────────

    def _model_column(self, f: FieldDefinition) -> str:
        """Generate a SQLAlchemy mapped_column line."""
        if not f.is_known_type:
            return f"# TODO: Define column for '{f.name}' (type: {f.type})"

        sa_type_expr, _ = SQLALCHEMY_TYPE_MAP[f.type]

        # String with max_length
        if f.type == "str" and f.max_length:
            sa_type_expr = f"String({f.max_length})"
        elif f.type == "str":
            sa_type_expr = "Text"

        nullable = "True" if f.nullable else "False"
        mapped_type = f.type
        if mapped_type == "datetime":
            mapped_type = "datetime"
        if f.nullable:
            mapped_type = f"Optional[{mapped_type}]"

        parts = [sa_type_expr, f"nullable={nullable}"]

        # Index searchable string fields
        if f.searchable and f.type == "str":
            parts.append("index=True")

        return f"{f.name}: Mapped[{mapped_type}] = mapped_column({', '.join(parts)})"

    def _update_models(self) -> tuple[str, bool, int]:
        """Update infrastructure/models.py with column definitions."""
        path = self._module_src("infrastructure", "models.py")
        if not path.exists():
            return str(path), False, 0

        content = path.read_text(encoding="utf-8")

        columns = [self._model_column(f) for f in self.fields]
        content, ok = _replace_todo_block(content, "Add your model columns here", columns)

        if ok:
            # Add missing SQLAlchemy imports (skip custom types)
            needed_types = set()
            for f in self.fields:
                if not f.is_known_type:
                    continue
                _, import_name = SQLALCHEMY_TYPE_MAP[f.type]
                needed_types.add(import_name)
                if f.type == "str" and not f.max_length:
                    needed_types.add("Text")

            import_line_re = re.compile(r"^from sqlalchemy import (.+)$", re.MULTILINE)
            match = import_line_re.search(content)
            if match:
                existing = {t.strip() for t in match.group(1).split(",")}
                all_types = sorted(existing | needed_types)
                content = content[: match.start()] + f"from sqlalchemy import {', '.join(all_types)}" + content[match.end():]

            path.write_text(content, encoding="utf-8")

        return str(path), ok, 1 if ok else 0

    # ── Pydantic Schemas generation ───────────────────────────────

    def _schema_field(self, f: FieldDefinition, optional: bool = False) -> str:
        """Generate a Pydantic Field() line."""
        if not f.is_known_type:
            return f"# TODO: Define schema field for '{f.name}' (type: {f.type})"

        py_type = f.type
        if py_type == "datetime":
            py_type = "datetime"

        kwargs = []
        if optional:
            py_type = f"Optional[{py_type}]"
            kwargs.append("None")
        else:
            if not f.nullable:
                kwargs.append("...")
            else:
                py_type = f"Optional[{py_type}]"
                kwargs.append("None")

        if f.type == "str":
            if f.min_length is not None:
                kwargs.append(f"min_length={f.min_length}")
            elif not optional and not f.nullable:
                kwargs.append("min_length=1")
            if f.max_length is not None:
                kwargs.append(f"max_length={f.max_length}")

        for constraint in ("gt", "ge", "lt", "le"):
            val = getattr(f, constraint, None)
            if val is not None:
                kwargs.append(f"{constraint}={val}")

        if f.description:
            kwargs.append(f'description="{f.description}"')

        return f'{f.name}: {py_type} = Field({", ".join(kwargs)})'

    def _schema_example_value(self, f: FieldDefinition) -> str:
        """Generate an example value for json_schema_extra."""
        if not f.is_known_type:
            return f'# TODO: Add example for \'{f.name}\' (type: {f.type})'

        examples = {
            "str": f'"Example {f.name}"',
            "int": "1",
            "float": "1.0",
            "bool": "True",
            "datetime": '"2024-01-15T10:30:00"',
            "date": '"2024-01-15"',
            "Decimal": '"10.50"',
        }
        return f'"{f.name}": {examples.get(f.type, "None")},'

    def _update_schemas(self) -> tuple[str, bool, int]:
        """Update application/schemas.py with field definitions."""
        path = self._module_src("application", "schemas.py")
        if not path.exists():
            return str(path), False, 0

        content = path.read_text(encoding="utf-8")
        replaced_count = 0

        # 1. Base schema fields
        base_fields = [self._schema_field(f) for f in self.fields]
        content, ok = _replace_todo_block(content, "Add your model fields here", base_fields)
        if ok:
            replaced_count += 1

        # 2. CreateRequest example
        create_examples = [self._schema_example_value(f) for f in self.fields if not f.nullable]
        content, ok = _replace_todo_block(content, "Add example data", create_examples)
        if ok:
            replaced_count += 1

        # 3. UpdateRequest fields (all optional)
        update_fields = [self._schema_field(f, optional=True) for f in self.fields]
        content, ok = _replace_todo_block(
            content, "Add fields that can be updated", update_fields
        )
        if ok:
            replaced_count += 1

        # 4. UpdateRequest example (second "Add example data" - already consumed first one above)
        update_examples = [self._schema_example_value(f) for f in self.fields[:1]]
        content, ok = _replace_todo_block(content, "Add example data", update_examples)
        if ok:
            replaced_count += 1

        # 5. Response example - "Add your fields"
        response_examples = [self._schema_example_value(f) for f in self.fields]
        content, ok = _replace_todo_block(content, "Add your fields", response_examples)
        if ok:
            replaced_count += 1

        # 6. ListResponse main fields
        list_fields = [f"{f.name}: {f.type}" for f in self.fields if not f.nullable]
        content, ok = _replace_todo_block(
            content, "Add main fields for list view", list_fields
        )
        if ok:
            replaced_count += 1

        # 7. ListResponse example - second "Add your fields"
        list_examples = [self._schema_example_value(f) for f in self.fields if not f.nullable]
        content, ok = _replace_todo_block(content, "Add your fields", list_examples)
        if ok:
            replaced_count += 1

        # 8. FilterParams
        searchable = [f for f in self.fields if f.searchable]
        if searchable:
            filter_fields = []
            for f in searchable:
                filter_fields.append(
                    f'{f.name}: Optional[{f.type}] = Field(None, description="Filter by {f.name}")'
                )
            content, ok = _replace_todo_block(
                content, "Add specific filters for your model", filter_fields
            )
        else:
            content, ok = _replace_todo_block(
                content, "Add specific filters for your model", []
            )
        if ok:
            replaced_count += 1

        # Add Decimal import if needed
        if any(f.type == "Decimal" for f in self.fields) and "from decimal import Decimal" not in content:
            content = "from decimal import Decimal\n" + content

        if replaced_count > 0:
            path.write_text(content, encoding="utf-8")

        return str(path), replaced_count > 0, replaced_count

    # ── Database/Repository generation ────────────────────────────

    def _update_database(self) -> tuple[str, bool, int]:
        """Update infrastructure/database.py with mapper and search fields."""
        path = self._module_src("infrastructure", "database.py")
        if not path.exists():
            return str(path), False, 0

        content = path.read_text(encoding="utf-8")
        replaced_count = 0

        # 1. _to_entity mapper
        mapper_lines = [f"{f.name}=orm_obj.{f.name}," for f in self.fields]
        content, ok = _replace_todo_block(content, "Map your fields here", mapper_lines)
        if ok:
            replaced_count += 1

        # 2. Search fields — the TODO sits above the or_() block, and the
        # commented-out example sits *inside* it.  We replace both:
        #   a) Remove the TODO + comment lines above search_pattern
        #   b) Replace the commented example inside or_() with real fields
        searchable = [f for f in self.fields if f.searchable and f.type == "str"]

        # a) Remove the TODO block itself (leaves search_pattern and or_() intact)
        content, ok = _replace_todo_block(
            content, "Customize search fields based on your model", []
        )
        if ok:
            replaced_count += 1

        # b) Replace the commented example inside or_() with actual ilike calls
        lines = content.split("\n")
        new_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#") and "ORM." in stripped and "ilike(search_pattern)" in stripped:
                if searchable:
                    indent = _get_indent(line)
                    for sf in searchable:
                        new_lines.append(f"{indent}{self.pascal_name}ORM.{sf.name}.ilike(search_pattern),")
                # else: remove the commented line entirely
                continue
            new_lines.append(line)
        content = "\n".join(new_lines)

        # 3. Custom filters
        filter_fields = [f for f in self.fields if f.searchable]
        if filter_fields:
            filter_lines = []
            for f in filter_fields:
                filter_lines.append(f'if {f.name}_val := filters.get("{f.name}"):')
                filter_lines.append(f"    stmt = stmt.where({self.pascal_name}ORM.{f.name} == {f.name}_val)")
        else:
            filter_lines = ["# No custom filters defined"]
        content, ok = _replace_todo_block(
            content, "Apply custom filters", filter_lines
        )
        if ok:
            replaced_count += 1

        if replaced_count > 0:
            path.write_text(content, encoding="utf-8")

        return str(path), replaced_count > 0, replaced_count

    # ── Main entry point ──────────────────────────────────────────

    def propagate(self) -> dict[str, Any]:
        """Propagate all fields to all layers. Returns summary dict."""
        results = []
        total_replaced = 0

        for updater in (
            self._update_entities,
            self._update_models,
            self._update_schemas,
            self._update_database,
        ):
            file_path, modified, count = updater()
            results.append({
                "file": file_path,
                "modified": modified,
                "todos_completed": count,
            })
            total_replaced += count

        files_modified = [r["file"] for r in results if r["modified"]]
        custom_fields = [f.name for f in self.fields if not f.is_known_type]

        result: dict[str, Any] = {
            "success": True,
            "module": self.snake_name,
            "fields_defined": len(self.fields),
            "files_modified": files_modified,
            "todos_completed": total_replaced,
            "details": results,
        }
        if custom_fields:
            result["custom_fields_as_todo"] = custom_fields
            result["custom_hint"] = (
                f"Fields {custom_fields} have unknown types and were placed as TODOs. "
                "Use complete_todos with action='guidance' or edit manually."
            )
        return result

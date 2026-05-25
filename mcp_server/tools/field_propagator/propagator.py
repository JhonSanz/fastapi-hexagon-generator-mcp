"""Orchestrator: propagate field definitions across all hexagonal layers."""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from hexagon_generator.utils.validators import normalize_name

from . import database, entities, models, schemas
from .field import FieldDefinition

logger = logging.getLogger(__name__)


@dataclass
class LayerResult:
    file: str
    todos_completed: int

    @property
    def modified(self) -> bool:
        return self.todos_completed > 0


Mutator = Callable[[str], tuple[str, int]]


class FieldPropagator:
    """Propagate field definitions to entities, ORM models, schemas, and database mapper."""

    def __init__(
        self,
        *,
        module_name: str,
        project_path: str,
        fields: list[dict[str, Any]],
    ):
        self.project_path = Path(project_path)
        self.fields = [FieldDefinition(**f) for f in fields]
        self.pascal_name, self.snake_name = normalize_name(module_name)

    def propagate(self) -> dict[str, Any]:
        results = [
            self._edit(self._src("domain", "entities.py"), self._wrap_decimal(entities.apply)),
            self._edit(self._src("infrastructure", "models.py"), lambda c: models.apply(c, self.fields)),
            self._edit(self._src("application", "schemas.py"), self._wrap_decimal(schemas.apply)),
            self._edit(self._src("infrastructure", "database.py"),
                       lambda c: database.apply(c, self.fields, self.pascal_name)),
        ]
        total = sum(r.todos_completed for r in results)
        custom_fields = [f.name for f in self.fields if not f.is_known_type]

        result: dict[str, Any] = {
            "success": True,
            "module": self.snake_name,
            "fields_defined": len(self.fields),
            "files_modified": [r.file for r in results if r.modified],
            "todos_completed": total,
            "details": [
                {"file": r.file, "modified": r.modified, "todos_completed": r.todos_completed}
                for r in results
            ],
        }
        if custom_fields:
            result["custom_fields_as_todo"] = custom_fields
            result["custom_hint"] = (
                f"Fields {custom_fields} have unknown types and were placed as TODOs. "
                "Use complete_todos with action='guidance' or edit manually."
            )
        return result

    def _src(self, *parts: str) -> Path:
        return self.project_path / "src" / self.snake_name / Path(*parts)

    def _edit(self, path: Path, mutate: Mutator) -> LayerResult:
        """Read, mutate, write a file; no-op when path is missing."""
        if not path.exists():
            return LayerResult(str(path), 0)

        content = path.read_text(encoding="utf-8")
        new_content, count = mutate(content)
        if count > 0:
            path.write_text(new_content, encoding="utf-8")
        return LayerResult(str(path), count)

    def _wrap_decimal(
        self, layer_apply: Callable[[str, list[FieldDefinition]], tuple[str, int]]
    ) -> Mutator:
        """Wrap a layer's apply() so its output is post-processed with the Decimal import."""
        def mutate(content: str) -> tuple[str, int]:
            content, count = layer_apply(content, self.fields)
            return self._ensure_decimal_import(content), count
        return mutate

    def _ensure_decimal_import(self, content: str) -> str:
        if any(f.type == "Decimal" for f in self.fields) and "from decimal import Decimal" not in content:
            return "from decimal import Decimal\n" + content
        return content

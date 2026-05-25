"""Orchestrator: build relationships between two hexagonal modules."""

import logging
from pathlib import Path
from typing import Any, Callable

from hexagon_generator.utils.validators import normalize_name

from .strategies import STRATEGIES

logger = logging.getLogger(__name__)


# Layer op signature: (content) -> (new_content, modified, description)
LayerOp = Callable[[str], tuple[str, bool, str]]


class RelationshipBuilder:
    """Build a relationship between two hexagonal modules.

    Strategies (one_to_many, one_to_one, many_to_many) drive atomic file-level
    operations via `apply_op` and `record`; this class owns the file I/O and
    the result accumulator.
    """

    def __init__(
        self,
        *,
        source_module: str,
        target_module: str,
        relation_type: str,
        project_path: str,
        nullable: bool = False,
    ):
        self.source_pascal, self.source_snake = normalize_name(source_module)
        self.target_pascal, self.target_snake = normalize_name(target_module)
        self.relation_type = relation_type
        self.project_path = Path(project_path)
        self.nullable = nullable
        self._mods: list[dict[str, Any]] = []

    def build(self) -> dict[str, Any]:
        strategy = STRATEGIES.get(self.relation_type)
        if not strategy:
            valid = ", ".join(STRATEGIES)
            return {
                "success": False,
                "error": f"Unknown relation_type '{self.relation_type}'. Use: {valid}",
            }

        strategy(self)
        return self._response()

    # Helpers exposed to strategy functions ──────────────────────

    def src(self, module: str, *parts: str) -> Path:
        return self.project_path / "src" / module / Path(*parts)

    def record(self, path: str, modified: bool, description: str) -> None:
        self._mods.append({"file": path, "modified": modified, "description": description})

    def apply_op(self, path: Path, op: LayerOp) -> None:
        """Read → run op → conditional write → record outcome."""
        if not path.exists():
            self.record(str(path), False, "File not found")
            return

        content = path.read_text(encoding="utf-8")
        new_content, modified, description = op(content)
        if modified:
            path.write_text(new_content, encoding="utf-8")
        self.record(str(path), modified, description)

    def _response(self) -> dict[str, Any]:
        files_modified = [m["file"] for m in self._mods if m["modified"]]
        remaining_todos = [
            "Configure cascade and lazy loading in relationship() declarations",
            f"Decide nested shape on {self.source_pascal}/{self.target_pascal} responses "
            "(embed object vs. ID-only)",
        ]
        return {
            "success": True,
            "relation": f"{self.source_snake} -> {self.target_snake} ({self.relation_type})",
            "files_modified": files_modified,
            "details": self._mods,
            "remaining_todos": remaining_todos,
        }

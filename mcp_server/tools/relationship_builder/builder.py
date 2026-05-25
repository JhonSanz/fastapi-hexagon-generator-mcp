"""Orchestrator: build relationships between two hexagonal modules."""

import ast
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
        """Read → run op → ast-validate → conditional write → record outcome.

        If the op's new content does not parse, the write is skipped and the
        failure is recorded — protects against subtle insertion bugs that would
        leave the project in an unparseable state.
        """
        if not path.exists():
            self.record(str(path), False, "File not found")
            return

        content = path.read_text(encoding="utf-8")
        new_content, modified, description = op(content)
        if modified:
            try:
                ast.parse(new_content)
            except SyntaxError as e:
                self.record(
                    str(path),
                    False,
                    f"{description} but produced invalid syntax "
                    f"({e.msg} at line {e.lineno}); write skipped",
                )
                return
            path.write_text(new_content, encoding="utf-8")
        self.record(str(path), modified, description)

    def _emit_followup_todos(self) -> list[dict[str, str]]:
        """Inject the judgment-call TODOs into the relevant files as `# TODO:`
        comments and return a summary so list_todos becomes the single source
        of truth."""
        emitted: list[dict[str, str]] = []

        cascade = (
            f"Configure cascade and lazy loading on the new relationship() "
            f"between {self.source_pascal}ORM and {self.target_pascal}ORM"
        )
        nested = (
            f"Decide nested shape on {self.source_pascal}/{self.target_pascal} "
            f"responses (embed object vs. ID-only)"
        )

        for module in (self.source_snake, self.target_snake):
            self._append_todo_to_file(
                self.src(module, "infrastructure", "models.py"), cascade, emitted
            )
            self._append_todo_to_file(
                self.src(module, "application", "schemas.py"), nested, emitted
            )

        if self.relation_type in ("one_to_many", "one_to_one"):
            hydrate = (
                f"Hydrate the inverse field on {self.source_pascal}'s _to_entity "
                f"mapper: map orm_obj's related rows into the new domain field, "
                f"or load lazily."
            )
            self._append_todo_to_file(
                self.src(self.source_snake, "infrastructure", "database.py"),
                hydrate,
                emitted,
            )

        return emitted

    def _append_todo_to_file(
        self, path: Path, todo_text: str, emitted: list[dict[str, str]]
    ) -> None:
        if not path.exists():
            return
        content = path.read_text(encoding="utf-8")
        if todo_text in content:
            return
        if not content.endswith("\n"):
            content += "\n"
        content += f"\n# TODO: {todo_text}\n"
        path.write_text(content, encoding="utf-8")
        emitted.append({"file": str(path), "todo": todo_text})

    def _response(self) -> dict[str, Any]:
        followups = self._emit_followup_todos()
        files_modified = sorted({
            *(m["file"] for m in self._mods if m["modified"]),
            *(t["file"] for t in followups),
        })
        return {
            "success": True,
            "relation": f"{self.source_snake} -> {self.target_snake} ({self.relation_type})",
            "files_modified": files_modified,
            "details": self._mods,
            "followup_todos": followups,
        }

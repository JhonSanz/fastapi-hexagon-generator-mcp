"""Orchestrator: wire a module's router and exception handlers into src/common/."""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Literal

from hexagon_generator.utils.validators import normalize_name

from . import exceptions, router

logger = logging.getLogger(__name__)


Status = Literal["wired", "already_wired", "file_not_found"]

REASON_FOR_STATUS = {
    "wired": "ok",
    "already_wired": "already wired",
    "file_not_found": "file not found",
}


@dataclass
class WireResult:
    file: str
    status: Status

    @property
    def wired(self) -> bool:
        return self.status == "wired"

    def to_dict(self) -> dict[str, Any]:
        return {"file": self.file, "wired": self.wired, "reason": REASON_FOR_STATUS[self.status]}


class ModuleWirer:
    """Register a module's router and exception handlers in src/common/."""

    def __init__(self, *, module_name: str, project_path: str):
        _, self.snake_name = normalize_name(module_name)
        self.upper_name = self.snake_name.upper()
        self.project_path = Path(project_path)

    def wire(self) -> dict[str, Any]:
        router_result = self._wire(
            self._common_path("router.py"),
            lambda c: router.apply(c, self.snake_name),
        )
        exceptions_result = self._wire(
            self._common_path("exceptions_mapping.py"),
            lambda c: exceptions.apply(c, self.snake_name, self.upper_name),
        )

        return {
            "success": True,
            "module": self.snake_name,
            "router_wired": router_result.wired,
            "exceptions_wired": exceptions_result.wired,
            "files_modified": [r.file for r in (router_result, exceptions_result) if r.wired],
            "details": {
                "router": router_result.to_dict(),
                "exceptions": exceptions_result.to_dict(),
            },
        }

    def _common_path(self, filename: str) -> Path:
        return self.project_path / "src" / "common" / filename

    def _wire(
        self,
        path: Path,
        apply_fn: Callable[[str], tuple[str, Literal["wired", "already_wired"]]],
    ) -> WireResult:
        if not path.exists():
            return WireResult(str(path), "file_not_found")

        content = path.read_text(encoding="utf-8")
        new_content, status = apply_fn(content)
        if status == "wired":
            path.write_text(new_content, encoding="utf-8")
        return WireResult(str(path), status)

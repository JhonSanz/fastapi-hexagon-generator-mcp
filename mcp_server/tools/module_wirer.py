"""Auto-wire a module's router and exception handlers into src/common/."""

import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _to_snake(name: str) -> str:
    s = re.sub(r"([A-Z])", r"_\1", name).lower().lstrip("_")
    return s.replace("__", "_")


class ModuleWirer:
    """Registers a module's router and exception handlers in src/common/."""

    def __init__(self, *, module_name: str, project_path: str):
        self.snake_name = _to_snake(module_name)
        self.upper_name = self.snake_name.upper()
        self.project_path = Path(project_path)

    def _common_path(self, filename: str) -> Path:
        return self.project_path / "src" / "common" / filename

    # ── Router wiring ─────────────────────────────────────────────

    def _wire_router(self) -> dict[str, Any]:
        path = self._common_path("router.py")
        if not path.exists():
            return {"file": str(path), "wired": False, "reason": "file not found"}

        content = path.read_text(encoding="utf-8")

        import_line = f"from src.{self.snake_name}.infrastructure.web import router as {self.snake_name}_router"
        include_line = f"api_router.include_router({self.snake_name}_router)"

        # Already wired? Check for uncommented import (not inside a # comment)
        for line in content.split("\n"):
            stripped = line.strip()
            if stripped == import_line or stripped == include_line:
                return {"file": str(path), "wired": False, "reason": "already wired"}

        lines = content.split("\n")
        new_lines = []
        todo_found = False

        i = 0
        while i < len(lines):
            stripped = lines[i].strip()

            # Replace TODO block
            if "TODO" in stripped and "Register your module routers here" in stripped:
                todo_found = True
                # Skip TODO + following comment lines
                i += 1
                while i < len(lines) and lines[i].strip().startswith("#"):
                    i += 1
                # Insert the wiring code
                new_lines.append(import_line)
                new_lines.append(include_line)
                continue

            new_lines.append(lines[i])
            i += 1

        # If no TODO found, append at end
        if not todo_found:
            new_lines.append("")
            new_lines.append(import_line)
            new_lines.append(include_line)

        path.write_text("\n".join(new_lines), encoding="utf-8")
        return {"file": str(path), "wired": True, "reason": "ok"}

    # ── Exception mapping wiring ──────────────────────────────────

    def _wire_exceptions(self) -> dict[str, Any]:
        path = self._common_path("exceptions_mapping.py")
        if not path.exists():
            return {"file": str(path), "wired": False, "reason": "file not found"}

        content = path.read_text(encoding="utf-8")

        mapping_var = f"EXCEPTIONS_{self.upper_name}_MAPPING"
        import_line = f"from src.{self.snake_name}.infrastructure.exception_handlers import {mapping_var}"
        append_line = f"ALL_EXCEPTIONS += {mapping_var}"

        # Already wired? Check for uncommented lines only
        for line in content.split("\n"):
            stripped = line.strip()
            if stripped == import_line or stripped == append_line:
                return {"file": str(path), "wired": False, "reason": "already wired"}

        lines = content.split("\n")
        new_lines = []

        i = 0
        import_todo_found = False
        append_todo_found = False

        while i < len(lines):
            stripped = lines[i].strip()

            # Replace import TODO block
            if "TODO" in stripped and "Import your module exception mappings here" in stripped:
                import_todo_found = True
                i += 1
                while i < len(lines) and lines[i].strip().startswith("#"):
                    i += 1
                new_lines.append(import_line)
                continue

            # Replace append TODO block
            if "TODO" in stripped and "Append your module exception mappings here" in stripped:
                append_todo_found = True
                i += 1
                while i < len(lines) and lines[i].strip().startswith("#"):
                    i += 1
                new_lines.append(append_line)
                continue

            new_lines.append(lines[i])
            i += 1

        # Fallback: if TODOs were already removed, append at appropriate locations
        if not import_todo_found:
            # Insert import after last existing 'from src.' import
            insert_idx = 0
            for idx, line in enumerate(new_lines):
                if line.strip().startswith("from src."):
                    insert_idx = idx + 1
            if insert_idx == 0:
                # Put after the initial block of imports
                for idx, line in enumerate(new_lines):
                    if line.strip().startswith("from ") or line.strip().startswith("import "):
                        insert_idx = idx + 1
            new_lines.insert(insert_idx, import_line)

        if not append_todo_found:
            # Append at end of file
            new_lines.append(append_line)

        path.write_text("\n".join(new_lines), encoding="utf-8")
        return {"file": str(path), "wired": True, "reason": "ok"}

    # ── Main entry point ──────────────────────────────────────────

    def wire(self) -> dict[str, Any]:
        """Wire the module into the project. Returns summary dict."""
        router_result = self._wire_router()
        exceptions_result = self._wire_exceptions()

        files_modified = []
        if router_result["wired"]:
            files_modified.append(router_result["file"])
        if exceptions_result["wired"]:
            files_modified.append(exceptions_result["file"])

        return {
            "success": True,
            "module": self.snake_name,
            "router_wired": router_result["wired"],
            "exceptions_wired": exceptions_result["wired"],
            "files_modified": files_modified,
            "details": {
                "router": router_result,
                "exceptions": exceptions_result,
            },
        }

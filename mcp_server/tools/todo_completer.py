"""Tool to scan and provide structured guidance for completing TODO comments."""

import re
from collections import Counter
from pathlib import Path
from typing import Any

from ..prompts.completion_prompts import (
    LAYER_RULES,
    get_file_context,
    get_todo_guidelines,
    is_delegated_todo,
)

TODO_PATTERN = re.compile(r'#\s*TODO:?\s*(.+)', re.IGNORECASE)


def _determine_category(file_path: Path) -> str:
    """Determine the architecture layer category from a file path."""
    parts = file_path.parts
    if "domain" in parts:
        return "domain"
    elif "application" in parts:
        return "application"
    elif "infrastructure" in parts:
        return "infrastructure"
    return "unknown"


def _extract_todos_from_file(file_path: Path) -> list[dict[str, Any]]:
    """Extract TODO comments from a single file."""
    todos = []
    content = file_path.read_text(encoding="utf-8")

    for line_num, line in enumerate(content.split("\n"), start=1):
        match = TODO_PATTERN.search(line)
        if match:
            todos.append({
                "line_number": line_num,
                "content": match.group(1).strip(),
                "original_line": line.strip(),
            })

    return todos


def _scan_directory_todos(
    scan_path: Path,
    rel_base: Path,
    todos: list,
    category_counter: Counter,
    file_type_counter: Counter,
) -> None:
    """Scan a directory for TODO comments and append results to the provided lists."""
    if not scan_path.is_dir():
        return

    for py_file in sorted(scan_path.rglob("*.py")):
        file_todos = _extract_todos_from_file(py_file)
        if not file_todos:
            continue

        category = _determine_category(py_file)
        file_type = py_file.stem
        rel_path = py_file.relative_to(rel_base)

        for todo in file_todos:
            todo["file_path"] = str(rel_path)
            todo["category"] = category
            todo["file_type"] = file_type
            todos.append(todo)

        category_counter[category] += len(file_todos)
        file_type_counter[file_type] += len(file_todos)


def scan_module_todos(module_path: Path) -> dict[str, Any]:
    """Scan a generated module directory and src/common for all TODO comments.

    Args:
        module_path: Absolute path to the module directory (e.g. .../src/school)

    Returns:
        Dictionary with todos and summary, same shape as before.
    """
    if not module_path.is_dir():
        return {
            "success": False,
            "error": f"Module directory not found: {module_path}",
        }

    todos: list[dict[str, Any]] = []
    category_counter: Counter = Counter()
    file_type_counter: Counter = Counter()

    src_path = module_path.parent
    rel_base = src_path.parent

    _scan_directory_todos(module_path, rel_base, todos, category_counter, file_type_counter)

    common_path = src_path / "common"
    _scan_directory_todos(common_path, rel_base, todos, category_counter, file_type_counter)

    module_name = module_path.name

    return {
        "success": True,
        "module": module_name,
        "total_todos": len(todos),
        "todos": todos,
        "summary": {
            "by_category": dict(category_counter),
            "by_file_type": dict(file_type_counter),
            "total": len(todos),
        },
    }


class TodoCompleter:
    """Completes TODO comments by removing them or providing guidance."""

    def _remove_todos_from_file(
        self,
        file_path: Path,
    ) -> dict[str, Any]:
        """Remove actionable TODO comments and their trailing blank lines from a file.

        Skips TODOs delegated to define_fields or wire_module.

        Returns:
            Result dictionary with count of removed TODOs.
        """
        content = file_path.read_text(encoding="utf-8")
        lines = content.split("\n")

        all_todos = _extract_todos_from_file(file_path)
        if not all_todos:
            return {"success": True, "file_path": str(file_path), "todos_removed": 0}

        # Collect line indices to remove (0-based)
        remove_indices: set[int] = set()
        for todo in all_todos:
            if is_delegated_todo(todo["content"]):
                continue
            idx = todo["line_number"] - 1
            remove_indices.add(idx)
            # Also remove the blank line immediately after, if present
            next_idx = idx + 1
            if next_idx < len(lines) and lines[next_idx].strip() == "":
                remove_indices.add(next_idx)

        if not remove_indices:
            return {"success": True, "file_path": str(file_path), "todos_removed": 0}

        new_lines = [line for i, line in enumerate(lines) if i not in remove_indices]
        file_path.write_text("\n".join(new_lines), encoding="utf-8")

        return {
            "success": True,
            "file_path": str(file_path),
            "todos_removed": len([i for i in remove_indices if i < len(lines) and TODO_PATTERN.search(lines[i])]),
        }

    def _guidance_for_todos(
        self,
        file_path: Path,
        context: str = "",
    ) -> dict[str, Any]:
        """Return structured guidance for actionable TODOs (original behavior)."""
        content = file_path.read_text(encoding="utf-8")
        file_type = file_path.stem
        category = _determine_category(file_path)

        all_todos = _extract_todos_from_file(file_path)
        if not all_todos:
            return {"success": True, "file_path": str(file_path), "todos_found": 0}

        actionable_todos = []
        delegated_count = 0
        for todo in all_todos:
            if is_delegated_todo(todo["content"]):
                delegated_count += 1
            else:
                actionable_todos.append(todo)

        todo_contexts = get_file_context(content, actionable_todos) if actionable_todos else []
        guidelines = get_todo_guidelines(file_type)

        replacements = []
        for todo, ctx in zip(actionable_todos, todo_contexts):
            replacements.append({
                "line": todo["line_number"],
                "todo": todo["content"],
                "before": ctx["before"],
                "after": ctx["after"],
                "guideline": guidelines.get("guideline", ""),
            })

        result: dict[str, Any] = {
            "success": True,
            "file_path": str(file_path),
            "file_type": file_type,
            "category": category,
            "actionable": len(actionable_todos),
            "delegated": delegated_count,
            "replacements": replacements,
            "layer_rules": LAYER_RULES.get(category, {}),
        }
        if context:
            result["context"] = context
        return result

    async def complete_file_todos(
        self,
        file_path: Path,
        context: str = "",
        action: str = "remove",
    ) -> dict[str, Any]:
        """Complete TODOs in a file.

        Args:
            file_path: Path to the file containing TODOs
            context: Additional context about the domain
            action: "remove" to delete TODO comments, "guidance" for suggestions

        Returns:
            Result dictionary
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if action == "remove":
            return self._remove_todos_from_file(file_path)
        return self._guidance_for_todos(file_path, context)

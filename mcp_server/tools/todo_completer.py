"""Tool to intelligently complete TODO comments in generated code."""

import re
from collections import Counter
from pathlib import Path
from typing import Any

from ..prompts.completion_prompts import (
    get_domain_dto_prompt,
    get_domain_model_prompt,
    get_exceptions_mapping_prompt,
    get_router_prompt,
    get_schema_prompt,
    get_repository_prompt,
    get_use_case_prompt,
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
        Dictionary with todos and summary, same shape as the old static list.
    """
    if not module_path.is_dir():
        return {
            "success": False,
            "error": f"Module directory not found: {module_path}",
        }

    todos: list[dict[str, Any]] = []
    category_counter: Counter = Counter()
    file_type_counter: Counter = Counter()

    # src/ is the parent of the module directory
    src_path = module_path.parent
    rel_base = src_path.parent  # project root, so paths show as src/...

    # Scan the module itself
    _scan_directory_todos(module_path, rel_base, todos, category_counter, file_type_counter)

    # Scan src/common/ for wiring TODOs (router, exceptions_mapping, etc.)
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
    """Intelligently completes TODO comments while respecting hexagonal architecture."""

    def __init__(self):
        """Initialize the completer."""
        self.prompt_map = {
            # Domain layer
            "entities": get_domain_dto_prompt,
            # Application layer
            "schemas": get_schema_prompt,
            "create": get_use_case_prompt,
            "update": get_use_case_prompt,
            "list": get_use_case_prompt,
            "retrieve": get_use_case_prompt,
            "delete": get_use_case_prompt,
            # Infrastructure layer
            "models": get_domain_model_prompt,
            "database": get_repository_prompt,
            # Common wiring
            "router": get_router_prompt,
            "exceptions_mapping": get_exceptions_mapping_prompt,
        }

    async def complete_file_todos(
        self,
        file_path: Path,
        context: str = ""
    ) -> dict[str, Any]:
        """Complete TODOs in a specific file.

        Args:
            file_path: Path to the file containing TODOs
            context: Additional context about the domain

        Returns:
            Result dictionary with suggestions and metadata
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Read the file content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Determine file type
        file_type = file_path.stem
        category = _determine_category(file_path)

        # Get appropriate prompt
        prompt_func = self.prompt_map.get(file_type)
        if not prompt_func:
            return {
                "success": False,
                "error": f"No completion prompt defined for file type: {file_type}"
            }

        # Extract TODOs
        todos = _extract_todos_from_file(file_path)

        if not todos:
            return {
                "success": True,
                "file_path": str(file_path),
                "message": "No TODOs found in this file",
                "todos_found": 0
            }

        # Generate prompt for LLM
        completion_prompt = prompt_func(
            file_path=str(file_path),
            file_content=content,
            context=context,
            todos=todos
        )

        result = {
            "success": True,
            "file_path": str(file_path),
            "file_type": file_type,
            "category": category,
            "todos_found": len(todos),
            "todos": todos,
            "completion_prompt": completion_prompt,
            "instructions": (
                "Use the completion_prompt to guide the LLM in completing the TODOs. "
                "The LLM should analyze the file, understand the hexagonal architecture layer, "
                "and provide appropriate implementations that follow best practices."
            )
        }

        return result

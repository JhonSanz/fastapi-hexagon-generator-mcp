"""Tool to intelligently complete TODO comments in generated code."""

import re
from pathlib import Path
from typing import Any

from ..prompts.completion_prompts import (
    get_domain_dto_prompt,
    get_domain_model_prompt,
    get_schema_prompt,
    get_repository_prompt,
    get_use_case_prompt,
)


class TodoCompleter:
    """Intelligently completes TODO comments while respecting hexagonal architecture."""

    def __init__(self):
        """Initialize the completer."""
        self.prompt_map = {
            "dtos": get_domain_dto_prompt,
            "models": get_domain_model_prompt,
            "schemas": get_schema_prompt,
            "repository": get_repository_prompt,
            "database": get_repository_prompt,
            "web_cases": get_use_case_prompt,
            "handlers": get_use_case_prompt,
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
        category = self._determine_category(file_path)

        # Get appropriate prompt
        prompt_func = self.prompt_map.get(file_type)
        if not prompt_func:
            return {
                "success": False,
                "error": f"No completion prompt defined for file type: {file_type}"
            }

        # Extract TODOs
        todos = self._extract_todos(content)

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

    def _extract_todos(self, content: str) -> list[dict[str, Any]]:
        """Extract TODO comments from file content.

        Args:
            content: File content

        Returns:
            List of TODO dictionaries
        """
        todos = []
        todo_pattern = re.compile(r'#\s*TODO:?\s*(.+)', re.IGNORECASE)

        for line_num, line in enumerate(content.split('\n'), start=1):
            match = todo_pattern.search(line)
            if match:
                todos.append({
                    "line_number": line_num,
                    "content": match.group(1).strip(),
                    "original_line": line.strip()
                })

        return todos

    def _determine_category(self, file_path: Path) -> str:
        """Determine the architecture layer category.

        Args:
            file_path: Path to the file

        Returns:
            Category name (domain, application, infrastructure)
        """
        parts = file_path.parts
        if "domain" in parts:
            return "domain"
        elif "application" in parts:
            return "application"
        elif "infrastructure" in parts:
            return "infrastructure"
        return "unknown"

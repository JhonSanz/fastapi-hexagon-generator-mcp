"""Wire a module's router into src/common/router.py."""

from typing import Literal

from .todo import already_wired, replace_todo_block

Status = Literal["wired", "already_wired"]


def apply(content: str, snake_name: str) -> tuple[str, Status]:
    """Inject the router import + include_router call into router.py content."""
    import_line = f"from src.{snake_name}.infrastructure.web import router as {snake_name}_router"
    include_line = f"api_router.include_router({snake_name}_router)"

    if already_wired(content, [import_line, include_line]):
        return content, "already_wired"

    lines = content.split("\n")
    new_lines, found = replace_todo_block(
        lines, "Register your module routers here", [import_line, include_line]
    )
    if not found:
        new_lines.extend(["", import_line, include_line])

    return "\n".join(new_lines), "wired"

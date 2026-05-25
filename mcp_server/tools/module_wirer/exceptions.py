"""Wire a module's exception mappings into src/common/exceptions_mapping.py."""

from typing import Literal

from .todo import already_wired, find_last_import_index, replace_todo_block

Status = Literal["wired", "already_wired"]


def apply(content: str, snake_name: str, upper_name: str) -> tuple[str, Status]:
    """Inject the mapping import + ALL_EXCEPTIONS append into exceptions_mapping.py content."""
    mapping_var = f"EXCEPTIONS_{upper_name}_MAPPING"
    import_line = f"from src.{snake_name}.infrastructure.exception_handlers import {mapping_var}"
    append_line = f"ALL_EXCEPTIONS += {mapping_var}"

    if already_wired(content, [import_line, append_line]):
        return content, "already_wired"

    lines = content.split("\n")
    lines, import_found = replace_todo_block(
        lines, "Import your module exception mappings here", [import_line]
    )
    lines, append_found = replace_todo_block(
        lines, "Append your module exception mappings here", [append_line]
    )

    # Fallbacks: if either TODO was already stripped from the template, place
    # the line at the most natural spot (after imports / at end-of-file).
    if not import_found:
        lines.insert(find_last_import_index(lines), import_line)
    if not append_found:
        lines.append(append_line)

    return "\n".join(lines), "wired"

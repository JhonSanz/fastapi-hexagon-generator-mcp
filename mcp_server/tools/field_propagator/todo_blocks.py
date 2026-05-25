"""Locate and replace TODO comment blocks in generated source files."""


def find_todo_block(lines: list[str], todo_substring: str) -> tuple[int, int]:
    """Find a TODO block: the TODO line plus following comment/pass lines.

    Returns (start, end) with end exclusive. Returns (-1, -1) if not found.
    """
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("#") and "TODO" in stripped and todo_substring in stripped:
            end = i + 1
            while end < len(lines):
                next_stripped = lines[end].strip()
                if next_stripped.startswith("#"):
                    end += 1
                elif next_stripped == "pass":
                    end += 1
                    break
                else:
                    break
            return i, end
    return -1, -1


def get_indent(line: str) -> str:
    return line[: len(line) - len(line.lstrip())]


def replace_todo_block(
    content: str, todo_substring: str, replacement_lines: list[str]
) -> tuple[str, bool]:
    """Replace a TODO block with generated code. Returns (new_content, was_replaced)."""
    lines = content.split("\n")
    start, end = find_todo_block(lines, todo_substring)
    if start == -1:
        return content, False

    indent = get_indent(lines[start])
    indented = [f"{indent}{line}" if line else "" for line in replacement_lines]
    return "\n".join(lines[:start] + indented + lines[end:]), True


def apply_todo(content: str, marker: str, lines: list[str]) -> tuple[str, int]:
    """replace_todo_block variant returning a 0/1 count for easy accumulation."""
    new_content, ok = replace_todo_block(content, marker, lines)
    return new_content, 1 if ok else 0

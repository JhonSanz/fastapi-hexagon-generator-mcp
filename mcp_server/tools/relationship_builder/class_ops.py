"""Class-scoped insertion helpers: locate and modify a specific class body."""

import re


def find_class(lines: list[str], class_name: str) -> tuple[int, int]:
    """Return (start, end_exclusive) for a class definition. (-1, -1) if absent."""
    start = -1
    for i, line in enumerate(lines):
        if re.match(rf"^class\s+{re.escape(class_name)}\b", line):
            start = i
            break
    if start == -1:
        return -1, -1
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if re.match(r"^class\s+\w+", lines[j]):
            end = j
            break
    return start, end


def append_to_class_body(content: str, class_name: str, line: str) -> tuple[str, bool]:
    """Append a single line at the end of a class body.

    Drops a trailing `pass` if present and skips trailing blank-line separation
    before the next class.
    """
    lines = content.split("\n")
    start, end = find_class(lines, class_name)
    if start == -1:
        return content, False

    insert_at = end
    while insert_at > start + 1 and lines[insert_at - 1].strip() == "":
        insert_at -= 1
    if insert_at > start + 1 and lines[insert_at - 1].strip() == "pass":
        lines.pop(insert_at - 1)
        insert_at -= 1

    lines.insert(insert_at, f"    {line}")
    return "\n".join(lines), True


def insert_before_first_default(content: str, class_name: str, line: str) -> tuple[str, bool]:
    """Insert a line in a class body before the first field that has a default value.

    Keeps required (non-default) fields above defaulted ones in dataclasses,
    avoiding `TypeError: non-default argument follows default argument`.
    Falls back to appending at the end if no defaulted field exists.
    """
    lines = content.split("\n")
    start, end = find_class(lines, class_name)
    if start == -1:
        return content, False

    for i in range(start + 1, end):
        stripped = lines[i].strip()
        if not stripped or stripped.startswith(('"""', "'''", "#")):
            continue
        if " = " in stripped:
            indent = lines[i][: len(lines[i]) - len(lines[i].lstrip())]
            lines.insert(i, f"{indent}{line}")
            return "\n".join(lines), True

    return append_to_class_body(content, class_name, line)


def insert_before_model_config(content: str, class_name: str, line: str) -> tuple[str, bool]:
    """Insert a line inside a class, right before its `model_config = ConfigDict(...)`."""
    lines = content.split("\n")
    start, end = find_class(lines, class_name)
    if start == -1:
        return content, False
    for i in range(start + 1, end):
        if "model_config = ConfigDict" in lines[i]:
            j = i
            while j > start + 1 and lines[j - 1].strip() == "":
                j -= 1
            lines.insert(j, f"    {line}")
            return "\n".join(lines), True
    return content, False


def insert_in_example(content: str, class_name: str, example_entry: str) -> tuple[str, bool]:
    """Insert an entry (e.g. `"store_id": 1,`) into a class's `"example": {...}` dict.

    Adds a trailing comma to the previous entry if missing.
    """
    lines = content.split("\n")
    start, end = find_class(lines, class_name)
    if start == -1:
        return content, False

    example_start = -1
    for i in range(start + 1, end):
        if '"example":' in lines[i] and "{" in lines[i]:
            example_start = i
            break
    if example_start == -1:
        return content, False

    depth = lines[example_start].count("{") - lines[example_start].count("}")
    close_idx = -1
    for i in range(example_start + 1, end):
        depth += lines[i].count("{") - lines[i].count("}")
        if depth <= 0:
            close_idx = i
            break
    if close_idx == -1:
        return content, False

    j = close_idx - 1
    while j > example_start and lines[j].strip() == "":
        j -= 1
    if j > example_start and lines[j].strip() and not lines[j].rstrip().endswith(","):
        lines[j] = lines[j].rstrip() + ","

    indent = "                "
    for k in range(example_start + 1, close_idx):
        if lines[k].strip().startswith('"'):
            ws = lines[k][: len(lines[k]) - len(lines[k].lstrip())]
            if ws:
                indent = ws
                break

    lines.insert(close_idx, f"{indent}{example_entry}")
    return "\n".join(lines), True

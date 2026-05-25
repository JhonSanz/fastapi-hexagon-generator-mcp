"""Content-level insertion helpers: line splicing and import merging."""

import re


def insert_before(content: str, marker: str, new_lines: list[str]) -> tuple[str, bool]:
    """Insert lines before the first line containing `marker`, matching its indent."""
    lines = content.split("\n")
    for i, line in enumerate(lines):
        if marker in line:
            indent = line[: len(line) - len(line.lstrip())]
            indented = [f"{indent}{ln}" for ln in new_lines]
            return "\n".join(lines[:i] + indented + lines[i:]), True
    return content, False


def insert_after(content: str, marker: str, new_lines: list[str]) -> tuple[str, bool]:
    """Insert lines after the **last** statement containing `marker`.

    Handles multi-line statements by tracking parenthesis depth: if the matched
    line has an unclosed `(`, scanning continues until parentheses are balanced.
    """
    lines = content.split("\n")
    last = -1
    for i, line in enumerate(lines):
        if marker in line:
            last = i
    if last == -1:
        return content, False

    end = last
    depth = 0
    for i in range(last, len(lines)):
        depth += lines[i].count("(") - lines[i].count(")")
        end = i
        if depth <= 0:
            break

    indent = lines[last][: len(lines[last]) - len(lines[last].lstrip())]
    indented = [f"{indent}{ln}" if ln.strip() else "" for ln in new_lines]
    return "\n".join(lines[: end + 1] + indented + lines[end + 1 :]), True


def add_to_import(content: str, module: str, *names: str) -> str:
    """Add names to an existing `from {module} import ...` line.

    No-op if the module isn't imported, or if all names are already imported.
    """
    pattern = rf"^from {re.escape(module)} import (.+)$"
    match = re.search(pattern, content, re.MULTILINE)
    if not match:
        return content
    existing = {t.strip() for t in match.group(1).split(",")}
    if set(names).issubset(existing):
        return content
    merged = sorted(existing | set(names))
    return (
        content[: match.start()]
        + f"from {module} import {', '.join(merged)}"
        + content[match.end() :]
    )

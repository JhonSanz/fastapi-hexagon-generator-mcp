"""Shared helpers for TODO replacement and import-position discovery."""


def replace_todo_block(
    lines: list[str], marker: str, replacement: list[str]
) -> tuple[list[str], bool]:
    """Replace the first matching TODO comment block with `replacement`.

    Returns (new_lines, was_found). When found, drops the TODO line and any
    immediately following `#` comment lines, then splices in `replacement`.
    """
    new_lines: list[str] = []
    found = False
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if not found and "TODO" in stripped and marker in stripped:
            found = True
            i += 1
            while i < len(lines) and lines[i].strip().startswith("#"):
                i += 1
            new_lines.extend(replacement)
            continue
        new_lines.append(lines[i])
        i += 1
    return new_lines, found


def find_last_import_index(lines: list[str]) -> int:
    """Index *after* the last top-level import. Prefers `from src.` lines."""
    insert_idx = 0
    for idx, line in enumerate(lines):
        if line.strip().startswith("from src."):
            insert_idx = idx + 1
    if insert_idx == 0:
        for idx, line in enumerate(lines):
            s = line.strip()
            if s.startswith("from ") or s.startswith("import "):
                insert_idx = idx + 1
    return insert_idx


def already_wired(content: str, sentinel_lines: list[str]) -> bool:
    """True if any of `sentinel_lines` appears as a non-commented line in `content`."""
    sentinels = set(sentinel_lines)
    return any(line.strip() in sentinels for line in content.split("\n"))

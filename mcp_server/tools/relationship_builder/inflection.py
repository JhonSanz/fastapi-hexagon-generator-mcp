"""English noun pluralization for relationship attribute names."""


def pluralize(name: str) -> str:
    if name.endswith(("s", "x", "z")) or name.endswith("sh") or name.endswith("ch"):
        return name + "es"
    if name.endswith("y") and len(name) > 1 and name[-2] not in "aeiou":
        return name[:-1] + "ies"
    return name + "s"

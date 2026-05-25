"""Field definition and SQLAlchemy type mapping."""

from dataclasses import dataclass
from typing import Optional


RESERVED_NAMES = {"id", "created_at", "updated_at"}

SQLALCHEMY_TYPE_MAP: dict[str, tuple[str, str]] = {
    "str": ("String", "String"),
    "int": ("Integer", "Integer"),
    "float": ("Float", "Float"),
    "bool": ("Boolean", "Boolean"),
    "datetime": ("DateTime(timezone=True)", "DateTime"),
    "date": ("Date", "Date"),
    "Decimal": ("Numeric", "Numeric"),
}

KNOWN_TYPES = frozenset(SQLALCHEMY_TYPE_MAP)


@dataclass
class FieldDefinition:
    """Validated field specification."""

    name: str
    type: str
    max_length: Optional[int] = None
    min_length: Optional[int] = None
    nullable: bool = False
    description: Optional[str] = None
    searchable: bool = False
    gt: Optional[float] = None
    ge: Optional[float] = None
    lt: Optional[float] = None
    le: Optional[float] = None

    def __post_init__(self) -> None:
        if self.name in RESERVED_NAMES:
            raise ValueError(f"Field name '{self.name}' is reserved (used by base template)")

    @property
    def is_known_type(self) -> bool:
        return self.type in KNOWN_TYPES

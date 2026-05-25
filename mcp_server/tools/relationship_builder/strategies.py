"""Per-relation-type orchestration: invoke the atomic layer ops in the right order.

Each function takes the parent RelationshipBuilder as `b` and uses its file-I/O
helpers (`b.apply_op`, `b.src`, `b.record`) plus pre-resolved naming attributes
(`b.source_snake`, `b.target_pascal`, `b.nullable`, ...).
"""

from . import entity, mapper, orm, schemas
from .association_table import ensure_association_table
from .inflection import pluralize


def one_to_many(b) -> None:
    """Source has many targets. FK lives on the target side."""
    plural_target = pluralize(b.target_snake)
    fk_name = f"{b.source_snake}_id"

    target_models = b.src(b.target_snake, "infrastructure", "models.py")
    source_models = b.src(b.source_snake, "infrastructure", "models.py")

    b.apply_op(target_models, lambda c: orm.add_fk_column(c, b.source_snake, nullable=b.nullable))
    b.apply_op(target_models, lambda c: orm.add_relationship(
        c, b.source_snake, f"{b.source_pascal}ORM",
        back_populates=plural_target, is_list=False,
    ))
    b.apply_op(source_models, lambda c: orm.add_relationship(
        c, plural_target, f"{b.target_pascal}ORM",
        back_populates=b.source_snake, is_list=True,
    ))

    _wire_fk_on_target(b, fk_name)


def one_to_one(b) -> None:
    """Source has one target. FK + unique constraint on the target side."""
    fk_name = f"{b.source_snake}_id"

    target_models = b.src(b.target_snake, "infrastructure", "models.py")
    source_models = b.src(b.source_snake, "infrastructure", "models.py")

    b.apply_op(target_models, lambda c: orm.add_fk_column(c, b.source_snake, nullable=b.nullable, unique=True))
    b.apply_op(target_models, lambda c: orm.add_relationship(
        c, b.source_snake, f"{b.source_pascal}ORM",
        back_populates=b.target_snake, is_list=False,
    ))
    b.apply_op(source_models, lambda c: orm.add_relationship(
        c, b.target_snake, f"{b.target_pascal}ORM",
        back_populates=b.source_snake, is_list=False, uselist=False,
    ))

    _wire_fk_on_target(b, fk_name)


def many_to_many(b) -> None:
    """Both sides have many. Creates an association table."""
    plural_target = pluralize(b.target_snake)
    plural_source = pluralize(b.source_snake)
    assoc_name = f"{b.source_snake}_{b.target_snake}"
    assoc_path = b.project_path / "src" / "common" / "association_tables.py"

    modified, desc = ensure_association_table(assoc_path, assoc_name, b.source_snake, b.target_snake)
    b.record(str(assoc_path), modified, desc)

    b.apply_op(
        b.src(b.source_snake, "infrastructure", "models.py"),
        lambda c: orm.add_relationship(
            c, plural_target, f"{b.target_pascal}ORM",
            back_populates=plural_source, is_list=True, secondary=assoc_name,
        ),
    )
    b.apply_op(
        b.src(b.target_snake, "infrastructure", "models.py"),
        lambda c: orm.add_relationship(
            c, plural_source, f"{b.source_pascal}ORM",
            back_populates=plural_target, is_list=True, secondary=assoc_name,
        ),
    )


def _wire_fk_on_target(b, fk_name: str) -> None:
    """Common tail used by one_to_many and one_to_one: propagate the FK to the
    target's entity, mapper, and schemas."""
    b.apply_op(
        b.src(b.target_snake, "domain", "entities.py"),
        lambda c: entity.add_fk_to_entity(c, b.target_pascal, fk_name, b.nullable),
    )
    b.apply_op(
        b.src(b.target_snake, "infrastructure", "database.py"),
        lambda c: mapper.add_fk_to_mapper(c, fk_name),
    )
    b.apply_op(
        b.src(b.target_snake, "application", "schemas.py"),
        lambda c: schemas.add_fk_to_schemas(c, b.target_pascal, fk_name, b.nullable),
    )


STRATEGIES = {
    "one_to_many": one_to_many,
    "one_to_one": one_to_one,
    "many_to_many": many_to_many,
}

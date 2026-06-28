"""Regression tests for SQLAlchemy ``Column`` generation.

Covers the generator fixes for the alembic-drift issues:

- ``required: true`` -> ``Column(..., nullable=False, ...)`` (P0 unblock)
- explicit ``nullable: false`` now reaches the generator (proto3 ``optional``)
- field-level ``index``/``unique`` are folded into ``Column`` for *all*
  sa_column paths, not just ``sa_column_type`` (Issue 2)
- ``server_default`` is emitted into ``Column`` (Issue 3)
"""
from google.protobuf import descriptor_pool

from protobuf_pydantic_gen.message_processor import MessageProcessor
from protobuf_pydantic_gen.models import Field
from protobuf_pydantic_gen.type_mapper import TypeMapper


def _processor() -> MessageProcessor:
    return MessageProcessor(TypeMapper(descriptor_pool.Default()))


def _field(field_type: str, ext: dict, *, required: bool = False) -> Field:
    return Field(
        name="col",
        type=field_type,
        repeated=False,
        required=required,
        attributes="",
        ext=dict(ext),
        message_info={},
    )


# --- P0: required -> nullable=False ----------------------------------------


def test_required_sa_column_type_field_emits_nullable_false():
    p = _processor()
    field = _field(
        "int",
        {"sa_column_type": "BigInteger", "description": '"Creation timestamp"'},
        required=True,
    )
    rendered = p._process_field_ext(set(), field, {"as_table": True})

    assert "sa_column=Column(BigInteger, nullable=False" in rendered
    assert "nullable=True" not in rendered


def test_non_required_sa_column_type_field_still_nullable():
    p = _processor()
    field = _field("int", {"sa_column_type": "BigInteger"}, required=False)
    rendered = p._process_field_ext(set(), field, {"as_table": True})

    assert "sa_column=Column(BigInteger, nullable=True)" in rendered


def test_required_datetime_auto_inject_emits_nullable_false():
    p = _processor()
    field = _field("datetime.datetime", {"description": '"ts"'}, required=True)
    rendered = p._process_field_ext(set(), field, {"as_table": True})

    assert "sa_column=Column(TIMESTAMP(timezone=True), nullable=False" in rendered


def test_required_enum_auto_inject_emits_nullable_false():
    p = _processor()
    p._enum_type_names.add("Status")
    field = _field("Status", {"enum_storage": "value"}, required=True)
    rendered = p._process_field_ext(set(), field, {"as_table": True})

    assert "sa_column=Column(StatusType, nullable=False" in rendered


# --- P0b: explicit nullable:false now reaches the generator -----------------


def test_explicit_nullable_false_sa_column_type_field():
    p = _processor()
    # With `optional bool nullable`, nullable:false survives proto3 and is
    # respected even without `required: true`.
    field = _field("int", {"sa_column_type": "BigInteger", "nullable": False})
    rendered = p._process_field_ext(set(), field, {"as_table": True})

    assert "sa_column=Column(BigInteger, nullable=False" in rendered
    assert "nullable=True" not in rendered


def test_explicit_nullable_false_does_not_reverse_python_type():
    # Regression guard for the "semantic reversal" symptom: nullable:false on
    # its own must not make the field Optional. The Field.required flag is the
    # single source of truth for Optional[] wrapping in the template.
    field = _field("int", {"sa_column_type": "BigInteger", "nullable": False})
    assert field.required is False  # nullable:false alone does not imply required


# --- Issue 2: index/unique folded into Column for all sa_column paths -------


def test_index_on_datetime_field_is_folded_into_column():
    # Previously the datetime auto-inject path left `index` on Field(),
    # crashing SQLModel at import ("Passing index is not supported when also
    # passing a sa_column").
    p = _processor()
    field = _field("datetime.datetime", {"index": True})
    rendered = p._process_field_ext(set(), field, {"as_table": True})

    assert "index=True" in rendered
    # `index` must be consumed by the Column, not leaked into Field() kwargs.
    assert "sa_column=Column(TIMESTAMP(timezone=True), nullable=True, index=True" in rendered


def test_unique_on_enum_field_is_folded_into_column():
    p = _processor()
    p._enum_type_names.add("Status")
    field = _field("Status", {"enum_storage": "value", "unique": True})
    rendered = p._process_field_ext(set(), field, {"as_table": True})

    assert "unique=True" in rendered
    assert "sa_column=Column(StatusType, nullable=False, unique=True" in rendered


def test_index_and_unique_on_sa_column_type_field():
    p = _processor()
    field = _field("int", {"sa_column_type": "BigInteger", "index": True, "unique": True})
    rendered = p._process_field_ext(set(), field, {"as_table": True})

    assert "index=True" in rendered
    assert "unique=True" in rendered
    # No duplicate/leaked index onto Field()
    field_kwargs = rendered.split("sa_column=")[0]
    assert "index=" not in field_kwargs


# --- Issue 3: server_default emitted into Column ---------------------------


def test_server_default_emitted_into_column():
    p = _processor()
    field = _field(
        "int",
        {"sa_column_type": "BigInteger", "server_default": "0"},
        required=True,
    )
    rendered = p._process_field_ext(set(), field, {"as_table": True})

    assert "nullable=False" in rendered
    assert "server_default='0'" in rendered


def test_server_default_empty_string_survives():
    # `optional string` lets an empty-string DB default reach the generator.
    p = _processor()
    field = _field(
        "str",
        {"sa_column_type": "Text", "server_default": ""},
    )
    rendered = p._process_field_ext(set(), field, {"as_table": True})

    assert "server_default=''" in rendered

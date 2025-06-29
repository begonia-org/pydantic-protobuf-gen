from google.protobuf import descriptor_pool

from protobuf_pydantic_gen.message_processor import MessageProcessor
from protobuf_pydantic_gen.models import Field
from protobuf_pydantic_gen.type_mapper import TypeMapper


def _build_processor() -> MessageProcessor:
    return MessageProcessor(TypeMapper(descriptor_pool.Default()))


def _build_field(field_type: str, ext: dict) -> Field:
    return Field(
        name="updated_at",
        type=field_type,
        repeated=False,
        required=False,
        attributes="",
        ext=ext,
        message_info={},
    )


def test_message_processor_adds_onupdate_for_implicit_datetime_columns():
    processor = _build_processor()
    imports = set()
    field = _build_field(
        "datetime.datetime",
        {
            "description": '"更新时间"',
            "label": '"更新时间"',
            "sa_auto_update": True,
        },
    )

    rendered = processor._process_field_ext(imports, field, {"as_table": True})

    assert "sa_column=Column(TIMESTAMP(timezone=True), nullable=True, doc='更新时间', onupdate=datetime.datetime.utcnow)" in rendered
    assert "sa_auto_update" not in rendered
    assert 'schema_extra={\'label\': \'更新时间\'}' in rendered
    assert "from sqlalchemy import TIMESTAMP" in imports
    assert "from sqlmodel import Column" in imports


def test_message_processor_adds_onupdate_for_explicit_sa_column_type():
    processor = _build_processor()
    imports = set()
    field = _build_field(
        "datetime.datetime",
        {
            "description": '"更新时间"',
            "sa_column_type": "TIMESTAMP(timezone=True)",
            "nullable": True,
            "sa_auto_update": True,
        },
    )

    rendered = processor._process_field_ext(imports, field, {"as_table": True})

    assert 'sa_column=Column(TIMESTAMP(timezone=True), nullable=True, onupdate=datetime.datetime.utcnow, doc="更新时间")' in rendered
    assert "sa_auto_update" not in rendered
    assert any(import_stmt.endswith(" import TIMESTAMP") for import_stmt in imports)
    assert "from sqlmodel import Column" in imports


def test_message_processor_normalizes_default_factory_zero_arg_calls_to_references():
    processor = _build_processor()
    field = _build_field(
        "datetime.datetime",
        {"default_factory": "datetime.datetime.utcnow()"},
    )

    rendered = processor._process_field_ext(set(), field, {"as_table": True})

    assert "default_factory=datetime.datetime.utcnow" in rendered


def test_message_processor_wraps_default_factory_calls_with_args_in_lambda():
    processor = _build_processor()
    field = _build_field(
        "datetime.datetime",
        {"default_factory": "datetime.datetime.now(datetime.timezone.utc)"},
    )

    rendered = processor._process_field_ext(set(), field, {"as_table": True})

    assert "default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)" in rendered

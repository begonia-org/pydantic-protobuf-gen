from enum import Enum

from google.protobuf import descriptor_pool

from protobuf_pydantic_gen.ext import GenericEnumType
from protobuf_pydantic_gen.generator import CodeGenerator
from protobuf_pydantic_gen.message_processor import MessageProcessor
from protobuf_pydantic_gen.models import Field, Message
from protobuf_pydantic_gen.type_mapper import TypeMapper


class NumericStatus(Enum):
    PENDING = 1
    DONE = 2


class StringStatus(Enum):
    ACTIVE = "active"
    PAUSED = "paused"


def test_generic_enum_type_supports_name_storage_with_legacy_value_reads():
    enum_type = GenericEnumType(
        NumericStatus,
        storage_mode="name",
        read_modes=("name", "value"),
    )

    assert enum_type.process_bind_param(NumericStatus.PENDING, None) == "PENDING"
    assert enum_type.process_bind_param("DONE", None) == "DONE"
    assert enum_type.process_result_value("PENDING", None) == NumericStatus.PENDING
    assert enum_type.process_result_value("2", None) == NumericStatus.DONE


def test_generic_enum_type_supports_string_values_in_value_mode():
    enum_type = GenericEnumType(
        StringStatus,
        storage_mode="value",
        read_modes=("value", "name"),
    )

    assert enum_type.process_bind_param(StringStatus.ACTIVE, None) == "active"
    assert enum_type.process_result_value("active", None) == StringStatus.ACTIVE
    assert enum_type.process_result_value("PAUSED", None) == StringStatus.PAUSED


def test_message_processor_uses_name_type_for_name_storage_columns():
    processor = MessageProcessor(TypeMapper(descriptor_pool.Default()))
    processor._enum_type_names.add("WorkflowStatus")
    field = Field(
        name="status",
        type="WorkflowStatus",
        repeated=False,
        required=False,
        attributes="",
        ext={
            "enum_storage": "name",
            "nullable": True,
            "description": '"Workflow status"',
        },
        message_info={"message": "demo.WorkflowStatus", "file": "workflow", "package": "demo"},
    )

    rendered = processor._process_field_ext(set(), field, {"as_table": True})

    assert "sa_column=Column(WorkflowStatusNameType, nullable=True, doc='Workflow status')" in rendered
    assert "enum_storage" not in rendered


def test_generator_imports_name_type_for_external_enums():
    generator = CodeGenerator()
    generator.message_processor._enum_type_names.add("WorkflowStatus")
    imports = set()
    message = Message(
        message_name="Job",
        fields=[
            Field(
                name="status",
                type="WorkflowStatus",
                repeated=False,
                required=False,
                attributes="",
                ext={},
                message_info={
                    "message": "demo.WorkflowStatus",
                    "file": "workflow",
                    "package": "demo",
                },
            )
        ],
        proto_full_name="demo.Job",
    )

    generator._add_conditional_imports("job", [message], imports, "demo")

    assert "from .workflow_model import WorkflowStatus, WorkflowStatusType, WorkflowStatusNameType" in imports
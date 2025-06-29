from google.protobuf import descriptor_pb2, descriptor_pool

from protobuf_pydantic_gen.type_mapper import TypeMapper


def _build_field_descriptor(name: str, field_type: int, *, type_name: str = ""):
    field = descriptor_pb2.FieldDescriptorProto()
    field.name = name
    field.number = 1
    setattr(field, "label", descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED)
    setattr(field, "type", field_type)
    if type_name:
        field.type_name = type_name
    return field


def test_set_default_value_uses_empty_list_for_repeated_int_fields():
    mapper = TypeMapper(descriptor_pool.Default())
    field = _build_field_descriptor(
        "scores", descriptor_pb2.FieldDescriptorProto.TYPE_INT32
    )

    ext = mapper.set_default_value("int", {}, field)

    assert ext["default"] == []


def test_set_default_value_uses_empty_list_for_repeated_string_fields_without_explicit_default():
    mapper = TypeMapper(descriptor_pool.Default())
    field = _build_field_descriptor(
        "tags", descriptor_pb2.FieldDescriptorProto.TYPE_STRING
    )

    ext = mapper.set_default_value("str", {}, field)

    assert ext["default"] == []


def test_set_default_value_uses_empty_list_for_repeated_message_fields():
    mapper = TypeMapper(descriptor_pool.Default())
    field = _build_field_descriptor(
        "items",
        descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE,
        type_name=".pydantic_example.Example2",
    )

    ext = mapper.set_default_value("Example2", {}, field)

    assert ext["default"] == []

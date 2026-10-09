"""Prototype: drive the generator in-process (no protoc) for the probe schema."""
from google.protobuf import descriptor_pb2
from google.protobuf.compiler import plugin_pb2

from protobuf_pydantic_gen.config import get_config
from protobuf_pydantic_gen.generator import CodeGenerator

LABEL_OPTIONAL = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
LABEL_REPEATED = descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED
TYPE_STRING = descriptor_pb2.FieldDescriptorProto.TYPE_STRING
TYPE_MESSAGE = descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE
TYPE_ENUM = descriptor_pb2.FieldDescriptorProto.TYPE_ENUM
TYPE_DOUBLE = descriptor_pb2.FieldDescriptorProto.TYPE_DOUBLE


def build_file_proto() -> descriptor_pb2.FileDescriptorProto:
    file_proto = descriptor_pb2.FileDescriptorProto()
    file_proto.name = "probe_inproc.proto"
    file_proto.package = "probe.inproc"
    file_proto.syntax = "proto3"

    enum = file_proto.enum_type.add()
    enum.name = "Level"
    enum.value.add(name="LEVEL_UNSPECIFIED", number=0)

    inner = file_proto.message_type.add()
    inner.name = "Inner"
    outcome = inner.field.add()
    outcome.name, outcome.number, outcome.label, outcome.type = (
        "outcome",
        1,
        LABEL_OPTIONAL,
        TYPE_STRING,
    )

    holder = file_proto.message_type.add()
    holder.name = "Holder"
    for name, number, value_type, value_type_name in (
        ("inners", 1, TYPE_MESSAGE, ".probe.inproc.Inner"),
        ("levels", 2, TYPE_ENUM, ".probe.inproc.Level"),
        ("tags", 3, TYPE_STRING, ""),
    ):
        entry = holder.nested_type.add()
        entry.name = name.capitalize() + "Entry"
        entry.options.map_entry = True
        key = entry.field.add()
        key.name, key.number, key.label, key.type = "key", 1, LABEL_OPTIONAL, TYPE_STRING
        value = entry.field.add()
        value.name, value.number, value.label, value.type = (
            "value",
            2,
            LABEL_OPTIONAL,
            value_type,
        )
        if value_type_name:
            value.type_name = value_type_name
        map_field = holder.field.add()
        map_field.name = name
        map_field.number = number
        map_field.label = LABEL_REPEATED
        map_field.type = TYPE_MESSAGE
        map_field.type_name = f".probe.inproc.Holder.{entry.name}"

    # proto3 `optional` is encoded as a synthetic oneof holding exactly this field
    # (see descriptor.proto: each proto3 optional field gets its own synthetic oneof).
    synthetic = holder.oneof_decl.add()
    synthetic.name = "_opt_score"
    opt = holder.field.add()
    opt.name, opt.number, opt.label, opt.type = "opt_score", 4, LABEL_OPTIONAL, TYPE_DOUBLE
    opt.oneof_index = 0
    opt.proto3_optional = True
    plain = holder.field.add()
    plain.name, plain.number, plain.label, plain.type = (
        "plain_score",
        5,
        LABEL_OPTIONAL,
        TYPE_DOUBLE,
    )
    return file_proto


request = plugin_pb2.CodeGeneratorRequest()
request.file_to_generate.append("probe_inproc.proto")
request.proto_file.append(build_file_proto())
request.parameter = "package_name=probe_inproc"

response = plugin_pb2.CodeGeneratorResponse()
CodeGenerator(get_config()).generate_code(request, response)

print(f"error={response.error!r}")
for generated in response.file:
    print(f"### {generated.name}")
    print(generated.content)

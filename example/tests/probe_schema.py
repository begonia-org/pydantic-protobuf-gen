"""Shared in-process probe schema for the generator/runtime regression tests.

Drives `CodeGenerator` directly with a hand-built `FileDescriptorProto`, so the
tests need neither protoc nor a checked-in generated module.
"""
import sys
import types

from google.protobuf import any_pb2, descriptor_pb2, descriptor_pool, message_factory
from google.protobuf.compiler import plugin_pb2

from protobuf_pydantic_gen.config import get_config
from protobuf_pydantic_gen.generator import CodeGenerator

LABEL_OPTIONAL = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
LABEL_REPEATED = descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED
TYPE_STRING = descriptor_pb2.FieldDescriptorProto.TYPE_STRING
TYPE_DOUBLE = descriptor_pb2.FieldDescriptorProto.TYPE_DOUBLE
TYPE_INT32 = descriptor_pb2.FieldDescriptorProto.TYPE_INT32
TYPE_BYTES = descriptor_pb2.FieldDescriptorProto.TYPE_BYTES
TYPE_MESSAGE = descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE
TYPE_ENUM = descriptor_pb2.FieldDescriptorProto.TYPE_ENUM

PROBE_FILE = "probe_schema_test.proto"
PROBE_PACKAGE = "probe.schema"
ANY_FILE = "google/protobuf/any.proto"
MODEL_FILE = "probe_schema_test_model.py"
MODEL_MODULE_NAME = "probe_schema_test_model"
HOLDER_FULL_NAME = f"{PROBE_PACKAGE}.Holder"


def _add_field(
    message: descriptor_pb2.DescriptorProto,
    name: str,
    number: int,
    field_type: int,
    *,
    label: int = LABEL_OPTIONAL,
    type_name: str = "",
) -> descriptor_pb2.FieldDescriptorProto:
    field = message.field.add()
    field.name = name
    field.number = number
    field.label = label
    field.type = field_type
    if type_name:
        field.type_name = type_name
    return field


def build_file_proto() -> descriptor_pb2.FileDescriptorProto:
    """proto3 file covering every map value kind, bytes, and proto3 `optional`."""
    file_proto = descriptor_pb2.FileDescriptorProto()
    file_proto.name = PROBE_FILE
    file_proto.package = PROBE_PACKAGE
    file_proto.syntax = "proto3"
    file_proto.dependency.append(ANY_FILE)

    level = file_proto.enum_type.add()
    level.name = "Level"
    level.value.add(name="LEVEL_UNSPECIFIED", number=0)

    inner = file_proto.message_type.add()
    inner.name = "Inner"
    _add_field(inner, "outcome", 1, TYPE_STRING)

    holder = file_proto.message_type.add()
    holder.name = "Holder"

    for name, number, value_type, value_type_name in (
        ("inners", 1, TYPE_MESSAGE, f".{PROBE_PACKAGE}.Inner"),
        ("levels", 2, TYPE_ENUM, f".{PROBE_PACKAGE}.Level"),
        ("tags", 3, TYPE_STRING, ""),
        ("anys", 4, TYPE_MESSAGE, ".google.protobuf.Any"),
        ("counts", 5, TYPE_INT32, ""),
        ("blobs", 6, TYPE_BYTES, ""),
    ):
        entry = holder.nested_type.add()
        entry.name = f"{name[0].upper()}{name[1:]}Entry"
        entry.options.map_entry = True
        _add_field(entry, "key", 1, TYPE_STRING)
        _add_field(entry, "value", 2, value_type, type_name=value_type_name)
        _add_field(
            holder,
            name,
            number,
            TYPE_MESSAGE,
            label=LABEL_REPEATED,
            type_name=f".{PROBE_PACKAGE}.Holder.{entry.name}",
        )

    # proto3 `optional` is encoded as a synthetic oneof holding exactly that field.
    synthetic = holder.oneof_decl.add()
    synthetic.name = "_opt_score"
    opt_score = _add_field(holder, "opt_score", 7, TYPE_DOUBLE)
    opt_score.oneof_index = 0
    opt_score.proto3_optional = True

    _add_field(holder, "plain_score", 8, TYPE_DOUBLE)
    _add_field(holder, "payload", 9, TYPE_BYTES)
    _add_field(holder, "note", 10, TYPE_STRING)

    return file_proto


def any_file_proto() -> descriptor_pb2.FileDescriptorProto:
    file_proto = descriptor_pb2.FileDescriptorProto()
    file_proto.ParseFromString(any_pb2.DESCRIPTOR.serialized_pb)
    return file_proto


def pool_with_probe() -> descriptor_pool.DescriptorPool:
    """Fresh pool holding the probe file (nothing is registered globally)."""
    pool = descriptor_pool.DescriptorPool()
    pool.AddSerializedFile(any_pb2.DESCRIPTOR.serialized_pb)
    pool.Add(build_file_proto())
    return pool


def runtime_holder():
    """Runtime `Holder` descriptor from a fresh pool."""
    return pool_with_probe().FindMessageTypeByName(HOLDER_FULL_NAME)


def generate_model_source() -> str:
    """Run the generator in-process and return the generated model module source."""
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append(PROBE_FILE)
    # protoc always ships transitive dependencies in `proto_file`; the generator's
    # pool cannot resolve `.google.protobuf.Any` otherwise.
    request.proto_file.append(any_file_proto())
    request.proto_file.append(build_file_proto())
    request.parameter = "package_name=probe_schema_test"

    response = plugin_pb2.CodeGeneratorResponse()
    CodeGenerator(get_config()).generate_code(request, response)

    assert not response.error, response.error
    sources = {generated.name: generated.content for generated in response.file}
    assert MODEL_FILE in sources, sorted(sources)
    return sources[MODEL_FILE]


def _load_generated_module(
    source: str, module_name: str, file_proto
) -> types.ModuleType:
    """Import generated source as a module (default pool + `sys.modules` registered)."""
    # The generated model resolves its proto types through the default pool, exactly
    # like a generated `*_pb2` module would have registered them.
    try:
        descriptor_pool.Default().AddSerializedFile(file_proto.SerializeToString())
    except Exception:  # noqa: BLE001 - already registered by an earlier test in the session
        pass

    module = types.ModuleType(module_name)
    module.__dict__["__name__"] = module.__name__
    # `get_type_hints()` resolves annotations through `sys.modules[cls.__module__]`,
    # so the generated module must be registered like a real import would.
    sys.modules[module.__name__] = module
    exec(compile(source, f"<{module_name}>", "exec"), module.__dict__)
    return module


def load_generated_model(source: str = None) -> types.ModuleType:
    """The map / bytes / presence probe model module."""
    return _load_generated_module(
        generate_model_source() if source is None else source,
        MODEL_MODULE_NAME,
        build_file_proto(),
    )


def holder_message():
    """An empty runtime `Holder` message (the class a generated `*_pb2` would expose)."""
    descriptor_pool.Default().AddSerializedFile(build_file_proto().SerializeToString())
    holder_cls = message_factory.GetMessageClass(
        descriptor_pool.Default().FindMessageTypeByName(HOLDER_FULL_NAME)
    )
    return holder_cls()


# --------------------------------------------------------------------------- #
# oneof probe
# --------------------------------------------------------------------------- #

ONEOF_FILE = "probe_oneof_test.proto"
ONEOF_PACKAGE = "probe.oneof"
ONEOF_MODEL_FILE = "probe_oneof_test_model.py"
ONEOF_MODEL_MODULE_NAME = "probe_oneof_test_model"
UNION_FULL_NAME = f"{ONEOF_PACKAGE}.Union"


def build_oneof_file_proto() -> descriptor_pb2.FileDescriptorProto:
    """proto3 file whose oneof mixes two scalars and a message."""
    file_proto = descriptor_pb2.FileDescriptorProto()
    file_proto.name = ONEOF_FILE
    file_proto.package = ONEOF_PACKAGE
    file_proto.syntax = "proto3"

    inner = file_proto.message_type.add()
    inner.name = "Inner"
    _add_field(inner, "outcome", 1, TYPE_STRING)

    union = file_proto.message_type.add()
    union.name = "Union"
    _add_field(union, "metric", 1, TYPE_STRING)

    oneof = union.oneof_decl.add()
    oneof.name = "value"
    for name, number, field_type, type_name in (
        ("numeric_value", 2, TYPE_DOUBLE, ""),
        ("text_value", 3, TYPE_STRING, ""),
        ("inner", 4, TYPE_MESSAGE, f".{ONEOF_PACKAGE}.Inner"),
    ):
        member = _add_field(union, name, number, field_type, type_name=type_name)
        member.oneof_index = 0

    return file_proto


def generate_oneof_model_source() -> str:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append(ONEOF_FILE)
    request.proto_file.append(build_oneof_file_proto())
    request.parameter = "package_name=probe_oneof_test"

    response = plugin_pb2.CodeGeneratorResponse()
    CodeGenerator(get_config()).generate_code(request, response)

    assert not response.error, response.error
    sources = {generated.name: generated.content for generated in response.file}
    assert ONEOF_MODEL_FILE in sources, sorted(sources)
    return sources[ONEOF_MODEL_FILE]


def load_oneof_model(source: str = None) -> types.ModuleType:
    """The oneof probe model module."""
    return _load_generated_module(
        generate_oneof_model_source() if source is None else source,
        ONEOF_MODEL_MODULE_NAME,
        build_oneof_file_proto(),
    )


def union_message():
    """An empty runtime `Union` message."""
    descriptor_pool.Default().AddSerializedFile(
        build_oneof_file_proto().SerializeToString()
    )
    union_cls = message_factory.GetMessageClass(
        descriptor_pool.Default().FindMessageTypeByName(UNION_FULL_NAME)
    )
    return union_cls()

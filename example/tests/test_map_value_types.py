"""Regression tests for map value type resolution and descriptor normalization.

`map<string, Msg>` and `map<string, Enum>` used to lose their value type: the
generator fed runtime ``FieldDescriptor`` objects into ``TypeMapper.get_field_type()``,
whose branches key off ``FieldDescriptorProto.type_name`` — an attribute runtime
descriptors do not have. Message values silently fell back to ``Any``; enum values
raised ``AttributeError``, which a broad ``except`` swallowed, and the map field
then rendered as the synthetic entry type name (``FooEntry``), i.e. a name that is
never defined in the generated module.

protobuf >= 7 additionally removed ``FieldDescriptor.label`` from the runtime
descriptor (``is_repeated`` / ``is_required`` are the replacements), which is what
the runtime conversion helpers in ``ext.py`` read.
"""
from google.protobuf import descriptor_pb2

from example.tests.probe_schema import (
    HOLDER_FULL_NAME,
    LABEL_OPTIONAL,
    LABEL_REPEATED,
    MODEL_FILE,
    PROBE_PACKAGE,
    TYPE_MESSAGE,
    TYPE_STRING,
    generate_model_source,
    load_generated_model,
    pool_with_probe,
    runtime_holder,
)
from protobuf_pydantic_gen.type_mapper import TypeMapper
from protobuf_pydantic_gen.utils import (
    field_descriptor_to_proto,
    is_repeated_field,
    is_required_field,
)


def _map_type(map_field_name: str) -> str:
    pool = pool_with_probe()
    holder = pool.FindMessageTypeByName(HOLDER_FULL_NAME)
    field = holder.fields_by_name[map_field_name]
    mapper = TypeMapper(pool)
    return mapper.get_field_type(field, set(), {}, MODEL_FILE)


# --------------------------------------------------------------------------- #
# map value types
# --------------------------------------------------------------------------- #


def test_map_with_message_value_resolves_to_message_type():
    """`map<string, Inner>` must not degrade to `Dict[str, Any]`."""
    assert _map_type("inners") == "Dict[str, Inner]"


def test_map_with_enum_value_resolves_to_enum_type():
    """`map<string, Level>` must resolve to the enum, not to an entry type name."""
    assert _map_type("levels") == "Dict[str, Level]"


def test_map_with_scalar_value_is_unchanged():
    """Positive control: scalar maps already worked and must keep working."""
    assert _map_type("tags") == "Dict[str, str]"


def test_map_with_well_known_any_value_is_unchanged():
    """Positive control for `example.proto`'s `map<string, google.protobuf.Any>`."""
    assert _map_type("anys") == "Dict[str, Any]"


def test_map_with_numeric_value_is_unchanged():
    """Positive control: numeric maps must keep resolving through FIELD_TYPE_MAPPING."""
    assert _map_type("counts") == "Dict[str, int]"


def test_map_with_bytes_value_resolves_to_bytes():
    assert _map_type("blobs") == "Dict[str, bytes]"


# --------------------------------------------------------------------------- #
# descriptor normalization helpers
# --------------------------------------------------------------------------- #


def test_runtime_field_descriptor_has_no_type_name_but_normalizes_to_one():
    """Documents the contract the map path depends on."""
    runtime_field = runtime_holder().fields_by_name["inners"]
    assert not hasattr(runtime_field, "type_name")

    normalized = field_descriptor_to_proto(runtime_field)

    assert isinstance(normalized, descriptor_pb2.FieldDescriptorProto)
    assert normalized.type_name == f".{PROBE_PACKAGE}.Holder.InnersEntry"
    assert normalized.type == TYPE_MESSAGE


def test_field_descriptor_to_proto_passes_proto_descriptors_through():
    field = descriptor_pb2.FieldDescriptorProto()
    field.name = "tags"
    field.number = 1
    field.label = LABEL_REPEATED
    field.type = TYPE_STRING

    assert field_descriptor_to_proto(field) is field


def test_is_repeated_field_accepts_both_descriptor_kinds():
    holder = runtime_holder()
    map_field = holder.fields_by_name["inners"]
    singular = holder.fields_by_name["plain_score"]

    assert is_repeated_field(map_field) is True
    assert is_repeated_field(singular) is False
    assert (
        is_repeated_field(descriptor_pb2.FieldDescriptorProto(label=LABEL_REPEATED))
        is True
    )
    assert (
        is_repeated_field(descriptor_pb2.FieldDescriptorProto(label=LABEL_OPTIONAL))
        is False
    )


def test_is_required_field_accepts_both_descriptor_kinds():
    singular = runtime_holder().fields_by_name["plain_score"]

    assert is_required_field(singular) is False
    assert (
        is_required_field(descriptor_pb2.FieldDescriptorProto(label=LABEL_OPTIONAL))
        is False
    )
    assert (
        is_required_field(
            descriptor_pb2.FieldDescriptorProto(
                label=descriptor_pb2.FieldDescriptorProto.LABEL_REQUIRED
            )
        )
        is True
    )


# --------------------------------------------------------------------------- #
# end-to-end: generated model source + runtime round trip
# --------------------------------------------------------------------------- #


def test_generated_model_declares_resolved_map_value_types():
    source = generate_model_source()

    assert "inners: Optional[Dict[str, Inner]]" in source
    assert "levels: Optional[Dict[str, Level]]" in source
    assert "tags: Optional[Dict[str, str]]" in source
    assert "counts: Optional[Dict[str, int]]" in source
    assert "blobs: Optional[Dict[str, bytes]]" in source
    assert "Entry]" not in source, "map fields must not render as their entry type"


def test_generated_model_round_trips_message_valued_map():
    model_module = load_generated_model()

    instance = model_module.Holder(inners={"a": model_module.Inner(outcome="ok")})
    proto = instance.to_protobuf()

    assert proto.inners["a"].outcome == "ok"

    restored = model_module.Holder.from_protobuf(proto)

    assert restored.inners["a"].outcome == "ok"


def test_generated_model_round_trips_scalar_valued_map():
    model_module = load_generated_model()

    proto = model_module.Holder(tags={"a": "b"}).to_protobuf()

    assert dict(proto.tags) == {"a": "b"}


def test_generated_model_round_trips_numeric_valued_map():
    model_module = load_generated_model()

    proto = model_module.Holder(counts={"a": 3}).to_protobuf()

    assert dict(proto.counts) == {"a": 3}


def test_generated_model_round_trips_enum_valued_map():
    model_module = load_generated_model()

    instance = model_module.Holder(levels={"a": model_module.Level.LEVEL_UNSPECIFIED})
    proto = instance.to_protobuf()

    assert proto.levels["a"] == 0

    restored = model_module.Holder.from_protobuf(proto)

    assert restored.levels["a"] == model_module.Level.LEVEL_UNSPECIFIED

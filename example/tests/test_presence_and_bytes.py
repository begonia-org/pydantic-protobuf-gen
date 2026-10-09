"""Regression tests for proto3 `optional` presence and `bytes` fidelity.

Both were silently wrong before:

* `optional double` was generated as `Optional[float] = _Field(default=0.0)`, and
  `model2protobuf` replaced a `None` value with the field's default — so "field was
  never set" and "field is 0" produced byte-identical messages.
* `bytes` values were handed to `ParseDict` (which wants base64 text) and read back
  from `MessageToDict` (which returns base64 text) without decoding, so every bytes
  field — scalar or map value — round-tripped to the base64 text of the original.
"""
from example.tests.probe_schema import (
    generate_model_source,
    holder_message,
    load_generated_model,
)


# --------------------------------------------------------------------------- #
# proto3 `optional` presence
# --------------------------------------------------------------------------- #


def test_generated_optional_scalar_defaults_to_none():
    source = generate_model_source()

    assert "opt_score: Optional[float] = _Field(default=None)" in source
    # implicit-presence scalars keep their zero default
    assert "plain_score: Optional[float] = _Field(default=0.0)" in source


def test_unset_optional_field_is_not_written_to_the_wire():
    model_module = load_generated_model()

    proto = model_module.Holder().to_protobuf()

    assert proto.HasField("opt_score") is False
    assert proto.SerializeToString() == b""


def test_explicit_zero_optional_field_is_written_to_the_wire():
    model_module = load_generated_model()

    proto = model_module.Holder(opt_score=0.0).to_protobuf()

    assert proto.HasField("opt_score") is True
    assert proto.opt_score == 0.0


def test_none_optional_field_is_treated_as_unset():
    model_module = load_generated_model()

    proto = model_module.Holder(opt_score=None).to_protobuf()

    assert proto.HasField("opt_score") is False


def test_from_protobuf_keeps_absent_optional_field_unset():
    model_module = load_generated_model()

    restored = model_module.Holder.from_protobuf(holder_message())

    assert restored.opt_score is None


def test_from_protobuf_reads_present_optional_field():
    model_module = load_generated_model()

    message = holder_message()
    message.opt_score = 0.0

    restored = model_module.Holder.from_protobuf(message)

    assert restored.opt_score == 0.0


# --------------------------------------------------------------------------- #
# bytes fidelity
# --------------------------------------------------------------------------- #


def test_bytes_scalar_round_trips():
    model_module = load_generated_model()
    payload = b"\x00\xff binary\x80"

    proto = model_module.Holder(payload=payload).to_protobuf()

    assert proto.payload == payload
    assert model_module.Holder.from_protobuf(proto).payload == payload


def test_bytes_valued_map_round_trips():
    model_module = load_generated_model()
    blob = b"\x00\xff\x80"

    proto = model_module.Holder(blobs={"a": blob}).to_protobuf()

    assert proto.blobs["a"] == blob
    assert model_module.Holder.from_protobuf(proto).blobs["a"] == blob

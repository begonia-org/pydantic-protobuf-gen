"""Regression tests for oneof support (option A: one `Optional[Union[...]]` field).

Before, the generator had no `oneof` awareness at all: every member was emitted as an
independent field, `model_dump()` therefore always carried all of them, and
`ParseDict` rejected the message outright:

    ParseError: Message type "..." should not have multiple "..." oneof fields
"""
from example.tests.probe_schema import (
    generate_oneof_model_source,
    load_oneof_model,
    union_message,
)


def test_generated_oneof_is_a_single_union_field():
    source = generate_oneof_model_source()

    assert "value: Optional[_Union[float, str, Inner]]" in source
    assert "value: Optional[_Union[float, str, Inner]] = _Field(default=None)" in source
    assert "Union as _Union" in source
    # the members must not be emitted as individual model fields
    assert "numeric_value:" not in source
    assert "text_value:" not in source
    assert "inner:" not in source


def test_unset_oneof_is_not_written_to_the_wire():
    model_module = load_oneof_model()

    proto = model_module.Union(metric="M").to_protobuf()

    assert proto.WhichOneof("value") is None
    assert proto.SerializeToString() == b"\n\x01M"


def test_forward_sets_exactly_one_member():
    model_module = load_oneof_model()

    cases = [
        ("numeric_value", 1.5),
        ("text_value", "a"),
        ("inner", model_module.Inner(outcome="ok")),
    ]
    for member_name, value in cases:
        proto = model_module.Union(**{"value": value}).to_protobuf()

        assert proto.WhichOneof("value") == member_name, member_name
        for other in ("numeric_value", "text_value", "inner"):
            if other != member_name:
                assert proto.HasField(other) is False, (member_name, other)


def test_reverse_reads_the_selected_member():
    model_module = load_oneof_model()

    for member_name, value in [
        ("numeric_value", 1.5),
        ("text_value", "a"),
    ]:
        proto = model_module.Union(**{"value": value}).to_protobuf()

        restored = model_module.Union.from_protobuf(proto)

        assert restored.value == value, member_name


def test_message_member_round_trips():
    model_module = load_oneof_model()

    proto = model_module.Union(value=model_module.Inner(outcome="ok")).to_protobuf()

    assert proto.WhichOneof("value") == "inner"
    assert proto.inner.outcome == "ok"

    restored = model_module.Union.from_protobuf(proto)

    assert isinstance(restored.value, model_module.Inner)
    assert restored.value.outcome == "ok"


def test_reverse_keeps_unset_oneof_as_none():
    model_module = load_oneof_model()

    restored = model_module.Union.from_protobuf(union_message())

    assert restored.value is None


def test_reverse_picks_the_message_member_despite_union_order():
    """`inner` is the third union member; resolution must not just take the first."""
    model_module = load_oneof_model()

    message = union_message()
    message.inner.outcome = "ok"

    restored = model_module.Union.from_protobuf(message)

    assert isinstance(restored.value, model_module.Inner)
    assert restored.value.outcome == "ok"

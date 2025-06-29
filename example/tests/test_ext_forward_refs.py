from __future__ import annotations

from pydantic import BaseModel

from example.pb.example_pb2 import Example as ExampleProto
from protobuf_pydantic_gen.ext import protobuf2model


class ForwardRefExample2(BaseModel):
    type: int = 0


class ForwardRefExample(BaseModel):
    name: str | None = None
    age: int | None = None
    examples: list["ForwardRefExample2"] | None = None


ForwardRefExample.model_rebuild()


def test_protobuf2model_resolves_forward_refs_for_repeated_nested_messages():
    proto = ExampleProto()
    proto.name = "forward-ref"
    proto.age = 7
    item = proto.examples.add()
    item.type = 1

    model = protobuf2model(ForwardRefExample, proto)

    assert model.name == "forward-ref"
    assert model.age == 7
    assert model.examples is not None
    assert len(model.examples) == 1
    assert isinstance(model.examples[0], ForwardRefExample2)
    assert model.examples[0].type == 1

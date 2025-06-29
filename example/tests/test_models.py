import datetime
from example.pb.example_pb2 import Example as ExampleProto  # noqa: F401
from example.models.example_model import Example, Nested, ExampleType
from example.models.example2_model import Example2


def test_example_model_basic():
    ex = Example(name="张三", age=18)
    assert ex.name == "张三"
    assert ex.age == 18
    assert isinstance(ex.created_at, (datetime.datetime, type(None)))
    assert ex.examples == []
    assert ex.embeddings == []
    assert ex.emails == ["example@example.com", "example2@example.com"]


def test_nested_model():
    nested = Nested(full_name="嵌套")
    assert nested.name == "嵌套"


def test_enum_field():
    ex2 = Example2(type=ExampleType.TYPE1)
    assert ex2.type == ExampleType.TYPE1

# 如有 to_protobuf/from_protobuf，可 mock 或集成测试


def test_to_from_protobuf_roundtrip():
    ex = Example(name="test", age=1)
    pb = ex.to_protobuf()
    ex2 = Example.from_protobuf(pb)
    assert ex2.name == ex.name
    assert ex2.age == ex.age


def test_to_from_protobuf_roundtrip_with_nested_examples():
    ex = Example(name="test", age=1, examples=[Example2(type=ExampleType.TYPE1)])
    pb = ex.to_protobuf()
    ex2 = Example.from_protobuf(pb)

    assert ex2.examples is not None
    assert len(ex2.examples) == 1
    assert ex2.examples[0].type == ExampleType.TYPE1

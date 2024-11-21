from google.protobuf import descriptor_pb2 as _descriptor_pb2
from protobuf_pydantic_gen import pydantic_pb2 as _pydantic_pb2
from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf import any_pb2 as _any_pb2
import constant_pb2 as _constant_pb2
import example2_pb2 as _example2_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Example(_message.Message):
    __slots__ = ["age", "created_at", "emails", "entry", "examples", "name", "nested", "score", "type"]
    class EntryEntry(_message.Message):
        __slots__ = ["key", "value"]
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: _any_pb2.Any
        def __init__(self, key: _Optional[str] = ..., value: _Optional[_Union[_any_pb2.Any, _Mapping]] = ...) -> None: ...
    AGE_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    EMAILS_FIELD_NUMBER: _ClassVar[int]
    ENTRY_FIELD_NUMBER: _ClassVar[int]
    EXAMPLES_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    NESTED_FIELD_NUMBER: _ClassVar[int]
    SCORE_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    age: int
    created_at: _timestamp_pb2.Timestamp
    emails: _containers.RepeatedScalarFieldContainer[str]
    entry: _containers.MessageMap[str, _any_pb2.Any]
    examples: _containers.RepeatedCompositeFieldContainer[_example2_pb2.Example2]
    name: str
    nested: Nested
    score: float
    type: _constant_pb2.ExampleType
    def __init__(self, name: _Optional[str] = ..., age: _Optional[int] = ..., emails: _Optional[_Iterable[str]] = ..., examples: _Optional[_Iterable[_Union[_example2_pb2.Example2, _Mapping]]] = ..., entry: _Optional[_Mapping[str, _any_pb2.Any]] = ..., nested: _Optional[_Union[Nested, _Mapping]] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., type: _Optional[_Union[_constant_pb2.ExampleType, str]] = ..., score: _Optional[float] = ...) -> None: ...

class Nested(_message.Message):
    __slots__ = ["name"]
    NAME_FIELD_NUMBER: _ClassVar[int]
    name: str
    def __init__(self, name: _Optional[str] = ...) -> None: ...

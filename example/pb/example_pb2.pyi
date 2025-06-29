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

class Nested(_message.Message):
    __slots__ = ("name",)
    NAME_FIELD_NUMBER: _ClassVar[int]
    name: str
    def __init__(self, name: _Optional[str] = ...) -> None: ...

class Example(_message.Message):
    __slots__ = ("name", "age", "emails", "examples", "entry", "nested", "created_at", "type", "score", "metadatas")
    class EntryEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: _any_pb2.Any
        def __init__(self, key: _Optional[str] = ..., value: _Optional[_Union[_any_pb2.Any, _Mapping]] = ...) -> None: ...
    class MetadatasEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: _any_pb2.Any
        def __init__(self, key: _Optional[str] = ..., value: _Optional[_Union[_any_pb2.Any, _Mapping]] = ...) -> None: ...
    NAME_FIELD_NUMBER: _ClassVar[int]
    AGE_FIELD_NUMBER: _ClassVar[int]
    EMAILS_FIELD_NUMBER: _ClassVar[int]
    EXAMPLES_FIELD_NUMBER: _ClassVar[int]
    ENTRY_FIELD_NUMBER: _ClassVar[int]
    NESTED_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    SCORE_FIELD_NUMBER: _ClassVar[int]
    METADATAS_FIELD_NUMBER: _ClassVar[int]
    name: str
    age: int
    emails: _containers.RepeatedScalarFieldContainer[str]
    examples: _containers.RepeatedCompositeFieldContainer[_example2_pb2.Example2]
    entry: _containers.MessageMap[str, _any_pb2.Any]
    nested: Nested
    created_at: _timestamp_pb2.Timestamp
    type: _constant_pb2.ExampleType
    score: float
    metadatas: _containers.MessageMap[str, _any_pb2.Any]
    def __init__(self, name: _Optional[str] = ..., age: _Optional[int] = ..., emails: _Optional[_Iterable[str]] = ..., examples: _Optional[_Iterable[_Union[_example2_pb2.Example2, _Mapping]]] = ..., entry: _Optional[_Mapping[str, _any_pb2.Any]] = ..., nested: _Optional[_Union[Nested, _Mapping]] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., type: _Optional[_Union[_constant_pb2.ExampleType, str]] = ..., score: _Optional[float] = ..., metadatas: _Optional[_Mapping[str, _any_pb2.Any]] = ...) -> None: ...

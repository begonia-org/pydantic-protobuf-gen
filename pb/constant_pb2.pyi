from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from typing import ClassVar as _ClassVar

DESCRIPTOR: _descriptor.FileDescriptor

class ExampleType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    UNKNOWN: _ClassVar[ExampleType]
    TYPE1: _ClassVar[ExampleType]
    TYPE2: _ClassVar[ExampleType]
    TYPE3: _ClassVar[ExampleType]
UNKNOWN: ExampleType
TYPE1: ExampleType
TYPE2: ExampleType
TYPE3: ExampleType

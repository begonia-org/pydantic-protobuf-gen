from google.protobuf import descriptor_pb2 as _descriptor_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DATABASE_FIELD_NUMBER: _ClassVar[int]
DESCRIPTOR: _descriptor.FileDescriptor
FIELD_FIELD_NUMBER: _ClassVar[int]
database: _descriptor.FieldDescriptor
field: _descriptor.FieldDescriptor

class Annotation(_message.Message):
    __slots__ = ["alias", "const", "default", "description", "example", "field_type", "foreign_key", "ge", "gt", "index", "le", "lt", "max_length", "min_length", "nullable", "primary_key", "required", "sa_column_type", "title", "unique"]
    ALIAS_FIELD_NUMBER: _ClassVar[int]
    CONST_FIELD_NUMBER: _ClassVar[int]
    DEFAULT_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    EXAMPLE_FIELD_NUMBER: _ClassVar[int]
    FIELD_TYPE_FIELD_NUMBER: _ClassVar[int]
    FOREIGN_KEY_FIELD_NUMBER: _ClassVar[int]
    GE_FIELD_NUMBER: _ClassVar[int]
    GT_FIELD_NUMBER: _ClassVar[int]
    INDEX_FIELD_NUMBER: _ClassVar[int]
    LE_FIELD_NUMBER: _ClassVar[int]
    LT_FIELD_NUMBER: _ClassVar[int]
    MAX_LENGTH_FIELD_NUMBER: _ClassVar[int]
    MIN_LENGTH_FIELD_NUMBER: _ClassVar[int]
    NULLABLE_FIELD_NUMBER: _ClassVar[int]
    PRIMARY_KEY_FIELD_NUMBER: _ClassVar[int]
    REQUIRED_FIELD_NUMBER: _ClassVar[int]
    SA_COLUMN_TYPE_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    UNIQUE_FIELD_NUMBER: _ClassVar[int]
    alias: str
    const: bool
    default: str
    description: str
    example: str
    field_type: str
    foreign_key: str
    ge: float
    gt: float
    index: bool
    le: float
    lt: float
    max_length: int
    min_length: int
    nullable: bool
    primary_key: bool
    required: bool
    sa_column_type: str
    title: str
    unique: bool
    def __init__(self, description: _Optional[str] = ..., example: _Optional[str] = ..., default: _Optional[str] = ..., alias: _Optional[str] = ..., title: _Optional[str] = ..., required: bool = ..., nullable: bool = ..., primary_key: bool = ..., unique: bool = ..., index: bool = ..., const: bool = ..., field_type: _Optional[str] = ..., sa_column_type: _Optional[str] = ..., min_length: _Optional[int] = ..., max_length: _Optional[int] = ..., gt: _Optional[float] = ..., ge: _Optional[float] = ..., lt: _Optional[float] = ..., le: _Optional[float] = ..., foreign_key: _Optional[str] = ...) -> None: ...

class CompoundIndex(_message.Message):
    __slots__ = ["index_type", "indexs", "name"]
    INDEXS_FIELD_NUMBER: _ClassVar[int]
    INDEX_TYPE_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    index_type: str
    indexs: _containers.RepeatedScalarFieldContainer[str]
    name: str
    def __init__(self, indexs: _Optional[_Iterable[str]] = ..., index_type: _Optional[str] = ..., name: _Optional[str] = ...) -> None: ...

class DatabaseAnnotation(_message.Message):
    __slots__ = ["as_table", "compound_index", "table_name"]
    AS_TABLE_FIELD_NUMBER: _ClassVar[int]
    COMPOUND_INDEX_FIELD_NUMBER: _ClassVar[int]
    TABLE_NAME_FIELD_NUMBER: _ClassVar[int]
    as_table: bool
    compound_index: _containers.RepeatedCompositeFieldContainer[CompoundIndex]
    table_name: str
    def __init__(self, table_name: _Optional[str] = ..., compound_index: _Optional[_Iterable[_Union[CompoundIndex, _Mapping]]] = ..., as_table: bool = ...) -> None: ...

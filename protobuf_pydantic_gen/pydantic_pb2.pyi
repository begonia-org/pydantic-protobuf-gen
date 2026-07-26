from google.protobuf import descriptor_pb2 as _descriptor_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor
DATABASE_FIELD_NUMBER: _ClassVar[int]
database: _descriptor.FieldDescriptor
FIELD_FIELD_NUMBER: _ClassVar[int]
field: _descriptor.FieldDescriptor
SERVICE_AUTH_FIELD_NUMBER: _ClassVar[int]
service_auth: _descriptor.FieldDescriptor
METHOD_AUTH_FIELD_NUMBER: _ClassVar[int]
method_auth: _descriptor.FieldDescriptor
METHOD_EXTRA_FIELD_NUMBER: _ClassVar[int]
method_extra: _descriptor.FieldDescriptor
OPTIONS_FIELD_NUMBER: _ClassVar[int]
options: _descriptor.FieldDescriptor

class Annotation(_message.Message):
    __slots__ = ("description", "example", "default", "alias", "title", "required", "nullable", "primary_key", "unique", "index", "const", "field_type", "sa_column_type", "min_length", "max_length", "gt", "ge", "lt", "le", "foreign_key", "label", "default_factory", "enum_storage", "sa_auto_update", "server_default")
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    EXAMPLE_FIELD_NUMBER: _ClassVar[int]
    DEFAULT_FIELD_NUMBER: _ClassVar[int]
    ALIAS_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    REQUIRED_FIELD_NUMBER: _ClassVar[int]
    NULLABLE_FIELD_NUMBER: _ClassVar[int]
    PRIMARY_KEY_FIELD_NUMBER: _ClassVar[int]
    UNIQUE_FIELD_NUMBER: _ClassVar[int]
    INDEX_FIELD_NUMBER: _ClassVar[int]
    CONST_FIELD_NUMBER: _ClassVar[int]
    FIELD_TYPE_FIELD_NUMBER: _ClassVar[int]
    SA_COLUMN_TYPE_FIELD_NUMBER: _ClassVar[int]
    MIN_LENGTH_FIELD_NUMBER: _ClassVar[int]
    MAX_LENGTH_FIELD_NUMBER: _ClassVar[int]
    GT_FIELD_NUMBER: _ClassVar[int]
    GE_FIELD_NUMBER: _ClassVar[int]
    LT_FIELD_NUMBER: _ClassVar[int]
    LE_FIELD_NUMBER: _ClassVar[int]
    FOREIGN_KEY_FIELD_NUMBER: _ClassVar[int]
    LABEL_FIELD_NUMBER: _ClassVar[int]
    DEFAULT_FACTORY_FIELD_NUMBER: _ClassVar[int]
    ENUM_STORAGE_FIELD_NUMBER: _ClassVar[int]
    SA_AUTO_UPDATE_FIELD_NUMBER: _ClassVar[int]
    SERVER_DEFAULT_FIELD_NUMBER: _ClassVar[int]
    description: str
    example: str
    default: str
    alias: str
    title: str
    required: bool
    nullable: bool
    primary_key: bool
    unique: bool
    index: bool
    const: bool
    field_type: str
    sa_column_type: str
    min_length: int
    max_length: int
    gt: float
    ge: float
    lt: float
    le: float
    foreign_key: str
    label: str
    default_factory: str
    enum_storage: str
    sa_auto_update: bool
    server_default: str
    def __init__(self, description: _Optional[str] = ..., example: _Optional[str] = ..., default: _Optional[str] = ..., alias: _Optional[str] = ..., title: _Optional[str] = ..., required: bool = ..., nullable: bool = ..., primary_key: bool = ..., unique: bool = ..., index: bool = ..., const: bool = ..., field_type: _Optional[str] = ..., sa_column_type: _Optional[str] = ..., min_length: _Optional[int] = ..., max_length: _Optional[int] = ..., gt: _Optional[float] = ..., ge: _Optional[float] = ..., lt: _Optional[float] = ..., le: _Optional[float] = ..., foreign_key: _Optional[str] = ..., label: _Optional[str] = ..., default_factory: _Optional[str] = ..., enum_storage: _Optional[str] = ..., sa_auto_update: bool = ..., server_default: _Optional[str] = ...) -> None: ...

class CompoundIndex(_message.Message):
    __slots__ = ("indexs", "index_type", "name")
    INDEXS_FIELD_NUMBER: _ClassVar[int]
    INDEX_TYPE_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    indexs: _containers.RepeatedScalarFieldContainer[str]
    index_type: str
    name: str
    def __init__(self, indexs: _Optional[_Iterable[str]] = ..., index_type: _Optional[str] = ..., name: _Optional[str] = ...) -> None: ...

class DatabaseAnnotation(_message.Message):
    __slots__ = ("table_name", "compound_index", "as_table")
    TABLE_NAME_FIELD_NUMBER: _ClassVar[int]
    COMPOUND_INDEX_FIELD_NUMBER: _ClassVar[int]
    AS_TABLE_FIELD_NUMBER: _ClassVar[int]
    table_name: str
    compound_index: _containers.RepeatedCompositeFieldContainer[CompoundIndex]
    as_table: bool
    def __init__(self, table_name: _Optional[str] = ..., compound_index: _Optional[_Iterable[_Union[CompoundIndex, _Mapping]]] = ..., as_table: bool = ...) -> None: ...

class AuthOption(_message.Message):
    __slots__ = ("required", "scopes", "role", "permission")
    REQUIRED_FIELD_NUMBER: _ClassVar[int]
    SCOPES_FIELD_NUMBER: _ClassVar[int]
    ROLE_FIELD_NUMBER: _ClassVar[int]
    PERMISSION_FIELD_NUMBER: _ClassVar[int]
    required: bool
    scopes: _containers.RepeatedScalarFieldContainer[str]
    role: str
    permission: str
    def __init__(self, required: bool = ..., scopes: _Optional[_Iterable[str]] = ..., role: _Optional[str] = ..., permission: _Optional[str] = ...) -> None: ...

class MethodAuthOptions(_message.Message):
    __slots__ = ("is_redirect",)
    IS_REDIRECT_FIELD_NUMBER: _ClassVar[int]
    is_redirect: bool
    def __init__(self, is_redirect: bool = ...) -> None: ...

class EnumValueOptions(_message.Message):
    __slots__ = ("description", "label")
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    LABEL_FIELD_NUMBER: _ClassVar[int]
    description: str
    label: str
    def __init__(self, description: _Optional[str] = ..., label: _Optional[str] = ...) -> None: ...

"""
Constants and type mappings for protobuf to pydantic conversion
"""
from google.protobuf import descriptor_pb2
from typing import Dict, Set

# Version information
__version__ = "0.1.0"

# Protobuf to Python type mappings
FIELD_TYPE_MAPPING: Dict[int, str] = {
    descriptor_pb2.FieldDescriptorProto.TYPE_DOUBLE: "float",
    descriptor_pb2.FieldDescriptorProto.TYPE_FLOAT: "float",
    descriptor_pb2.FieldDescriptorProto.TYPE_INT64: "int",
    descriptor_pb2.FieldDescriptorProto.TYPE_UINT64: "int",
    descriptor_pb2.FieldDescriptorProto.TYPE_INT32: "int",
    descriptor_pb2.FieldDescriptorProto.TYPE_FIXED64: "int",
    descriptor_pb2.FieldDescriptorProto.TYPE_FIXED32: "int",
    descriptor_pb2.FieldDescriptorProto.TYPE_BOOL: "bool",
    descriptor_pb2.FieldDescriptorProto.TYPE_STRING: "str",
    descriptor_pb2.FieldDescriptorProto.TYPE_BYTES: "bytes",
    descriptor_pb2.FieldDescriptorProto.TYPE_UINT32: "int",
    descriptor_pb2.FieldDescriptorProto.TYPE_ENUM: "Enum",
    descriptor_pb2.FieldDescriptorProto.TYPE_SFIXED32: "int",
    descriptor_pb2.FieldDescriptorProto.TYPE_SFIXED64: "int",
    descriptor_pb2.FieldDescriptorProto.TYPE_SINT32: "int",
    descriptor_pb2.FieldDescriptorProto.TYPE_SINT64: "int",
}

# Default values by type
DEFAULT_VALUES: Dict[str, str] = {
    "str": '""',
    "int": "0",
    "float": "0.0",
    "bool": "False",
    "bytes": "b''",
    "datetime.datetime": "None",
    "Any": "None",
    "List": "None",
    "Dict": "None",
}

# Special protobuf types
SPECIAL_PROTOBUF_TYPES: Dict[str, str] = {
    ".google.protobuf.Timestamp": "datetime.datetime",
}

# Files to skip during generation
SKIP_FILES: Set[str] = {
    "google/",
    "pydantic",
}

# Required imports for generated code - minimal base set
BASE_IMPORTS: Set[str] = set()

# Conditional imports based on what's actually used
CONDITIONAL_IMPORTS = {
    'datetime': "import datetime",
    'enum': "from enum import Enum as _Enum",
    'pydantic_base': "from pydantic import BaseModel, ConfigDict",
    'pydantic_field': "from pydantic import Field as _Field",
    'sqlmodel': "from sqlmodel import SQLModel, Field",
    'typing_base': "from typing import Type",
    'typing_optional': "Optional",
    'typing_list': "List",
    'typing_dict': "Dict",
    'typing_any': "Any",
    'protobuf_message': "from google.protobuf import message as _message",
    'protobuf_factory': "from google.protobuf import message_factory",
    'ext_functions': "from protobuf_pydantic_gen.ext import model2protobuf, protobuf2model, pool",
}

# SQL Model imports (optional)
SQLMODEL_IMPORTS_BASE: Set[str] = {
    "from sqlmodel import SQLModel, Field",
}

# Validation patterns
VALID_LOG_LEVELS: Set[str] = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}

# Template configuration
TEMPLATE_FILE: str = "template.j2"
AUTOPEP8_OPTIONS: Dict[str, any] = {
    "max_line_length": 120,
    "in_place": True,
    "aggressive": 5,
}

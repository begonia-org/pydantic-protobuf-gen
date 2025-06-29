"""
Data models for protobuf to pydantic conversion
"""
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class MessageType(Enum):
    """Type of message being generated"""
    CLASS = "class"
    ENUM = "enum"


@dataclass
class Field:
    """Represents a field in a protobuf message"""
    name: str
    type: str
    repeated: bool
    required: bool
    attributes: str
    ext: Dict[str, Any]
    message_info: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Validate field data after initialization"""
        if not self.name:
            raise ValueError("Field name cannot be empty")
        if not self.type:
            raise ValueError(f"Field type cannot be empty - {self.name}")

    def __str__(self) -> str:
        return f"Field({self.name}, {self.type}, repeated={self.repeated}, required={self.required})"


@dataclass
class EnumField:
    """Represents an enum field"""
    name: str
    value: str

    def __post_init__(self):
        """Validate enum field data"""
        if not self.name:
            raise ValueError("Enum field name cannot be empty")
        if self.value is None:
            raise ValueError("Enum field value cannot be None")

    def __str__(self) -> str:
        return f"EnumField({self.name}, {self.value})"


@dataclass
class Message:
    """Represents a protobuf message or enum"""
    message_name: str
    fields: List[Field]
    message_type: MessageType = MessageType.CLASS
    table_name: Optional[str] = None
    table_args: Optional[Tuple[str, ...]] = None
    as_table: bool = False
    proto_full_name: str = ""
    proto_file: str = ""
    ext: Dict[str, Any] = None

    def __post_init__(self):
        """Process message data after initialization"""
        if not self.message_name:
            raise ValueError("Message name cannot be empty")

        # Auto-generate table name if not provided
        if self.table_name is None:
            self.table_name = self._snake_case(self.message_name)

    def _snake_case(self, name: str) -> str:
        """Convert camelCase to snake_case"""
        import re
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

    def __str__(self) -> str:
        return f"Message({self.message_name}, {len(self.fields)} fields, type={self.message_type.value})"


@dataclass
class ServiceMethod:
    """Represents a gRPC service method"""
    name: str
    input_type: str
    output_type: str
    streaming_type: str
    method_full_name: str
    http_info: Optional[Dict[str, Any]] = None
    options: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Validate service method data"""
        if not self.name:
            raise ValueError("Method name cannot be empty")
        if not self.input_type:
            raise ValueError("Input type cannot be empty")
        if not self.output_type:
            raise ValueError("Output type cannot be empty")


@dataclass
class Service:
    """Represents a gRPC service"""
    name: str
    methods: List[ServiceMethod]
    package: str = ""

    def __post_init__(self):
        """Validate service data"""
        if not self.name:
            raise ValueError("Service name cannot be empty")

    def __str__(self) -> str:
        return f"Service({self.name}, {len(self.methods)} methods)"


@dataclass
class GenerationResult:
    """Result of code generation"""
    filename: str
    content: str
    messages: List[Message]
    services: List[Service]

    def __str__(self) -> str:
        return f"GenerationResult({self.filename}, {len(self.messages)} messages, {len(self.services)} services)"

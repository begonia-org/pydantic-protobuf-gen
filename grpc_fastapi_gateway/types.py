"""
Type definitions for the gRPC FastAPI Gateway
"""
from typing import TypedDict, Literal, Optional, Dict, Any, Callable, Type, Union
from typing_extensions import NotRequired
from pydantic import BaseModel


# HTTP configuration
class HttpInfo(TypedDict):
    """HTTP configuration for a gRPC method"""
    method: str
    path: str
    body: NotRequired[Optional[str]]


# Service method information
class MethodInfo(TypedDict):
    """Information about a gRPC method"""
    input_type: str
    output_type: str
    streaming_type: Literal["unary", "server_streaming",
                            "client_streaming", "bidirectional_streaming"]
    http: HttpInfo
    method_full_name: str
    options: NotRequired[Dict[str, Any]]


# Service definition
class ServiceInfo(TypedDict):
    """Information about a gRPC service"""
    methods: Dict[str, MethodInfo]


# Complete services configuration
ServicesConfig = Dict[str, ServiceInfo]

# Streaming types
StreamingType = Literal["unary", "server_streaming",
                        "client_streaming", "bidirectional_streaming"]

# Service method callable types
UnaryMethod = Callable[[BaseModel], BaseModel]
ServerStreamingMethod = Callable[[BaseModel], Any]  # AsyncGenerator
# AsyncGenerator -> BaseModel
ClientStreamingMethod = Callable[[Any], BaseModel]
# AsyncGenerator -> AsyncGenerator
BidirectionalStreamingMethod = Callable[[Any], Any]

# Union of all method types
ServiceMethod = Union[
    UnaryMethod,
    ServerStreamingMethod,
    ClientStreamingMethod,
    BidirectionalStreamingMethod
]

# Service registry entry


class ServiceEntry(TypedDict):
    """Entry in the service registry"""
    service: object
    method: ServiceMethod
    input_type: Type[BaseModel]
    output_type: Type[BaseModel]
    input_pb2: Type
    output_pb2: Type
    streaming_type: StreamingType
    http_info: HttpInfo
    group: str
    input_message_cls: Type
    output_message_cls: Type


# WebSocket message types
class WebSocketMessage(TypedDict):
    """WebSocket message structure"""
    type: Literal["request", "response", "error", "complete"]
    data: NotRequired[Dict[str, Any]]
    error: NotRequired[str]


# Error response structure
class ErrorResponse(TypedDict):
    """Standard error response structure"""
    error: str
    code: int
    details: NotRequired[Dict[str, Any]]


# Metrics data
class MetricsData(TypedDict):
    """Metrics data structure"""
    method: str
    status: str
    duration: float
    streaming_type: StreamingType
    error_type: NotRequired[str]


# Configuration types
class CacheConfig(TypedDict):
    """Cache configuration"""
    enabled: bool
    max_size: int
    ttl_seconds: NotRequired[int]


class SecurityConfig(TypedDict):
    """Security configuration"""
    enable_validation: bool
    sanitize_errors: bool
    max_error_length: int


class PerformanceConfig(TypedDict):
    """Performance configuration"""
    max_message_size: int
    request_timeout: int
    websocket_timeout: int
    max_connections: int


# Class loading result
class ClassLoadResult(TypedDict):
    """Result of class loading operation"""
    success: bool
    class_type: NotRequired[Type]
    error: NotRequired[str]
    cached: NotRequired[bool]

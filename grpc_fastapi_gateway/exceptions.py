"""
Custom exceptions for the gRPC FastAPI Gateway
"""
import grpc
from typing import Dict, List, Optional, Any


def http_status_to_grpc_status(status_code: int) -> grpc.StatusCode:
    """Convert HTTP status code to gRPC status code"""
    if 200 <= status_code < 300:
        return grpc.StatusCode.OK
    elif status_code == 400:
        return grpc.StatusCode.INVALID_ARGUMENT
    elif status_code == 401:
        return grpc.StatusCode.UNAUTHENTICATED
    elif status_code == 403:
        return grpc.StatusCode.PERMISSION_DENIED
    elif status_code == 404:
        return grpc.StatusCode.NOT_FOUND
    elif status_code == 409:
        return grpc.StatusCode.ALREADY_EXISTS
    elif status_code == 500:
        return grpc.StatusCode.INTERNAL
    else:
        return grpc.StatusCode.UNKNOWN


class GatewayError(Exception):
    """Base exception for gateway-related errors"""

    def __init__(
        self,
        message: str,
        error_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for JSON serialization"""
        return {
            "error": self.message,
            "code": self.error_code,
            "details": self.details
        }


class GrpcError(GatewayError):
    """Custom gRPC error exception"""

    def __init__(self, message: str, status_code: grpc.StatusCode):
        super().__init__(message, status_code.value[0])
        self.status_code = status_code


class ServiceNotFoundError(GatewayError):
    """Raised when a service is not found"""

    def __init__(self, service_name: str):
        super().__init__(
            f"Service '{service_name}' not found",
            404,
            {"service_name": service_name}
        )


class MethodNotFoundError(GatewayError):
    """Raised when a method is not found in a service"""

    def __init__(self, service_name: str, method_name: str):
        super().__init__(
            f"Method '{method_name}' not found in service '{service_name}'",
            404,
            {"service_name": service_name, "method_name": method_name}
        )


class ModelNotFoundError(GatewayError):
    """Raised when a model class is not found"""

    def __init__(self, model_name: str, directory: str):
        super().__init__(
            f"Model '{model_name}' not found in directory '{directory}'",
            404,
            {"model_name": model_name, "directory": directory}
        )


class ValidationError(GatewayError):
    """Raised when request validation fails"""

    def __init__(self, message: str, field_errors: List[str]):
        super().__init__(
            message,
            400,
            {"field_errors": field_errors}
        )


class ConnectionError(GatewayError):
    """Raised when connection-related errors occur"""

    def __init__(self, message: str, connection_type: str = "unknown"):
        super().__init__(
            message,
            503,
            {"connection_type": connection_type}
        )


class ConfigurationError(GatewayError):
    """Raised when configuration is invalid"""

    def __init__(self, message: str, config_field: Optional[str] = None):
        super().__init__(
            message,
            500,
            {"config_field": config_field}
        )


class SecurityError(GatewayError):
    """Raised when security validation fails"""

    def __init__(self, message: str, security_type: str = "general"):
        super().__init__(
            message,
            403,
            {"security_type": security_type}
        )


class ServiceLoadError(GatewayError):
    """Raised when service loading fails"""

    def __init__(self, message: str, service_name: Optional[str] = None):
        super().__init__(
            message,
            500,
            {"service_name": service_name}
        )


class ClassLoadingError(GatewayError):
    """Raised when class loading fails"""

    def __init__(self, message: str, class_name: Optional[str] = None):
        super().__init__(
            message,
            500,
            {"class_name": class_name}
        )

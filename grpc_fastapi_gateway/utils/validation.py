"""
Input validation utilities for the gRPC FastAPI Gateway
"""
import re
import json
from typing import Any, Dict, List, Optional
from ..exceptions import ValidationError, SecurityError
from ..config import get_config


class InputValidator:
    """Input validation and sanitization utilities"""
    
    # Regex patterns for validation
    SERVICE_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9_.]+$')
    METHOD_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9_]+$')
    PATH_PATTERN = re.compile(r'^[a-zA-Z0-9_/.-]+$')
    
    # File path patterns to remove from error messages
    FILE_PATH_PATTERN = re.compile(r'/[^\s]*\.py')
    LINE_NUMBER_PATTERN = re.compile(r'line \d+')
    
    def __init__(self):
        self.config = get_config()
    
    @classmethod
    def validate_service_name(cls, service_name: str) -> bool:
        """
        Validate service name format
        
        Args:
            service_name: The service name to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not service_name or not isinstance(service_name, str):
            return False
        if len(service_name) > 100:  # Reasonable length limit
            return False
        return bool(cls.SERVICE_NAME_PATTERN.match(service_name))
    
    @classmethod
    def validate_method_name(cls, method_name: str) -> bool:
        """
        Validate method name format
        
        Args:
            method_name: The method name to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not method_name or not isinstance(method_name, str):
            return False
        if len(method_name) > 100:  # Reasonable length limit
            return False
        return bool(cls.METHOD_NAME_PATTERN.match(method_name))
    
    @classmethod
    def validate_path(cls, path: str) -> bool:
        """
        Validate HTTP path format
        
        Args:
            path: The path to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not path or not isinstance(path, str):
            return False
        if len(path) > 500:  # Reasonable path length limit
            return False
        if not path.startswith('/'):
            return False
        return bool(cls.PATH_PATTERN.match(path))
    
    def validate_json_payload(self, payload: str, max_size: Optional[int] = None) -> Dict[str, Any]:
        """
        Validate and parse JSON payload
        
        Args:
            payload: JSON string to validate
            max_size: Maximum payload size in bytes
            
        Returns:
            Parsed JSON data
            
        Raises:
            ValidationError: If payload is invalid
        """
        if not payload:
            raise ValidationError("Empty payload", ["payload"])
        
        # Check size limit
        if max_size is None:
            max_size = self.config.max_message_size
        
        if len(payload.encode('utf-8')) > max_size:
            raise ValidationError(
                f"Payload too large: {len(payload.encode('utf-8'))} bytes > {max_size} bytes",
                ["payload_size"]
            )
        
        try:
            return json.loads(payload)
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON: {str(e)}", ["json_format"])
    
    def validate_request_data(self, data: Dict[str, Any], required_fields: List[str]) -> None:
        """
        Validate request data structure
        
        Args:
            data: Request data to validate
            required_fields: List of required field names
            
        Raises:
            ValidationError: If validation fails
        """
        if not isinstance(data, dict):
            raise ValidationError("Request data must be a dictionary", ["data_type"])
        
        missing_fields = []
        for field in required_fields:
            if field not in data:
                missing_fields.append(field)
        
        if missing_fields:
            raise ValidationError(
                f"Missing required fields: {', '.join(missing_fields)}",
                missing_fields
            )
    
    def sanitize_error_message(self, message: str) -> str:
        """
        Sanitize error message by removing sensitive information
        
        Args:
            message: Original error message
            
        Returns:
            Sanitized error message
        """
        if not self.config.sanitize_error_messages:
            return message
        
        # Remove file paths
        message = self.FILE_PATH_PATTERN.sub('<file>', message)
        
        # Remove line numbers
        message = self.LINE_NUMBER_PATTERN.sub('line <num>', message)
        
        # Remove stack trace information
        lines = message.split('\n')
        sanitized_lines = []
        skip_next = False
        
        for line in lines:
            if skip_next:
                skip_next = False
                continue
                
            # Skip common stack trace patterns
            if any(pattern in line.lower() for pattern in [
                'traceback', 'file "', 'line ', 'in <module>',
                'raise ', 'error:', 'exception:'
            ]):
                continue
                
            # Limit line length
            if len(line) > self.config.max_error_message_length:
                line = line[:self.config.max_error_message_length] + "..."
                
            sanitized_lines.append(line)
        
        sanitized_message = '\n'.join(sanitized_lines).strip()
        
        # Final length check
        if len(sanitized_message) > self.config.max_error_message_length:
            sanitized_message = sanitized_message[:self.config.max_error_message_length] + "..."
        
        return sanitized_message or "An error occurred"
    
    def validate_websocket_message(self, message: str) -> Dict[str, Any]:
        """
        Validate WebSocket message format
        
        Args:
            message: WebSocket message to validate
            
        Returns:
            Parsed message data
            
        Raises:
            ValidationError: If message is invalid
        """
        if not message or not message.strip():
            raise ValidationError("Empty WebSocket message", ["message"])
        
        try:
            data = json.loads(message)
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON in WebSocket message: {str(e)}", ["json_format"])
        
        if not isinstance(data, dict):
            raise ValidationError("WebSocket message must be a JSON object", ["message_type"])
        
        return data
    
    def check_rate_limit(self, client_id: str, requests_per_minute: int = 60) -> bool:
        """
        Simple rate limiting check (in-memory, for demo purposes)
        
        Args:
            client_id: Client identifier
            requests_per_minute: Maximum requests per minute
            
        Returns:
            True if request is allowed, False if rate limited
        """
        # This is a simplified implementation
        # In production, you'd use Redis or another persistent store
        # For now, we'll just return True (no rate limiting)
        return True
    
    def validate_grpc_metadata(self, metadata: Dict[str, str]) -> Dict[str, str]:
        """
        Validate gRPC metadata
        
        Args:
            metadata: gRPC metadata dictionary
            
        Returns:
            Validated metadata
            
        Raises:
            ValidationError: If metadata is invalid
        """
        if not isinstance(metadata, dict):
            raise ValidationError("Metadata must be a dictionary", ["metadata_type"])
        
        validated_metadata = {}
        
        for key, value in metadata.items():
            # Validate key format
            if not isinstance(key, str) or not key:
                raise ValidationError(f"Invalid metadata key: {key}", ["metadata_key"])
            
            # Validate value format
            if not isinstance(value, str):
                raise ValidationError(f"Invalid metadata value for key {key}", ["metadata_value"])
            
            # Check for suspicious patterns
            if any(suspicious in key.lower() for suspicious in ['password', 'secret', 'token']):
                raise SecurityError(f"Suspicious metadata key: {key}", "metadata_security")
            
            validated_metadata[key] = value
        
        return validated_metadata


# Global validator instance
_validator: Optional[InputValidator] = None


def get_validator() -> InputValidator:
    """Get the global input validator instance"""
    global _validator
    if _validator is None:
        _validator = InputValidator()
    return _validator

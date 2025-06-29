"""
Configuration management for the gRPC FastAPI Gateway
"""
import os
from typing import Optional, Dict, Any
from pydantic import field_validator, Field
from pydantic_settings import BaseSettings
from .exceptions import ConfigurationError


class GatewayConfig(BaseSettings):
    """Gateway configuration with validation"""

    # Basic settings
    debug: bool = Field(False, description="Enable debug mode")
    log_level: str = Field("INFO", description="Logging level")

    # Performance settings
    max_message_size: int = Field(
        4 * 1024 * 1024,
        description="Maximum message size in bytes (4MB default)"
    )
    websocket_timeout: int = Field(
        300,
        description="WebSocket timeout in seconds"
    )
    request_timeout: int = Field(
        30,
        description="Request timeout in seconds"
    )
    max_concurrent_connections: int = Field(
        1000,
        description="Maximum concurrent connections"
    )

    # Cache settings
    enable_class_cache: bool = Field(
        True,
        description="Enable class loading cache"
    )
    class_cache_size: int = Field(
        128,
        description="Maximum number of cached classes"
    )

    # Monitoring settings
    enable_metrics: bool = Field(
        True,
        description="Enable Prometheus metrics"
    )
    metrics_path: str = Field(
        "/metrics",
        description="Metrics endpoint path"
    )

    # Security settings
    enable_input_validation: bool = Field(
        True,
        description="Enable input validation"
    )
    sanitize_error_messages: bool = Field(
        True,
        description="Sanitize error messages in production"
    )
    max_error_message_length: int = Field(
        500,
        description="Maximum error message length"
    )

    # gRPC settings
    grpc_compression: Optional[str] = Field(
        "gzip",
        description="gRPC compression algorithm"
    )

    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v):
        """Validate log level"""
        valid_levels = {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}
        if v.upper() not in valid_levels:
            raise ConfigurationError(
                f'Invalid log level: {v}. Must be one of {valid_levels}',
                "log_level"
            )
        return v.upper()

    @field_validator('max_message_size')
    @classmethod
    def validate_max_message_size(cls, v):
        """Validate max message size"""
        if v <= 0 or v > 100 * 1024 * 1024:  # 100MB limit
            raise ConfigurationError(
                'max_message_size must be between 1 byte and 100MB',
                "max_message_size"
            )
        return v

    @field_validator('websocket_timeout')
    @classmethod
    def validate_websocket_timeout(cls, v):
        """Validate WebSocket timeout"""
        if v <= 0 or v > 3600:  # 1 hour limit
            raise ConfigurationError(
                'websocket_timeout must be between 1 and 3600 seconds',
                "websocket_timeout"
            )
        return v

    @field_validator('request_timeout')
    @classmethod
    def validate_request_timeout(cls, v):
        """Validate request timeout"""
        if v <= 0 or v > 300:  # 5 minutes limit
            raise ConfigurationError(
                'request_timeout must be between 1 and 300 seconds',
                "request_timeout"
            )
        return v

    @field_validator('max_concurrent_connections')
    @classmethod
    def validate_max_concurrent_connections(cls, v):
        """Validate max concurrent connections"""
        if v <= 0 or v > 10000:
            raise ConfigurationError(
                'max_concurrent_connections must be between 1 and 10000',
                "max_concurrent_connections"
            )
        return v

    @field_validator('class_cache_size')
    @classmethod
    def validate_class_cache_size(cls, v):
        """Validate class cache size"""
        if v <= 0 or v > 1000:
            raise ConfigurationError(
                'class_cache_size must be between 1 and 1000',
                "class_cache_size"
            )
        return v

    @field_validator('grpc_compression')
    @classmethod
    def validate_grpc_compression(cls, v):
        """Validate gRPC compression"""
        if v is not None:
            valid_compression = {'gzip', 'deflate', None}
            if v not in valid_compression:
                raise ConfigurationError(
                    f'Invalid gRPC compression: {v}. Must be one of {valid_compression}',
                    "grpc_compression"
                )
        return v

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return self.dict()

    @classmethod
    def from_env(cls) -> 'GatewayConfig':
        """Create config from environment variables"""
        return cls()

    @classmethod
    def from_file(cls, config_file: str) -> 'GatewayConfig':
        """Create config from file"""
        if not os.path.exists(config_file):
            raise ConfigurationError(f"Config file {config_file} not found")

        # Support for different file formats
        if config_file.endswith('.json'):
            import json
            with open(config_file, 'r') as f:
                data = json.load(f)
        elif config_file.endswith('.yaml') or config_file.endswith('.yml'):
            try:
                import yaml
                with open(config_file, 'r') as f:
                    data = yaml.safe_load(f)
            except ImportError:
                raise ConfigurationError(
                    "PyYAML not installed, cannot load YAML config")
        else:
            raise ConfigurationError(
                f"Unsupported config file format: {config_file}")

        return cls(**data)

    class Config:
        env_prefix = "GATEWAY_"
        env_file = ".env"
        case_sensitive = False


# Global config instance
_config: Optional[GatewayConfig] = None


def get_config() -> GatewayConfig:
    """Get the global configuration instance"""
    global _config
    if _config is None:
        _config = GatewayConfig.from_env()
    return _config


def set_config(config: GatewayConfig) -> None:
    """Set the global configuration instance"""
    global _config
    _config = config


def reset_config() -> None:
    """Reset the global configuration instance"""
    global _config
    _config = None

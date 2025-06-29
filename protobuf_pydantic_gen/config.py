"""
Configuration management for protobuf pydantic generator
"""

import os
import sys
import logging
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from .constants import VALID_LOG_LEVELS


class GeneratorConfig(BaseModel):
    """Configuration for the protobuf to pydantic generator"""

    # Logging configuration
    log_level: str = Field("INFO", description="Logging level")
    log_to_stderr: bool = Field(True, description="Log to stderr")

    # Output configuration
    max_line_length: int = Field(
        120, description="Maximum line length for formatting")
    autopep8_aggressive: int = Field(
        5, description="Autopep8 aggressive level")

    # Code generation options
    generate_sqlmodel: bool = Field(
        False, description="Generate SQLModel classes")
    skip_google_types: bool = Field(
        True, description="Skip Google protobuf types")
    add_table_args: bool = Field(
        True, description="Add table args for SQLModel")

    # Template configuration
    template_file: str = Field(
        "template.j2", description="Template file to use")

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level"""
        if v.upper() not in VALID_LOG_LEVELS:
            raise ValueError(
                f"Invalid log level: {v}. Must be one of {VALID_LOG_LEVELS}"
            )
        return v.upper()

    @field_validator("max_line_length")
    @classmethod
    def validate_max_line_length(cls, v: int) -> int:
        """Validate max line length"""
        if v < 50 or v > 200:
            raise ValueError("max_line_length must be between 50 and 200")
        return v

    @field_validator("autopep8_aggressive")
    @classmethod
    def validate_autopep8_aggressive(cls, v: int) -> int:
        """Validate autopep8 aggressive level"""
        if v < 0 or v > 10:
            raise ValueError("autopep8_aggressive must be between 0 and 10")
        return v

    def setup_logging(self) -> None:
        """Setup logging configuration"""
        logging.basicConfig(
            stream=sys.stderr if self.log_to_stderr else None,
            level=getattr(logging, self.log_level),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

    @classmethod
    def from_env(cls) -> "GeneratorConfig":
        """Create config from environment variables"""
        return cls(
            log_level=os.getenv("PROTOBUF_PYDANTIC_LOG_LEVEL", "INFO"),
            max_line_length=int(
                os.getenv("PROTOBUF_PYDANTIC_MAX_LINE_LENGTH", "120")),
            generate_sqlmodel=os.getenv(
                "PROTOBUF_PYDANTIC_SQLMODEL", "false").lower()
            == "true",
            skip_google_types=os.getenv(
                "PROTOBUF_PYDANTIC_SKIP_GOOGLE", "true").lower()
            == "true",
        )


# Global config instance
_config: Optional[GeneratorConfig] = None


def get_config() -> GeneratorConfig:
    """Get the global configuration instance"""
    global _config
    if _config is None:
        _config = GeneratorConfig.from_env()
        _config.setup_logging()
    return _config


def set_config(config: GeneratorConfig) -> None:
    """Set the global configuration instance"""
    global _config
    _config = config
    config.setup_logging()

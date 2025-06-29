"""
Template rendering utilities
"""

import os
import sys
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import List
from jinja2 import FileSystemLoader, Environment
from .models import Message
from .config import get_config

logger = logging.getLogger(__name__)


def get_ruff_path() -> str:
    """Get the path to ruff based on the current Python interpreter's bin directory."""
    # Get the directory where the Python interpreter is located
    python_path = Path(sys.executable)
    bin_dir = python_path.parent

    # Try to find ruff in the same bin directory as the Python interpreter
    ruff_path = bin_dir / "ruff"
    if ruff_path.exists():
        return str(ruff_path)

    # Fallback to system ruff if not found
    return "ruff"


class TemplateRenderer:
    """Handles Jinja2 template rendering"""

    def __init__(self, template_dir: str = None):
        """
        Initialize template renderer

        Args:
            template_dir: Directory containing templates (defaults to current package dir)
        """
        if template_dir is None:
            template_dir = os.path.dirname(__file__)

        self.template_dir = template_dir
        self.config = get_config()

        # Setup Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(template_dir), trim_blocks=True, lstrip_blocks=True
        )

    def render_code(
        self,
        filename: str,
        messages: List[Message],
        enums: List[Message],
        imports: List[str],
    ) -> str:
        """
        Render Python code from template

        Args:
            filename: Base filename for the generated code
            messages: List of message definitions
            enums: List of enum definitions
            imports: List of import statements

        Returns:
            Rendered Python code
        """
        try:
            template = self.env.get_template(self.config.template_file)

            # Add current datetime for template
            import datetime

            current_datetime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            rendered = template.render(
                name=filename,
                messages=messages,
                enums=enums,
                imports=imports,
                datetime=current_datetime,
                config=self.config,
            )

            return rendered

        except Exception as e:
            logger.error(f"Error rendering template for {filename}: {e}")
            raise

    def format_with_ruff(self, code: str) -> str:
        ruff_cmd = get_ruff_path()
        with tempfile.NamedTemporaryFile("w+", suffix=".py", delete=False) as tmp:
            tmp.write(code)
            tmp.flush()
            tmp_name = tmp.name

            try:
                # First, fix linting issues (remove unused imports, sort imports, etc.)
                subprocess.run(
                    [ruff_cmd, "check", "--fix", "--unsafe-fixes", tmp_name],
                    check=False,  # Don't fail if there are unfixable issues
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

                # Then format the code
                subprocess.run(
                    [ruff_cmd, "format", tmp_name],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

                with open(tmp_name, "r") as f:
                    formatted = f.read()
                return formatted
            except Exception as e:
                logger.warning(f"ruff format failed: {e}")
                return code
            finally:
                import os

                os.remove(tmp_name)

    def format_code(self, code: str) -> str:
        """
        Format generated code using autopep8

        Args:
            code: Raw generated code

        Returns:
            Formatted code
        """
        try:
            import autopep8

            options = {
                "max_line_length": self.config.max_line_length,
                "in_place": True,
                "aggressive": self.config.autopep8_aggressive,
            }

            formatted = autopep8.fix_code(code, options=options)
            return formatted

        except ImportError:
            logger.warning("autopep8 not available, skipping code formatting")
            return code
        except Exception as e:
            logger.error(f"Error formatting code: {e}")
            return code

    def render_and_format(
        self,
        filename: str,
        messages: List[Message],
        enums: List[Message],
        imports: List[str],
    ) -> str:
        """
        Render and format code in one step

        Args:
            filename: Base filename
            messages: Message definitions
            enums: Enum definitions
            imports: Import statements

        Returns:
            Rendered and formatted code
        """
        raw_code = self.render_code(filename, messages, enums, imports)
        return self.format_with_ruff(raw_code)

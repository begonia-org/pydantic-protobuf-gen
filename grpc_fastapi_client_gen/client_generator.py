"""
Jinja2-based client code generator
"""

import json
import ast
import logging
from pathlib import Path
import subprocess
import tempfile
from typing import Dict, Any, Set
from jinja2 import Environment, FileSystemLoader


def to_snake_case(name: str) -> str:
    """Convert CamelCase or PascalCase to snake_case, handling consecutive uppercase letters correctly."""
    import re

    # Replace transitions from lower-to-upper or digit-to-upper with _
    s1 = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
    # Replace transitions from uppercase followed by uppercase+lower (e.g., HTTPRequest -> HTTP_Request)
    s2 = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", s1)
    return s2.lower()


class ClientCodeGenerator:
    """Client code generator"""

    def __init__(self, template_dir: str = None):
        if template_dir is None:
            template_dir = Path(__file__).parent

        self.env = Environment(
            loader=FileSystemLoader(template_dir), trim_blocks=True, lstrip_blocks=True
        )

        # Add custom filters
        self.env.filters["to_snake_case"] = self._to_snake_case

    def _to_snake_case(self, name: str) -> str:
        """Convert to snake_case"""
        return to_snake_case(name)

    def format_with_ruff(self, code: str) -> str:
        with tempfile.NamedTemporaryFile("w+", suffix=".py", delete=False) as tmp:
            tmp.write(code)
            tmp.flush()
            tmp_name = tmp.name
            try:
                subprocess.run(
                    ["ruff", "format", tmp_name],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                subprocess.run(
                    ["ruff", "check", "--select", "F401,I", "--fix", tmp_name],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                # Read formatted code
                with open(tmp_name, "r") as f:
                    formatted = f.read()
                return formatted
            except Exception:
                return code
            finally:
                import os

                os.remove(tmp_name)

    def scan_models_directory(
        self, package_name: str, models_dir: str
    ) -> Dict[str, str]:
        """Scan model directory to get import statements for all BaseModel classes"""
        models_dir = Path(models_dir)
        model_imports = {}

        if not models_dir.exists():
            return model_imports

        for py_file in models_dir.rglob("*.py"):
            if py_file.name.startswith("__"):
                continue

            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()

                tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        # Check if inherits from BaseModel
                        for base in node.bases:
                            is_basemodel = False

                            if isinstance(base, ast.Name) and base.id == "BaseModel":
                                is_basemodel = True
                            elif (
                                isinstance(base, ast.Attribute)
                                and isinstance(base.value, ast.Name)
                                and base.value.id == "pydantic"
                                and base.attr == "BaseModel"
                            ):
                                is_basemodel = True

                            if is_basemodel:
                                import_path = self._calculate_import_path(
                                    py_file, models_dir, package_name
                                )
                                model_imports[node.name] = (
                                    f"from {import_path} import {node.name}"
                                )
                                break

            except Exception as e:
                logging.error(f"Error processing file {py_file}: {e}")
                continue

        return model_imports

    def _calculate_import_path(
        self, py_file: Path, models_dir: Path, package_name: str
    ) -> str:
        """Calculate import path"""
        try:
            relative_path = py_file.relative_to(models_dir)
            module_path_parts = list(relative_path.parts[:-1]) + [relative_path.stem]

            if module_path_parts and module_path_parts != [py_file.stem]:
                sub_module = ".".join(module_path_parts)
                return f"{package_name}.models.{sub_module}"
            else:
                return f"{package_name}.models.{py_file.stem}"

        except ValueError:
            return f".models.{py_file.stem}"

    def parse_services_json(self, services_json_path: str) -> Dict[str, Any]:
        """Parse services.json file"""
        with open(services_json_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def prepare_template_data(
        self,
        services_data: Dict[str, Any],
        model_imports: Dict[str, str],
        class_name: str = "Client",
    ) -> Dict[str, Any]:
        """Prepare template data"""
        # Collect used models
        used_models: Set[str] = set()

        # Process service data
        processed_services = {}

        for service_name, service_info in services_data.items():
            processed_methods = {}

            for method_name, method_info in service_info.items():
                input_type = method_info.get("input_type", "").split(".")[-1]
                output_type = method_info.get("output_type", "").split(".")[-1]
                streaming_type = method_info.get("streaming_type", "unary")
                http_info = method_info.get("http", {})

                used_models.add(input_type)
                used_models.add(output_type)

                snake_name = f"{self._to_snake_case(service_name)}_{self._to_snake_case(method_name)}"

                processed_methods[method_name] = {
                    "snake_name": snake_name,
                    "input_type": input_type,
                    "output_type": output_type,
                    "streaming_type": streaming_type,
                    "http": {
                        "method": http_info.get("method", "POST"),
                        "path": http_info.get("path", ""),
                        "body": http_info.get("body") is not None,
                    },
                }

            processed_services[service_name] = processed_methods

        # Prepare import statements
        import_statements = []
        for model_name in sorted(used_models):
            if model_name and model_name in model_imports:
                import_statements.append(model_imports[model_name])
            elif model_name:
                import_statements.append(f"# {model_name} = Any  # Model not found")

        return {
            "class_name": class_name,
            "services": processed_services,
            "model_imports": import_statements,
            "used_models": list(used_models),
        }

    def generate_client_code(
        self,
        services_json_path: str,
        models_dir: str,
        package_name: str,
        class_name: str = "Client",
        template_name: str = "client.j2",
    ) -> str:
        """Generate client code"""
        # Parse service definitions
        services_data = self.parse_services_json(services_json_path)

        # Scan model directory
        model_imports = self.scan_models_directory(package_name, models_dir)

        # Prepare template data
        template_data = self.prepare_template_data(
            services_data, model_imports, class_name
        )
        # Render template
        template = self.env.get_template(template_name)
        generated_code = template.render(**template_data)
        return self.format_with_ruff(generated_code)


def generate_client_from_services(
    services_json_path: str,
    models_dir: str,
    package_name: str,
    output_path: str,
    class_name: str = "GeneratedClient",
    template_dir: str = None,
) -> str:
    """Convenience function: generate client code from services.json"""
    generator = ClientCodeGenerator(template_dir)
    return generator.generate_client_code(
        services_json_path=services_json_path,
        models_dir=models_dir,
        package_name=package_name,
        output_path=output_path,
        class_name=class_name,
    )


if __name__ == "__main__":
    # Usage example
    generator = ClientCodeGenerator()

    output_file = generator.generate_client_code(
        services_json_path="/app/example/models/services.json",
        models_dir="/app/example/models",
        package_name="example",
        output_path="/app/example/generated_client.py",
        class_name="MyAPIClient",
    )

    print(f"Generated client code: {output_file}")

"""
Main code generator orchestrating the entire process
"""

import os
import sys
import json
import logging
from collections import defaultdict, deque
from contextlib import contextmanager
from typing import Iterator, Tuple, List, Dict, Set
from google.protobuf.compiler import plugin_pb2
from google.protobuf import descriptor_pool

from .constants import CONDITIONAL_IMPORTS, SKIP_FILES, BASE_IMPORTS, __version__
from .config import get_config, GeneratorConfig
from .models import GenerationResult, MessageType, Service
from .type_mapper import TypeMapper, ImportManager
from .message_processor import MessageProcessor
from .service_processor import ServiceProcessor
from .template_renderer import TemplateRenderer

logger = logging.getLogger(__name__)


class CodeGenerator:
    """Main code generator class"""

    def __init__(self, config: GeneratorConfig = None):
        """
        Initialize code generator

        Args:
            config: Generator configuration (uses default if None)
        """
        self.config = config or get_config()
        self.pool = descriptor_pool.DescriptorPool()

        # Initialize processors
        self.type_mapper = TypeMapper(self.pool)
        self.import_manager = ImportManager()
        self.message_processor = MessageProcessor(self.type_mapper)
        self.service_processor = ServiceProcessor()
        self.template_renderer = TemplateRenderer()

    @contextmanager
    def plugin_context(
        self,
    ) -> Iterator[
        Tuple[plugin_pb2.CodeGeneratorRequest, plugin_pb2.CodeGeneratorResponse]
    ]:
        """
        Context manager for protoc plugin processing

        Yields:
            Tuple of (request, response) for protoc plugin
        """
        # Handle version check
        if len(sys.argv) > 1 and sys.argv[1] in ("-V", "--version"):
            print(f"protobuf-pydantic-gen {__version__}")
            sys.exit(0)

        # Read request from stdin
        try:
            data = sys.stdin.buffer.read()
            request = plugin_pb2.CodeGeneratorRequest()
            request.ParseFromString(data)
        except Exception as e:
            logger.error(f"Failed to read protoc request: {e}")
            sys.exit(1)

        # Create response
        response = plugin_pb2.CodeGeneratorResponse()
        response.supported_features |= (
            plugin_pb2.CodeGeneratorResponse.FEATURE_PROTO3_OPTIONAL
        )

        try:
            yield request, response
        finally:
            # Write response to stdout
            try:
                output = response.SerializeToString()
                sys.stdout.buffer.write(output)
            except Exception as e:
                logger.error(f"Failed to write protoc response: {e}")
                sys.exit(1)

    def should_skip_file(self, proto_file) -> bool:
        """Check if file should be skipped"""
        if proto_file.package == "pydantic":
            return True

        for skip_pattern in SKIP_FILES:
            if skip_pattern in proto_file.name:
                return True

        return False

    def load_protos(self, request: plugin_pb2.CodeGeneratorRequest) -> None:
        """
        Load protobuf files into the descriptor pool

        Args:
            request: Protoc plugin request containing proto files
        """
        for proto_file in request.proto_file:
            # if self.should_skip_file(proto_file):
            #     logger.debug(f"Skipping file: {proto_file.name}")
            #     continue

            try:
                self.pool.Add(proto_file)
                logger.debug(f"Added {proto_file.name} to descriptor pool")
            except Exception as e:
                logger.warning(f"Failed to add {proto_file.name} to pool: {e}")

    def process_proto_file(self, proto_file) -> GenerationResult:
        """
        Process a single protobuf file

        Args:
            proto_file: Protobuf file descriptor

        Returns:
            Generation result with code and metadata
        """
        filename = os.path.basename(proto_file.name).split(".")[0]
        logger.debug(f"Processing file: {filename}")

        # Initialize collections
        self.import_manager.clear()
        type_mapping: Dict[str, str] = {}
        imports: Set[str] = set(BASE_IMPORTS)
        imports.add(CONDITIONAL_IMPORTS["typing_base"])
        # Process messages and enums
        messages = self.message_processor.extract_messages_from_file(
            proto_file, imports, type_mapping
        )

        # Separate messages and enums
        actual_messages = [m for m in messages if m.message_type.value == "class"]
        enums = [m for m in messages if m.message_type.value == "enum"]
        # Emit same-file dependencies first where possible so generated code stays
        # readable and static analyzers see fewer forward references.
        actual_messages = self._order_messages_by_dependency(actual_messages)

        # Process services
        services = self.service_processor.extract_services_from_file(
            proto_file
        )  # Add extension imports if needed
        if any(
            hasattr(m, "proto_full_name") and m.proto_full_name for m in actual_messages
        ):
            imports.update(
                [
                    "from protobuf_pydantic_gen.ext import model2protobuf, protobuf2model, pool, GenericEnumType",
                    "from google.protobuf import message_factory",
                ]
            )

        # Check if SQLModel is needed
        if any(hasattr(m, "as_table") and m.as_table for m in actual_messages):
            imports.add("from sqlmodel import SQLModel, Field")

        # Add conditional imports based on field types used
        self._add_conditional_imports(
            filename, actual_messages, imports, proto_file.package
        )

        # Don't add self-imports for type mapping in the same file
        filtered_type_mapping = {
            name: file for name, file in type_mapping.items() if file != filename
        }

        # Add type imports
        self._add_type_imports(filtered_type_mapping, imports)

        # Merge and organize imports
        organized_imports = self._merge_imports(list(imports))

        # Generate code
        code = self.template_renderer.render_and_format(
            filename, actual_messages, enums, organized_imports
        )

        return GenerationResult(
            filename=f"{filename.lower()}_model.py",
            content=code,
            messages=actual_messages,
            services=services,
        )

    def _order_messages_by_dependency(self, messages: List[MessageType]) -> List[MessageType]:
        """Order messages so same-file dependencies are emitted before their consumers.

        Falls back to original relative order for dependency cycles.
        """
        if len(messages) < 2:
            return messages

        message_names = {message.message_name for message in messages}
        original_positions = {
            message.message_name: index for index, message in enumerate(messages)
        }
        dependencies: Dict[str, Set[str]] = {}
        reverse_edges: Dict[str, Set[str]] = defaultdict(set)
        indegree: Dict[str, int] = {message.message_name: 0 for message in messages}

        for message in messages:
            same_file_dependencies = set()
            for field in getattr(message, "fields", []):
                message_info = getattr(field, "message_info", None) or {}
                dependency_name = message_info.get("message", "").split(".")[-1]
                if (
                    dependency_name
                    and dependency_name in message_names
                    and dependency_name != message.message_name
                ):
                    # Only order against types emitted into this file; cross-file
                    # dependencies are handled by normal imports instead.
                    same_file_dependencies.add(dependency_name)
            dependencies[message.message_name] = same_file_dependencies
            indegree[message.message_name] = len(same_file_dependencies)
            for dependency_name in same_file_dependencies:
                reverse_edges[dependency_name].add(message.message_name)

        ready = deque(
            sorted(
                (
                    message_name
                    for message_name, degree in indegree.items()
                    if degree == 0
                ),
                key=lambda name: original_positions[name],
            )
        )
        ordered_names: List[str] = []

        while ready:
            message_name = ready.popleft()
            ordered_names.append(message_name)
            for dependent_name in sorted(
                reverse_edges.get(message_name, set()),
                key=lambda name: original_positions[name],
            ):
                indegree[dependent_name] -= 1
                if indegree[dependent_name] == 0:
                    ready.append(dependent_name)

        if len(ordered_names) != len(messages):
            # Cycles still need forward references in the template, so preserve
            # source order for the unresolved remainder instead of guessing.
            remaining_names = sorted(
                (
                    message.message_name
                    for message in messages
                    if message.message_name not in ordered_names
                ),
                key=lambda name: original_positions[name],
            )
            ordered_names.extend(remaining_names)

        message_map = {message.message_name: message for message in messages}
        return [message_map[name] for name in ordered_names]

    def set_python_type_value(self, type_str: str, ext: dict):
        if type_str == "str":
            if "example" in ext:
                ext["example"] = f'"{ext["example"]}"'
        if "description" in ext:
            ext["description"] = f'"{ext["description"]}"'
        if "alias" in ext:
            ext["alias"] = f'"{ext["alias"]}"'
        return ext

    def _add_conditional_imports(
        self,
        current_file: str,
        messages: List,
        imports: Set[str],
        current_package: str = "",
    ) -> None:
        """Add imports based on field types used in messages

        Args:
            current_file: Current proto file name (without extension)
            messages: List of messages to process
            imports: Set to collect import statements
            current_package: Current proto file's package name
        """
        from .constants import CONDITIONAL_IMPORTS

        typing_imports = set()
        needs_protobuf = False
        needs_sqlmodel = False
        needs_pydantic = False  # Always need pydantic base

        for message in messages:
            if message.message_type == MessageType.CLASS:
                needs_pydantic = True
            if hasattr(message, "fields"):
                for field in message.fields:
                    field_type = getattr(field, "type", "")
                    # Check for datetime usage
                    if "datetime" in field_type:
                        imports.add(CONDITIONAL_IMPORTS["datetime"])

                    # Check for optional fields
                    if not getattr(field, "required", True):
                        typing_imports.add("Optional")

                    # Check for repeated fields
                    if getattr(field, "repeated", False):
                        typing_imports.add("List")

                    # Check for dict fields
                    if "Dict" in field_type:
                        typing_imports.add("Dict")

                    # Check for any fields
                    if "Any" in field_type:
                        typing_imports.add("Any")
                    if field.message_info:
                        # Add message type to type mapping
                        type_name = field.message_info.get("message", "")
                        file_name = field.message_info.get("file", "")
                        imported_package = field.message_info.get("package", "")

                        # Convert proto file path to Python module path
                        # e.g., "stew/api/v1/context.proto" -> "stew.api.v1.context_model"
                        filename = os.path.basename(file_name).split(".")[0]

                        if (
                            type_name
                            and file_name
                            and not file_name.startswith("google/")
                            and filename != current_file
                        ):
                            cls_name = type_name.split(".")[-1]
                            # Also import the GenericEnumType instance for enum types
                            import_names = [cls_name]
                            if cls_name in self.message_processor._enum_type_names:
                                import_names.append(f"{cls_name}Type")
                                import_names.append(f"{cls_name}NameType")
                            import_str = ", ".join(import_names)

                            # Check if packages are different
                            # Use absolute import for different packages (like google.protobuf)
                            # Use relative import for same package
                            if (
                                imported_package
                                and current_package
                                and imported_package != current_package
                            ):
                                # Different package - use absolute import
                                # e.g., "stew/api/v1/context.proto" -> "from stew.api.v1.context_model import ..."
                                module_path = file_name.replace(
                                    ".proto", "_model"
                                ).replace("/", ".")
                                imports.add(f"from {module_path} import {import_str}")
                            else:
                                # Same package or no package info - use relative import
                                imports.add(f"from .{filename}_model import {import_str}")

            # Check if message uses SQLModel
            if hasattr(message, "as_table") and message.as_table:
                needs_sqlmodel = True

            # Check if message has protobuf methods
            if hasattr(message, "proto_full_name") and message.proto_full_name:
                needs_protobuf = True

        # Add typing imports
        if typing_imports:
            typing_imports.add("Type")  # Always need Type for methods
            typing_str = ", ".join(sorted(typing_imports))
            imports.add(f"from typing import {typing_str}")

        # Add base model imports
        if needs_pydantic:
            imports.add(CONDITIONAL_IMPORTS["pydantic_base"])
            imports.add(CONDITIONAL_IMPORTS["pydantic_field"])

        # Add SQLModel if needed
        if needs_sqlmodel:
            imports.add(CONDITIONAL_IMPORTS["sqlmodel"])

        # Add protobuf imports if needed
        if needs_protobuf:
            imports.add(CONDITIONAL_IMPORTS["protobuf_message"])
            imports.add(CONDITIONAL_IMPORTS["protobuf_factory"])
            imports.add(CONDITIONAL_IMPORTS["ext_functions"])

        # Add enum import if there are enums
        # This will be handled in the template rendering

    def _add_type_imports(
        self, type_mapping: Dict[str, str], imports: Set[str]
    ) -> None:
        """Add imports for external types"""
        for type_name, file_name in type_mapping.items():
            if file_name != "current_file":  # Avoid self-imports
                import_names = [type_name]
                # Also import the GenericEnumType instance for enum types
                if type_name in self.message_processor._enum_type_names:
                    import_names.append(f"{type_name}Type")
                    import_names.append(f"{type_name}NameType")
                imports.add(f"from .{file_name.lower()}_model import {', '.join(import_names)}")

    def _merge_imports(self, import_lines: List[str]) -> List[str]:
        """
        Merge and organize import lines into a single list
        """
        from collections import defaultdict

        from_imports = defaultdict(set)
        direct_imports = set()

        for line in import_lines:
            if not line or not line.strip():
                continue

            line = line.strip()
            if line.startswith("from ") and " import " in line:
                parts = line.split(" import ")
                from_part = parts[0][5:].strip()  # remove 'from ' prefix
                # Split imports by comma and strip whitespace
                imports_list = [item.strip() for item in parts[1].split(",")]
                from_imports[from_part].update(imports_list)
            elif line.startswith("import "):
                imports_list = [item.strip() for item in line[7:].split(",")]
                direct_imports.update(imports_list)

        # Build merged imports
        merged_imports = []

        for module in sorted(direct_imports):
            merged_imports.append(f"import {module}")

        for from_part, import_set in sorted(from_imports.items()):
            import_items = ", ".join(sorted(import_set))
            merged_imports.append(f"from {from_part} import {import_items}")

        return merged_imports

    def process_request(self, request: plugin_pb2.CodeGeneratorRequest):
        results: List[GenerationResult] = []
        self.load_protos(request)
        self.type_mapper = TypeMapper(self.pool)
        self.message_processor = MessageProcessor(self.type_mapper)
        for proto_file in request.proto_file:
            # Skip files that shouldn't be processed
            if self.should_skip_file(proto_file):
                logger.debug(f"Skipping file: {proto_file.name}")
                continue
            try:
                result = self.process_proto_file(proto_file)
                results.append(result)
                # Add generated file to response
                # response.file.add(
                #     name=result.filename,
                #     content=result.content
                # )
                # # Collect all messages and services
                # all_messages.extend(result.messages)
                # all_services.extend(result.services)
                # logger.debug(f"Generated: {result.filename}")
            except Exception as e:
                logger.error(f"Error processing file {proto_file.name}: {e}")
                continue
        return results

    def generate_code(
        self,
        request: plugin_pb2.CodeGeneratorRequest,
        response: plugin_pb2.CodeGeneratorResponse,
    ) -> None:
        """
        Main code generation entry point

        Args:
            request: Protoc plugin request
            response: Protoc plugin response to populate
        """
        all_messages = []
        all_services: List[Service] = []
        results = self.process_request(request)
        for result in results:
            response.file.add(name=result.filename, content=result.content)
            all_messages.extend(result.messages)
            all_services.extend(result.services)
            logger.debug(f"Generated: {result.filename}")
        self._generate_metadata_files(response, all_messages, all_services)
        if self.config.generate_tables_py:
            self._generate_tables_file(response, all_messages)

    def _generate_metadata_files(
        self,
        response: plugin_pb2.CodeGeneratorResponse,
        all_messages: List,
        all_services: List,
    ) -> None:
        """Generate JSON metadata files"""
        try:
            # Generate messages metadata
            messages_json, fields_json = self.message_processor.messages_to_metadata(
                all_messages
            )

            response.file.add(name="messages.json", content=messages_json)

            response.file.add(name="fields.json", content=fields_json)

            # Generate services metadata
            services_dict = self.service_processor.services_to_dict(all_services)
            services_json = json.dumps(services_dict, indent=4, ensure_ascii=False)

            response.file.add(name="services.json", content=services_json)

            logger.info(
                "Generated metadata files: messages.json, fields.json, services.json"
            )

        except Exception as e:
            logger.error(f"Error generating metadata files: {e}")

    def _generate_tables_file(
        self,
        response: plugin_pb2.CodeGeneratorResponse,
        all_messages: List,
    ) -> None:
        """Generate tables.py anti-corruption layer for table models.

        Produces a single file that re-exports all SQLModel table classes
        with a configurable alias suffix, isolating business code from
        generated model paths.
        """
        table_messages = [
            m for m in all_messages
            if getattr(m, "as_table", False) and m.message_type == MessageType.CLASS
        ]

        if not table_messages:
            logger.debug("No table models found, skipping tables.py generation")
            return

        suffix = self.config.table_alias_suffix
        lines = [
            '"""',
            "Auto-generated anti-corruption layer for ORM table models.",
            "",
            "Business code should import table classes from this module",
            "instead of referencing generated model files directly.",
            "",
            "DO NOT EDIT — regenerated by protoc-gen-pydantic.",
            '"""',
            "",
        ]

        # Group by source file for cleaner output
        from collections import defaultdict
        file_groups: Dict[str, List] = defaultdict(list)
        for msg in table_messages:
            # msg.proto_file is the basename without extension (e.g. "example")
            module_name = f"{msg.proto_file.lower()}_model"
            file_groups[module_name].append(msg.message_name)

        for module_name in sorted(file_groups.keys()):
            class_names = sorted(file_groups[module_name])
            for class_name in class_names:
                alias = f"{class_name}{suffix}"
                lines.append(
                    f"from .{module_name} import {class_name} as {alias}  # noqa: F401"
                )

        # Add __all__ for explicit public API
        lines.append("")
        all_aliases = sorted(
            f"{msg.message_name}{suffix}" for msg in table_messages
        )
        lines.append("__all__ = [")
        for alias in all_aliases:
            lines.append(f'    "{alias}",')
        lines.append("]")
        lines.append("")

        content = "\n".join(lines)
        response.file.add(name="tables.py", content=content)
        logger.info(
            f"Generated tables.py with {len(table_messages)} table model(s)"
        )


def main():
    """Main entry point for the protoc plugin"""
    config = get_config()
    generator = CodeGenerator(config)

    with generator.plugin_context() as (request, response):
        generator.generate_code(request, response)


if __name__ == "__main__":
    main()

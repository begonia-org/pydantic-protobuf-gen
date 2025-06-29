"""
Type mapping and conversion utilities
"""
import json
import logging
from typing import Dict, List, Set, Optional, Tuple, Any
from google.protobuf import descriptor_pb2, descriptor_pool
from .constants import FIELD_TYPE_MAPPING, SPECIAL_PROTOBUF_TYPES, DEFAULT_VALUES

logger = logging.getLogger(__name__)


class TypeMapper:
    """Handles type mapping from protobuf to Python types"""

    def __init__(self, descriptor_pool: descriptor_pool.DescriptorPool):
        self.pool = descriptor_pool

    def get_message_info(self, field: descriptor_pb2.FieldDescriptorProto) -> Dict[str, Any]:
        """
        Get message information for a field

        Args:
            field: Protobuf field descriptor

        Returns:
            Dictionary with message information
        """
        if field.type in [descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE,
                          descriptor_pb2.FieldDescriptorProto.TYPE_ENUM]:

            if self._is_map_field(field):
                return {}
            type_name = field.type_name
            if type_name.startswith('.'):
                type_name = type_name[1:]
            if field.type == descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE:
                desc = self.pool.FindMessageTypeByName(type_name)
            if field.type == descriptor_pb2.FieldDescriptorProto.TYPE_ENUM:
                desc = self.pool.FindEnumTypeByName(type_name)
            file_name: str = desc.file.name
            return {
                "message": type_name,
                "file": file_name.removesuffix(".proto"),  # 添加文件名
            }
        return {}

    def get_field_type(
        self,
        field: descriptor_pb2.FieldDescriptorProto,
        imports: Set[str],
        type_mapping: Dict[str, str],
        file_name: str
    ) -> str:
        """
        Convert protobuf field type to Python type

        Args:
            field: Protobuf field descriptor
            imports: Set to add required imports
            type_mapping: Mapping of type names to file names
            file_name: Current file name

        Returns:
            Python type string
        """
        # Handle special Google protobuf types
        if hasattr(field, "type_name") and field.type_name in SPECIAL_PROTOBUF_TYPES:
            return SPECIAL_PROTOBUF_TYPES[field.type_name]

        # Handle message types
        if (hasattr(field, "type_name") and
                field.type == descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE):

            # Check if it's a map field
            if self._is_map_field(field):
                key_type, value_type = self._get_map_field_types(
                    field, imports, type_mapping, file_name)
                if key_type and value_type:
                    imports.add("Dict")
                    return f"Dict[{key_type}, {value_type}]"

            # Regular message type
            type_name = field.type_name.split(".")[-1]
            type_mapping[type_name] = file_name
            return type_name

        # Handle enum types
        if field.type == descriptor_pb2.FieldDescriptorProto.TYPE_ENUM:
            type_name = field.type_name.split(".")[-1]
            type_mapping[type_name] = file_name
            return type_name
        return FIELD_TYPE_MAPPING.get(field.type, "Any")

    def _is_map_field(self, field: descriptor_pb2.FieldDescriptorProto) -> bool:
        """Check if field is a map type"""
        return (
            field.label == descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED and
            field.type == descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE and
            field.type_name.endswith("Entry")
        )

    def _get_map_field_types(
        self,
        field: descriptor_pb2.FieldDescriptorProto,
        imports: Set[str],
        type_mapping: Dict[str, str],
        file_name: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """Get key and value types for map fields"""
        try:
            type_name = field.type_name
            if type_name.startswith("."):
                type_name = type_name[1:]

            message_descriptor = self.pool.FindMessageTypeByName(type_name)
            key_type = None
            value_type = None

            for nested_field in message_descriptor.fields:
                if nested_field.name == "key":
                    key_type = self.get_field_type(
                        nested_field, imports, type_mapping, file_name)
                elif nested_field.name == "value":
                    value_type = self.get_field_type(
                        nested_field, imports, type_mapping, file_name)

            return key_type, value_type
        except Exception as e:
            logger.error(f"Error getting map field types: {e}")
            return None, None

    def set_default_value(
        self,
        type_str: str,
        ext: Dict[str, Any],
        field_descriptor: descriptor_pb2.FieldDescriptorProto
    ) -> Dict[str, Any]:
        """Set default value based on type and extensions"""
        if "default" in ext:
            # Handle existing default value
            if type_str == "str":
                # Remove extra quotes and re-quote properly
                value = str(ext["default"]).strip('"\'')
                ext["default"] = f'"{value}"'
            elif type_str.startswith("Dict") or type_str.startswith("List"):
                try:
                    if isinstance(ext["default"], str):
                        ext["default"] = json.loads(ext["default"])
                except (json.JSONDecodeError, TypeError):
                    logger.warning(
                        f"Failed to parse default value as JSON: {ext['default']}")
                    ext["default"] = None
        else:
            # Set type-appropriate default
            if type_str in DEFAULT_VALUES:
                ext["default"] = DEFAULT_VALUES[type_str]
            elif field_descriptor.type == descriptor_pb2.FieldDescriptorProto.TYPE_ENUM:
                enum_type_name = field_descriptor.type_name.split('.')[-1]
                ext["default"] = f"{enum_type_name}(0)"
            else:
                ext["default"] = None

        return ext

    def sanitize_python_values(self, type_str: str, ext: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize extension values for Python code generation"""
        for key in ["example", "description", "alias"]:
            if key in ext and isinstance(ext[key], str):
                ext[key] = f'"{ext[key]}"'
        return ext


class ImportManager:
    """Manages imports for generated code"""

    def __init__(self):
        self.imports: Set[str] = set()

    def add_import(self, import_statement: str) -> None:
        """Add an import statement"""
        if import_statement.strip():
            self.imports.add(import_statement.strip())

    def add_imports(self, import_statements: List[str]) -> None:
        """Add multiple import statements"""
        for stmt in import_statements:
            self.add_import(stmt)

    def merge_imports(self) -> List[str]:
        """
        Merge and organize import statements
        Combines 'from ... import ...' statements from the same module
        """
        from collections import defaultdict

        from_imports = defaultdict(set)
        direct_imports = set()

        for line in self.imports:
            line = line.strip()
            if not line:
                continue

            if line.startswith("from ") and " import " in line:
                # Handle 'from ... import ...'
                parts = line.split(" import ", 1)
                from_part = parts[0][5:].strip()  # Remove 'from '
                imports_list = [item.strip() for item in parts[1].split(",")]
                from_imports[from_part].update(imports_list)
            elif line.startswith("import "):
                # Handle 'import ...'
                imports_list = [item.strip() for item in line[7:].split(",")]
                direct_imports.update(imports_list)

        # Build merged imports
        merged_imports = []

        # Add direct imports (each on separate line)
        for module in sorted(direct_imports):
            merged_imports.append(f"import {module}")

        # Add from imports
        for from_part, import_set in sorted(from_imports.items()):
            import_items = ", ".join(sorted(import_set))
            merged_imports.append(f"from {from_part} import {import_items}")

        return merged_imports

    def clear(self) -> None:
        """Clear all imports"""
        self.imports.clear()

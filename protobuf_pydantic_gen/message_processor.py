"""
Message and enum processing utilities
"""

import ast
import json
import logging
from typing import List, Dict, Set, Any
from google.protobuf import descriptor_pb2
from google.protobuf.json_format import MessageToDict
from . import pydantic_pb2
from .models import Message, Field, EnumField, MessageType
from .type_mapper import TypeMapper
from .config import get_config

logger = logging.getLogger(__name__)


class MessageProcessor:
    """Processes protobuf messages and enums"""

    def __init__(self, type_mapper: TypeMapper):
        self.type_mapper = type_mapper
        self.config = get_config()

    def extract_messages_from_file(
        self,
        proto_file: descriptor_pb2.FileDescriptorProto,
        imports: Set[str],
        type_mapping: Dict[str, str],
    ) -> List[Message]:
        """
        Extract all messages and enums from a protobuf file

        Args:
            proto_file: Protobuf file descriptor
            imports: Set to collect required imports
            type_mapping: Mapping of type names to file names

        Returns:
            List of extracted messages and enums
        """
        filename = self._get_filename(proto_file.name)
        messages = []

        # Process enums
        for enum_desc in proto_file.enum_type:
            try:
                enum_message = self._process_enum(enum_desc, filename, type_mapping)
                messages.append(enum_message)
                imports.add("from enum import Enum as _Enum")
            except Exception as e:
                logger.error(f"Error processing enum {enum_desc.name}: {e}")
                continue

        # Process messages
        for message_desc in proto_file.message_type:
            try:
                message = self._process_message(
                    message_desc, filename, imports, type_mapping, proto_file.package
                )
                messages.append(message)
            except Exception as e:
                logger.error(f"Error processing message {message_desc.name}: {e}")
                continue

        return messages

    def _get_filename(self, proto_name: str) -> str:
        """Extract filename from proto file name"""
        import os

        return os.path.basename(proto_name).split(".")[0]

    def _process_enum(
        self,
        enum_desc: descriptor_pb2.EnumDescriptorProto,
        filename: str,
        type_mapping: Dict[str, str],
    ) -> Message:
        """Process a protobuf enum"""
        type_mapping[enum_desc.name] = filename
        fields = []

        for value_desc in enum_desc.value:
            enum_field = EnumField(name=value_desc.name, value=str(value_desc.number))
            # Convert EnumField to Field for consistency
            field = Field(
                name=enum_field.name,
                type="Enum",  # Not used for enums
                repeated=False,
                required=False,
                attributes={},
                ext={"value": enum_field.value},
            )
            fields.append(field)

        return Message(
            message_name=enum_desc.name, fields=fields, message_type=MessageType.ENUM
        )

    def _process_message(
        self,
        message_desc: descriptor_pb2.DescriptorProto,
        filename: str,
        imports: Set[str],
        type_mapping: Dict[str, str],
        package: str,
    ) -> Message:
        """Process a protobuf message"""
        type_mapping[message_desc.name] = filename
        fields = []

        # Get message-level extensions
        message_ext = self._extract_message_extensions(message_desc)

        # Process fields
        for field_desc in message_desc.field:
            try:
                field = self._process_field(
                    field_desc, message_desc, filename, imports, type_mapping
                )
                fields.append(field)
            except Exception as e:
                logger.error(f"Error processing field {field_desc.name}: {e}")
                continue

        # Add required imports
        imports.add("Type")
        imports.add("from google.protobuf import message as _message")

        # Build full proto name
        proto_full_name = (
            f"{package}.{message_desc.name}" if package else message_desc.name
        )

        # Create message
        message = Message(
            message_name=message_desc.name,
            fields=fields,
            message_type=MessageType.CLASS,
            proto_full_name=proto_full_name,
            proto_file=filename,
            ext=message_ext,
        )

        # Apply message-level configuration
        self._apply_message_extensions(message, message_ext, imports)

        return message

    def _is_JSON_field(self, field: Field) -> bool:
        # Check for repeated fields
        if getattr(field, "repeated", False):
            return True
        if "Dict" in field.type:
            return True
        if "List" in field.type:
            return True
        # Check for JSON-like types
        if field.type in ["dict", "list", "set", "tuple"]:
            return True
        return False

    def safe_python_value(self, key: str, val, field: Field) -> Any:
        logger.debug(f"Converted string to JSON:{key}:{field.type}: {val}")

        if (field.type == "str" and not field.repeated) or key in [
            "description",
            "doc",
        ]:
            return val

        if isinstance(val, str):
            # Remove extra quotes and escape characters
            v = val.strip()
            if (v.startswith('"') and v.endswith('"')) or (
                v.startswith("'") and v.endswith("'")
            ):
                v = v[1:-1]
            logger.debug(f"Processed string value: {v}")
            try:
                value = json.loads(v)
                logger.debug(f"Converted string to JSON: {value}")
                return value
            except Exception:
                pass
            try:
                return ast.literal_eval(v)
            except Exception:
                pass

        return val

    def _process_field_ext(
        self, imports: Set[str], field: Field, msg_ext: Dict[str, Any] = {}
    ) -> str:
        ext = field.ext
        sqlmodel_imports = set()
        logger.info(f"Processing field extensions: {msg_ext}")
        if ext:
            if ext.get("field_type") and not ext.get("sa_column_type"):
                # If field_type is set, use it as sa_column_type
                ext["sa_column_type"] = ext["field_type"]
                ext.pop("field_type", None)
            if (
                ext
                and (ext.get("sa_column_type") or self._is_JSON_field(field))
                and msg_ext.get("as_table", False)
            ):
                sqlmodel_imports.add("Column")
                if "Enum" in ext["sa_column_type"]:
                    sqlmodel_imports.add("Enum")
                else:
                    sqlmodel_imports.add(ext["sa_column_type"])
                ext["sa_column"] = (
                    f"Column({ext['sa_column_type']}, doc={ext.get('description', '')})"
                )
                ext.pop("sa_column_type", None)
            if (
                ext
                and ext.get("description")
                and not ext.get("sa_column")
                and msg_ext.get("as_table", False)
            ):
                ext["sa_column_kwargs"] = {
                    "comment": ext["description"].replace('"', "")
                }
        if sqlmodel_imports:
            sqlmodel_imports_str = ", ".join(set(sqlmodel_imports))
            sqlmodel_imports_str = (
                f"from sqlmodel import {sqlmodel_imports_str}"
                if sqlmodel_imports_str
                else ""
            )
            imports.add(sqlmodel_imports_str)
        ext.pop("required", None)
        attr = ", ".join(
            f"{key}={self.safe_python_value(key, value, field)}"
            for key, value in ext.items()
        )
        logger.debug(f"Processed field attributes: {attr}")
        return attr

    def _process_field(
        self,
        field_desc: descriptor_pb2.FieldDescriptorProto,
        message_desc: descriptor_pb2.DescriptorProto,
        filename: str,
        imports: Set[str],
        type_mapping: Dict[str, str],
    ) -> Field:
        """Process a protobuf field"""
        # Get field type
        field_type = self.type_mapper.get_field_type(
            field_desc, imports, type_mapping, filename
        )

        # Determine if field is repeated and required
        repeated = (
            field_desc.label == descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED
        )
        # required = field_desc.label == descriptor_pb2.FieldDescriptorProto.LABEL_REQUIRED

        # Extract field extensions
        field_ext = self._extract_field_extensions(field_desc)

        # Set default values
        field_ext = self.type_mapper.set_default_value(
            field_type, field_ext, field_desc
        )
        field_ext = self.type_mapper.sanitize_python_values(field_type, field_ext)

        # Build field attributes for Pydantic Field(
        message_info = self.type_mapper.get_message_info(field_desc)
        f = Field(
            name=field_desc.name,
            type=field_type,
            repeated=repeated,
            required=field_ext.get("required", False),
            attributes="",
            ext=field_ext,
            message_info=message_info,
        )
        message_ext = self._extract_message_extensions(message_desc)
        f.attributes = self._process_field_ext(imports, f, message_ext)
        return f

    def _extract_message_extensions(
        self, message_desc: descriptor_pb2.DescriptorProto
    ) -> Dict[str, Any]:
        """Extract message-level pydantic extensions"""
        try:
            if message_desc.options.HasExtension(pydantic_pb2.database):
                message_ext = message_desc.options.Extensions[pydantic_pb2.database]
                return MessageToDict(message_ext)
        except Exception as e:
            logger.debug(f"No database extension for message {message_desc.name}: {e}")

        return {}

    def _extract_field_extensions(
        self, field_desc: descriptor_pb2.FieldDescriptorProto
    ) -> Dict[str, Any]:
        """Extract field-level pydantic extensions"""
        try:
            if field_desc.options.HasExtension(pydantic_pb2.field):
                field_ext = field_desc.options.Extensions[pydantic_pb2.field]
                ext_dict = MessageToDict(field_ext)
                return ext_dict if ext_dict else {}
        except Exception as e:
            logger.debug(f"No field extension for field {field_desc.name}: {e}")

        return {}

    def _clean_extension_dict(self, ext_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Clean up extension dictionary by removing quotes and escape characters"""
        cleaned = {}
        for key, value in ext_dict.items():
            logger.info(f"Processing extension key: {key} with value: {value}")
            if isinstance(value, str):
                # Remove extra quotes and escape characters
                cleaned[key] = value.replace('"', "").replace("'", "")
            elif isinstance(value, dict):
                cleaned[key] = self._clean_extension_dict(value)
            elif isinstance(value, list):
                cleaned[key] = [
                    self._clean_extension_dict(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                cleaned[key] = value
        return cleaned

    def _build_field_attributes(
        self, field_ext: Dict[str, Any], repeated: bool, required: bool
    ) -> Dict[str, Any]:
        """Build Pydantic Field attributes from extensions"""
        attributes = {}

        # Map extension keys to Pydantic Field parameters
        ext_mapping = {
            "description": "description",
            "example": "example",
            "default": "default",
            "alias": "alias",
            "title": "title",
            "min_length": "min_length",
            "max_length": "max_length",
            "gt": "gt",
            "ge": "ge",
            "lt": "lt",
            "le": "le",
        }

        for ext_key, field_key in ext_mapping.items():
            if ext_key in field_ext:
                value = field_ext[ext_key]
                # Ensure string values are properly quoted
                if isinstance(value, str) and ext_key in [
                    "description",
                    "example",
                    "alias",
                    "title",
                ]:
                    # Remove extra quotes if already present
                    value = value.strip("\"'")
                    attributes[field_key] = f'"{value}"'
                else:
                    attributes[field_key] = value

        # Handle special cases
        if repeated and "default" not in attributes:
            attributes["default"] = "[]"

        if not required and "default" not in attributes:
            attributes["default"] = "None"

        return attributes

    def _apply_message_extensions(
        self, message: Message, message_ext: Dict[str, Any], imports: Set[str]
    ) -> None:
        """Apply message-level extensions"""
        if message_ext.get("as_table", False):
            message.as_table = True
            if self.config.generate_sqlmodel:
                imports.add("from sqlmodel import SQLModel, Field")

        if "table_name" in message_ext:
            message.table_name = message_ext["table_name"]

        # Handle compound indexes and other table args
        if message_ext.get("compound_index"):
            table_args = self._build_table_args(message_ext, imports)
            message.table_args = str(tuple(table_args)) if table_args else None
            message.table_args = message.table_args.replace("'", "")
            # message.table_args = ast.literal_eval(message.table_args) if message.table_args else None
            logger.info(
                f"Built table args for message {message.message_name}: {message.table_args}"
            )

    def _build_table_args(
        self, message_ext: Dict[str, Any], imports: Set[str]
    ) -> List[str]:
        """Build SQLAlchemy table args from extensions"""
        args = []
        compound_indexes = message_ext.get("compound_index", [])
        sqlmodel_imports = set()
        for index in compound_indexes:
            if not isinstance(index, dict):
                continue

            index_fields = index.get("indexs", [])
            index_type = index.get("index_type", "").upper()
            index_name = index.get("name", "")

            if not index_fields:
                continue

            # Build index definition
            fields_str = ", ".join(f'"{field}"' for field in index_fields)

            if index_type == "UNIQUE":
                args.append(f'UniqueConstraint({fields_str},name="{index_name}")')
                sqlmodel_imports.add("UniqueConstraint")
            elif index_type == "PRIMARY":
                args.append(f'PrimaryKeyConstraint({fields_str}, name="{index_name}")')
                sqlmodel_imports.add("PrimaryKeyConstraint")
            else:
                args.append(f"Index({index_name}, {fields_str})")
                sqlmodel_imports.add("Index")

        if sqlmodel_imports:
            sqlmodel_imports_str = ", ".join(set(sqlmodel_imports))
            sqlmodel_imports_str = (
                f"from sqlmodel import {sqlmodel_imports_str}"
                if sqlmodel_imports_str
                else ""
            )
            imports.add(sqlmodel_imports_str)
        return args

    def messages_to_metadata(self, messages: List[Message]) -> tuple[str, str]:
        """Convert messages to JSON metadata"""
        messages_metadata = {}
        fields_description = {}

        for message in messages:
            if message.message_type == MessageType.ENUM:
                continue  # Skip enums for now

            fields_dict = {}
            field_descriptions = {}

            for field in message.fields:
                field_descriptions[field.name] = field.ext.get("description", "")
                fields_dict[field.name] = {
                    "type": field.type,
                    "repeated": field.repeated,
                    "required": field.required,
                    "ext": field.ext,
                    "description": field.ext.get("description", ""),
                }

            messages_metadata[message.message_name] = fields_dict
            fields_description[message.message_name] = field_descriptions

        messages_json = json.dumps(messages_metadata, indent=4, ensure_ascii=False)
        fields_json = json.dumps(fields_description, indent=4, ensure_ascii=False)

        return messages_json, fields_json

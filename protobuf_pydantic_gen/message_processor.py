"""
Message and enum processing utilities
"""

import ast
import json
import logging
import re
from typing import List, Dict, Set, Any
from google.protobuf import descriptor_pb2
from google.protobuf.json_format import MessageToDict

from protobuf_pydantic_gen.utils import is_map_field
from . import pydantic_pb2
from .models import Message, Field, EnumField, MessageType
from .type_mapper import TypeMapper
from .config import get_config

logger = logging.getLogger(__name__)


def _discover_sa_types() -> Set[str]:
    """Dynamically discover SQLAlchemy column types from sqlalchemy.sql.sqltypes"""
    try:
        import sqlalchemy.sql.sqltypes as sqltypes
        from sqlalchemy import types as sa_types
        return {
            name for name in dir(sa_types)
            if not name.startswith('_') and isinstance(getattr(sa_types, name, None), type)
            and issubclass(getattr(sa_types, name), sqltypes.TypeEngine)
        }
    except ImportError:
        logger.warning("sqlalchemy not installed, using empty type set")
        return set()


def _discover_pg_types() -> Set[str]:
    """Dynamically discover PostgreSQL-specific types"""
    try:
        from sqlalchemy.dialects import postgresql
        from sqlalchemy.sql.sqltypes import TypeEngine
        return {
            name for name in dir(postgresql)
            if not name.startswith('_') and isinstance(getattr(postgresql, name, None), type)
            and issubclass(getattr(postgresql, name), TypeEngine)
        }
    except ImportError:
        logger.warning("sqlalchemy postgresql dialect not available, using empty type set")
        return set()


def _discover_pgvector_types() -> Set[str]:
    """Dynamically discover pgvector types from pgvector.sqlalchemy"""
    try:
        import pgvector.sqlalchemy as pgv
        from sqlalchemy.sql.sqltypes import TypeEngine
        return {
            name for name in dir(pgv)
            if not name.startswith('_') and isinstance(getattr(pgv, name, None), type)
            and issubclass(getattr(pgv, name), TypeEngine)
        }
    except ImportError:
        logger.warning("pgvector not installed, using empty type set")
        return set()


class MessageProcessor:
    """Processes protobuf messages and enums"""

    SQLALCHEMY_TYPES = _discover_sa_types()
    POSTGRESQL_TYPES = _discover_pg_types()
    PGVECTOR_TYPES = _discover_pgvector_types()

    def __init__(self, type_mapper: TypeMapper):
        self.type_mapper = type_mapper
        self.config = get_config()
        # Track Python enum type names so enum-typed table fields can be
        # given an explicit sa_column=Column(XxxType, ...) instead of
        # letting SQLAlchemy infer a native PostgreSQL ENUM type.
        self._enum_type_names: Set[str] = set()

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
                imports.add("from protobuf_pydantic_gen.ext import GenericEnumType")
            except Exception as e:
                logger.error(f"Error processing enum {enum_desc.name}: {e}")
                continue

        # Process messages (with nested enums extracted first)
        for message_desc in proto_file.message_type:
            try:
                # Extract and process nested enums before the message itself
                for enum_desc in self._extract_nested_enums(message_desc):
                    enum_message = self._process_enum(enum_desc, filename, type_mapping)
                    messages.append(enum_message)
                    imports.add("from enum import Enum as _Enum")
                    imports.add("from protobuf_pydantic_gen.ext import GenericEnumType")

                message = self._process_message(
                    message_desc, filename, imports, type_mapping, proto_file.package
                )
                messages.append(message)
            except Exception as e:
                logger.error(f"Error processing message {message_desc.name}: {e}")
                continue

        return messages

    @staticmethod
    def _extract_nested_enums(
        message_desc: descriptor_pb2.DescriptorProto,
    ) -> List[descriptor_pb2.EnumDescriptorProto]:
        """Recursively extract enums from within a message descriptor, skipping map entries."""
        enums: List[descriptor_pb2.EnumDescriptorProto] = list(message_desc.enum_type)
        for nested in message_desc.nested_type:
            if nested.options.map_entry:
                continue
            enums.extend(MessageProcessor._extract_nested_enums(nested))
        return enums

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
        self._enum_type_names.add(enum_desc.name)
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
                import traceback
                logger.error(f"Error processing field {field_desc.name}: {e}:{traceback.format_exc()}")
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

    def _get_sa_type_import(self, sa_column_type: str, imports: Set[str]) -> str:
        """Get the appropriate import statement for a SQLAlchemy type.

        Args:
            sa_column_type: The SQLAlchemy column type string (e.g. "ARRAY(Text)", "String(50)")
            imports: Set to add import statements to

        Returns:
            The type name to use in Column()
        """
        import re

        if not sa_column_type:
            return sa_column_type

        # Extract all identifiers from the type string to handle nested types
        # e.g. "ARRAY(Text)" -> ["ARRAY", "Text"], "String(50)" -> ["String"]
        identifiers = re.findall(r'\b([A-Za-z_][A-Za-z0-9_]*)\b', sa_column_type)

        for identifier in identifiers:
            if identifier in self.PGVECTOR_TYPES:
                imports.add(f"from pgvector.sqlalchemy import {identifier}")
            elif identifier in self.POSTGRESQL_TYPES:
                imports.add(f"from sqlalchemy.dialects.postgresql import {identifier}")
            elif identifier in self.SQLALCHEMY_TYPES:
                imports.add(f"from sqlalchemy import {identifier}")

        return sa_column_type

    # Keys whose values are code expressions and must never be repr()-quoted
    _CODE_EXPR_KEYS = frozenset({"sa_column", "sa_column_kwargs", "default_factory"})

    def _normalize_default_factory(self, ext: Dict[str, Any]) -> None:
        default_factory = ext.get("default_factory")
        if not isinstance(default_factory, str):
            return

        expr = default_factory.strip()
        if not expr:
            return

        if (expr.startswith('"') and expr.endswith('"')) or (
            expr.startswith("'") and expr.endswith("'")
        ):
            expr = expr[1:-1].strip()

        if expr.startswith("lambda "):
            ext["default_factory"] = expr
            return

        call_match = re.fullmatch(r"(?P<callable>[A-Za-z_][\w\.]*)\((?P<args>.*)\)", expr)
        if not call_match:
            ext["default_factory"] = expr
            return

        callable_expr = call_match.group("callable")
        call_args = call_match.group("args").strip()
        if not call_args:
            ext["default_factory"] = callable_expr
            return

        ext["default_factory"] = f"lambda: {expr}"

    def _pop_enum_storage_mode(self, field: Field, ext: Dict[str, Any]) -> str:
        storage_mode = str(ext.pop("enum_storage", "value")).strip().lower()
        if storage_mode not in {"value", "name"}:
            logger.warning(
                "Invalid enum_storage %r for field %s, falling back to 'value'",
                storage_mode,
                field.name,
            )
            return "value"
        if storage_mode != "value" and field.type not in self._enum_type_names:
            logger.warning(
                "enum_storage is only supported for enum fields, ignoring %r on %s",
                storage_mode,
                field.name,
            )
            return "value"
        return storage_mode

    def safe_python_value(self, key: str, val, field: Field) -> Any:
        if field.type == "str" and not field.repeated:
            if key not in self._CODE_EXPR_KEYS and (
                isinstance(val, str)
                and not val.startswith('"')
                and not val.startswith("'")
            ):
                # If it's a string and not quoted, we return it as is
                return repr(val)  # Return as a string with quotes

        if isinstance(val, str):
            v = val.strip()
            if (v.startswith('"') and v.endswith('"')) or (
                v.startswith("'") and v.endswith("'")
            ):
                v = v[1:-1]
            try:
                value = json.loads(v)
                return value
            except Exception:
                pass
            try:
                v = ast.literal_eval(v)
                return v
            except Exception:
                pass

        return val

    def _process_field_ext(
        self, imports: Set[str], field: Field, msg_ext: Dict[str, Any] = {}
    ) -> str:
        ext = field.ext
        sqlmodel_imports = set()
        if ext:
            self._normalize_default_factory(ext)
            enum_storage_mode = self._pop_enum_storage_mode(field, ext)
            if ext.get("field_type") and not ext.get("sa_column_type"):
                # If field_type is set, use it as sa_column_type
                ext["sa_column_type"] = ext["field_type"]
                ext.pop("field_type", None)
            # Auto-inject sa_column for datetime fields in table models.
            # Without this, SQLAlchemy maps datetime to TIMESTAMP WITHOUT
            # TIME ZONE, but migrations typically create TIMESTAMPTZ columns.
            # asyncpg then fails when binding tz-aware datetimes.
            if (
                msg_ext.get("as_table", False)
                and field.type == "datetime.datetime"
                and not ext.get("sa_column")
                and not ext.get("sa_column_type")
            ):
                sqlmodel_imports.add("Column")
                imports.add("from sqlalchemy import TIMESTAMP")
                nullable_val = ext.pop("nullable", True)
                col_extra: List[str] = [f"nullable={nullable_val}"]
                if ext.get("description"):
                    _doc = str(ext["description"]).replace('"', "")
                    col_extra.append(f"doc={repr(_doc)}")
                if ext.pop("sa_auto_update", False):
                    col_extra.append("onupdate=lambda: datetime.datetime.now(datetime.timezone.utc)")
                ext["sa_column"] = f"Column(TIMESTAMP(timezone=True), {', '.join(col_extra)})"

            # Auto-inject sa_column for enum-typed fields in table models.
            # Without this, SQLAlchemy infers a native PostgreSQL ENUM type
            # (e.g. ::dailycardstatus) which doesn't exist when the db schema
            # uses VARCHAR + CHECK constraints instead.
            if (
                msg_ext.get("as_table", False)
                and field.type in self._enum_type_names
                and not ext.get("sa_column")
                and not ext.get("sa_column_type")
            ):
                sqlmodel_imports.add("Column")
                enum_type_alias = (
                    f"{field.type}NameType" if enum_storage_mode == "name" else f"{field.type}Type"
                )
                # Use nullable from ext (proto nullable extension); default False
                nullable_val = ext.pop("nullable", False)
                col_extra: List[str] = [f"nullable={nullable_val}"]
                if ext.get("description"):
                    _doc = str(ext["description"]).replace('"', "")
                    col_extra.append(f"doc={repr(_doc)}")
                ext["sa_column"] = f"Column({enum_type_alias}, {', '.join(col_extra)})"
            if (
                ext
                and (ext.get("sa_column_type") or self._is_JSON_field(field))
                and msg_ext.get("as_table", False)
            ):
                sqlmodel_imports.add("Column")
                sa_column_type = ext.get("sa_column_type", "")

                # Handle type imports automatically
                if sa_column_type:
                    # Check if it contains "Enum" from sqlmodel (not SQLAlchemy Enum type)
                    if "Enum" in sa_column_type and not sa_column_type.startswith("Enum"):
                        # This is likely an Enum usage like Enum(MyEnum)
                        sqlmodel_imports.add("Enum")
                    else:
                        # Use the new method to handle SQLAlchemy types
                        sa_column_type = self._get_sa_type_import(sa_column_type, imports)

                # Build Column() with all SQLAlchemy attributes
                column_args = [sa_column_type] if sa_column_type else []
                column_kwargs = []

                # Move index/unique/nullable/primary_key to Column()
                if ext.get("index"):
                    column_kwargs.append(f"index={ext['index']}")
                    ext.pop("index", None)
                if ext.get("unique"):
                    column_kwargs.append(f"unique={ext['unique']}")
                    ext.pop("unique", None)
                if ext.get("nullable") is not None:
                    column_kwargs.append(f"nullable={ext['nullable']}")
                    ext.pop("nullable", None)
                if ext.get("primary_key"):
                    column_kwargs.append(f"primary_key={ext['primary_key']}")
                    ext.pop("primary_key", None)
                if ext.get("foreign_key"):
                    column_kwargs.append(f"foreign_key={ext['foreign_key']}")
                    ext.pop("foreign_key", None)
                if ext.pop("sa_auto_update", False):
                    column_kwargs.append("onupdate=lambda: datetime.datetime.now(datetime.timezone.utc)")

                # Add doc parameter
                if ext.get("description"):
                    column_kwargs.append(f"doc={ext['description']}")

                column_args_str = ", ".join(column_args + column_kwargs)
                ext["sa_column"] = f"Column({column_args_str})"
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
        ext.pop("sa_auto_update", None)
        ext.pop("required", None)
        extra_key = (
            "schema_extra" if msg_ext.get("as_table", False) else "json_schema_extra"
        )
        if ext.get("example"):
            ext[extra_key] = ext.get(extra_key, {})
            example = ext["example"].replace('"', "")
            ext[extra_key].update({"example": example})
            ext.pop("example", None)
        if ext.get("label"):
            ext[extra_key] = ext.get(extra_key, {})
            label = ext["label"].replace('"', "")
            ext[extra_key].update({"label": label})
            ext.pop("label", None)
        if ext.get("nullable") is not None:
            if not msg_ext.get("as_table", False):
                # Non-ORM (service message) field: move nullable into json_schema_extra
                # to stay Pydantic V2 compatible (Field() does not accept nullable kwarg)
                ext[extra_key] = ext.get(extra_key, {})
                ext[extra_key]["nullable"] = ext.pop("nullable")
            else:
                # ORM table field: nullable should already be consumed by Column(); drop leftover
                ext.pop("nullable", None)

        attr = ", ".join(
            f"{key}={self.safe_python_value(key, value, field)}"
            for key, value in ext.items()
        )
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
        ) and not is_map_field(field_desc, message_desc)
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
            logger.info(f"No field extension for field {field_desc.name}: {e}")

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
                args.append(f'Index("{index_name}", {fields_str})')
                sqlmodel_imports.add("Index")
        args.append({"'extend_existing'": True})
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

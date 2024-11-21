#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File    :   main.py
@Time    :   2024/04/23 14:09:16
@Desc    :   Code generation for pydantic models from protobuf definitions
'''

from contextlib import contextmanager
import json
import ast
import sys
import logging
import os
import autopep8
import inflection

from typing import Iterator, Set, Tuple, List
from google.protobuf.compiler import plugin_pb2
from google.protobuf import descriptor_pb2, descriptor_pool
from google.protobuf.json_format import MessageToDict

from jinja2 import Template
from protobuf_pydantic_gen import pydantic_pb2


# from .template import tpl_str


__version__ = "0.0.1"

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
pool = descriptor_pool.DescriptorPool()


class Field:
    def __init__(self, name: str, type: str, repeated: bool, required: bool, attributes: dict):
        self.name = name
        self.type = type
        self.repeated = repeated
        self.required = required
        self.attributes = attributes

        def __str__(self):
            return f"FieldItem({self.name}, {self.type}, {self.repeated}, {self.optional})"


class EnumField:
    def __init__(self, name: str, value: str):
        self.name = name
        self.value = value

        def __str__(self):
            return f"EnumField({self.name}, {self.value})"


class Message:
    def __init__(
            self,
            name: str,
            fields: list,
            message_type="class",
            table_name=None,
            table_args=None,
            as_table=False,
            full_name: str = ""):
        self.message_name = name
        self.fields = fields
        # self.imports = imports
        self.type = message_type

        self.table_name = table_name or name
        self.table_name = inflection.underscore(self.table_name)
        self.table_args: Tuple[str] = table_args
        self.proto_full_name = full_name

        self.as_table = as_table

        def __str__(self):
            return f"Message({self.messages}, {self.fields})"


def get_field_type(field, imports: List[str], out: dict, file_name: str):
    # 这个函数用于将field.type（枚举值）转换为对应的类型名称
    field_type_mapping = {
        descriptor_pb2.FieldDescriptorProto.TYPE_DOUBLE: "float",
        descriptor_pb2.FieldDescriptorProto.TYPE_FLOAT: "float",
        descriptor_pb2.FieldDescriptorProto.TYPE_INT64: "int",
        descriptor_pb2.FieldDescriptorProto.TYPE_UINT64: "int",
        descriptor_pb2.FieldDescriptorProto.TYPE_INT32: "int",
        descriptor_pb2.FieldDescriptorProto.TYPE_FIXED64: "int",
        descriptor_pb2.FieldDescriptorProto.TYPE_FIXED32: "int",
        descriptor_pb2.FieldDescriptorProto.TYPE_BOOL: "bool",
        descriptor_pb2.FieldDescriptorProto.TYPE_STRING: "str",
        # descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE: "message",  # 保持原样，因为指向特定消息
        descriptor_pb2.FieldDescriptorProto.TYPE_BYTES: "bytes",
        descriptor_pb2.FieldDescriptorProto.TYPE_UINT32: "int",
        descriptor_pb2.FieldDescriptorProto.TYPE_ENUM: "Enum",  # Python 枚举类
        descriptor_pb2.FieldDescriptorProto.TYPE_SFIXED32: "int",
        descriptor_pb2.FieldDescriptorProto.TYPE_SFIXED64: "int",
        descriptor_pb2.FieldDescriptorProto.TYPE_SINT32: "int",
        descriptor_pb2.FieldDescriptorProto.TYPE_SINT64: "int",
    }

    # 如果类型为消息或枚举，返回type_name，否则返回基本类型的名称
    if hasattr(field, "type_name") and field.type == descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE:
        if field.type_name == ".google.protobuf.Timestamp":
            return "datetime.datetime"
        key_type, value_type = get_map_field_types(
            field, imports, out, file_name)
        if key_type and value_type and check_if_map_field(field):
            imports.add("Dict")
            return f"Dict[{key_type},{value_type}]"
        out[field.type_name.split(".")[-1]] = file_name
        return field.type_name.split(".")[-1]
    else:
        if field.type == descriptor_pb2.FieldDescriptorProto.TYPE_ENUM:
            out[field.type_name.split(".")[-1]] = file_name
            return field.type_name.split(".")[-1]
        return field_type_mapping.get(field.type, "Any")


@contextmanager
def code_generation() -> Iterator[Tuple[plugin_pb2.CodeGeneratorRequest, plugin_pb2.CodeGeneratorResponse],]:
    if len(sys.argv) > 1 and sys.argv[1] in ("-V", "--version"):
        print("pydantic-protobuf " + __version__)
        sys.exit(0)
    # Read request message from stdin
    data = sys.stdin.buffer.read()

    # Parse request
    request = plugin_pb2.CodeGeneratorRequest()

    request.ParseFromString(data)
    # Create response
    response = plugin_pb2.CodeGeneratorResponse()

    # Declare support for optional proto3 fields
    response.supported_features |= plugin_pb2.CodeGeneratorResponse.FEATURE_PROTO3_OPTIONAL

    yield request, response

    # Serialise response message
    output = response.SerializeToString()

    # Write to stdout
    sys.stdout.buffer.write(output)


def applyTemplate(filename: str, messages: List[Message], enums: List[Message], imports: List[str]) -> str:
    filepath = os.path.join(os.path.dirname(__file__), "template.j2")
    with open(filepath, "r", encoding="utf-8") as f:
        tpl_str = f.read()
        tpl = Template(tpl_str)
        return tpl.render(name=filename, messages=messages, enums=enums, imports=imports)


def get_map_field_types(field, imports: List[str], out: dict, file_name: str):
    # 此函数假设您可以访问到整个文件的描述符，以便查找相应的嵌套类型
    if field.type_name and field.type_name.startswith("."):
        field.type_name = field.type_name[1:]
    message_descriptor = pool.FindMessageTypeByName(field.type_name)
    key_type = None
    value_type = None
    for field in message_descriptor.fields:
        if field.name == "key":
            key_type = get_field_type(field, imports, out, file_name)
        elif field.name == "value":
            value_type = get_field_type(field, imports, out, file_name)
            if value_type == "Any":
                imports.add("Any")
    return key_type, value_type


def is_valid_expression(s):
    try:
        ast.literal_eval(s)
        return s
    except Exception as err:
        # logging.info(f"Error: {err} in {s}")
        return f'"{s}"'


def set_default(type_str: str, ext: dict, fd: descriptor_pb2.FieldDescriptorProto):
    """根据类型设置默认值

    Args:
        type_str (str): _description_
        ext (dict): _description_
        fd (descriptor_pb2.FieldDescriptorProto): _description_

    Returns:
        _type_: _description_
    """
    if "default" in ext:
        # logging.info(f"type str is {type_str}")
        if type_str in ["str"]:
            ext["default"] = f'"{ext["default"]}"'
        elif type_str.find("Dict") != -1 or type_str.startswith("List"):
            # logging.info(f"set Dict {ext['default']}")
            ext["default"] = json.loads(ext["default"])
        else:
            # logging.info(f"set python type:{ext['default']}")
            ext["default"] = ext["default"]
    else:
        if type_str == "str":
            ext["default"] = '""'
        elif type_str == "int":
            ext["default"] = 0
        elif type_str == "float":
            ext["default"] = 0.0
        elif type_str == "bool":
            ext["default"] = False
        elif type_str == "bytes":
            ext["default"] = b""
        elif type_str == "datetime.datetime":
            ext["default"] = None
        elif fd.type == descriptor_pb2.FieldDescriptorProto.TYPE_ENUM:
            # logging.debug(f"fd.type_name:{fd.DESCRIPTOR.enum_types_by_name}")
            ext["default"] = f"{fd.type_name.split('.')[-1]}(0)"
        elif type_str == "Any":
            ext["default"] = None
        elif type_str == "List":
            ext["default"] = []
        elif type_str == "Dict":
            ext["default"] = {}
    return ext


def set_python_type_value(type_str: str, ext: dict):
    if type_str == "str":
        if "example" in ext:
            ext["example"] = f'"{ext["example"]}"'
    if "description" in ext:
        ext["description"] = f'"{ext["description"]}"'
    if "alias" in ext:
        ext["alias"] = f'"{ext["alias"]}"'
    return ext


def check_if_map_field(field_descriptor):
    # 检查字段是否是 repeated 类型
    if field_descriptor.label != descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED:
        return False
    # 检查字段的类型是否是消息类型，因为 map 类型在 Protobuf 中实现为消息类型
    if field_descriptor.type != descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE:
        return False
    # 检查消息类型是否以 'Entry' 结尾，这是一个通常的命名约定，用于 protobuf 中的 map entry 类型
    return field_descriptor.type_name.endswith('Entry')


def is_JSON_field(type_str):
    field_types = ["message", "List", "Dict", "Tuple", "dict", "list", "tuple"]
    for field_type in field_types:
        if field_type in type_str:
            return True
    return False


def get_table_args(ext: dict, pydantic_imports: Set[str]) -> List[str]:
    # # logging.info(f"message ext: {ext}")
    compound_indexs = ext.get("compound_index")
    args = []
    if compound_indexs:
        for index in compound_indexs:
            arg = [f'"{i}"' for i in index["indexs"]]
            name = index.get("name")
            # arg.append(f'"{name}"')
            if index.get("index_type", "").lower() == "UNIQUE".lower():
                args.append(f"UniqueConstraint({','.join(arg)},name='{name}')")
                pydantic_imports.add("UniqueConstraint")
            if index.get("index_type", "").lower() == "PRIMARY".lower():
                args.append(
                    f"PrimaryKeyConstraint({','.join(arg)},name='{name}')")
                pydantic_imports.add("PrimaryKeyConstraint")
    return args


def generate_code(request: plugin_pb2.CodeGeneratorRequest,
                  response: plugin_pb2.CodeGeneratorResponse):

    message_types = {}
    for proto_file in request.proto_file:
        filename = os.path.basename(proto_file.name).split('.')[0]

        messages: List[Message] = []
        enums: List[Message] = []
        try:
            pool.Add(proto_file)
        except Exception as err:
            logging.error(
                f"Error adding file {proto_file.name} to pool: {err}")
            pass
        if proto_file.package == "pydantic":
            continue
        if "google/protobuf" in proto_file.name:
            continue  # 跳过 Protobuf 的内置类型文件
        imports = set()
        type_imports = set()
        sqlmodel_imports = set()
        ext_message = {}
        ext_imports = set()
        for enum in proto_file.enum_type:
            message_types[enum.name] = filename
            fields = []
            imports.add("from enum import Enum as _Enum")

            for value in enum.value:
                fields.append(EnumField(value.name, value.number))
            enums.append(Message(enum.name, fields, "enum"))
        for message in proto_file.message_type:
            fields = []

            message_types[message.name] = filename
            for field in message.field:
                # # logging.info(f"Field: {field.options.Extensions}")
                field_extension = field.options.Extensions[pydantic_pb2.field]
                ext = MessageToDict(field_extension)
                required = False
                type_str = get_field_type(
                    field, type_imports, ext_message, filename)
                # logging.info(f"field type is {type_str}")
                if type_str in ["Any", "message"]:
                    type_imports.add("Any")
                is_repeated = field.label == descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED and \
                    not check_if_map_field(
                        field)
                if ext:

                    if "required" in ext:
                        ext["schema_extra"] = f"{{'required': {ext['required']}}}"
                        required = ext.pop("required")
                    # logging.info(f"set python type value:{type_str}")
                    _type_str = type_str
                    if is_repeated:
                        _type_str = "List"
                    ext = set_default(_type_str, ext, field)
                    ext = set_python_type_value(_type_str, ext)
                if ext.get("field_type"):
                    field_type_str = ext["field_type"]
                    ext.pop("field_type")
                    ext["sa_type"] = field_type_str
                    sqlmodel_imports.add(field_type_str)
                if ext and ext.get("sa_column_type"):
                    sqlmodel_imports.add("Column")
                    if "Enum" in ext["sa_column_type"]:
                        sqlmodel_imports.add("Enum")
                    else:
                        sqlmodel_imports.add(ext["sa_column_type"])

                    ext["sa_column"] = f"Column({ext['sa_column_type']})"
                    ext.pop("sa_column_type")

                if is_JSON_field(type_str) and ext:
                    sqlmodel_imports.add("JSON")
                    sqlmodel_imports.add("Column")
                    ext["sa_column"] = "Column(JSON)"

                attr = ",".join(f"{key}={value}" for key,
                                value in ext.items())
                if is_repeated:
                    type_imports.add("List")
                if field.label == descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL:
                    type_imports.add("Optional")

                if type_str == "datetime.datetime":
                    imports.add("import datetime")

                f = Field(field.name, type_str, is_repeated,
                          required, attr)

                fields.append(f)
            type_imports.add("Type")

            message_ext = message.options.Extensions[pydantic_pb2.database]
            ext = MessageToDict(message_ext)

            table_args = get_table_args(ext, sqlmodel_imports)
            sqlmodel_imports_str = ", ".join(set(sqlmodel_imports))
            sqlmodel_imports_str = f"from sqlmodel import {sqlmodel_imports_str}" if sqlmodel_imports_str else ""
            imports.add(sqlmodel_imports_str)
            if ext.get("as_table", False):
                imports.add("from sqlmodel import SQLModel, Field")
                ext_imports.add("PySQLModel")
            else:
                imports.add("from pydantic import BaseModel, ConfigDict")
                imports.add("from pydantic import Field as _Field")

                ext_imports.add("PydanticModel")
            ext_imports.add("model2protobuf")
            ext_imports.add("protobuf2model")
            ext_imports.add("pool")
            imports.add("from google.protobuf import message as _message")
            imports.add("from google.protobuf import message_factory")
            messages.append(
                Message(
                    message.name,
                    fields,
                    table_name=ext.get("table_name"),
                    as_table=ext.get("as_table", False),
                    table_args=",".join(table_args),
                    full_name=f"{proto_file.package}.{message.name}"
                )
            )
        type_imports_str = ", ".join(type_imports)

        type_imports_str = f"from typing import {type_imports_str}" if type_imports_str else ""
        imports.add(type_imports_str)
        for msg_type in ext_message.keys():
            import_from = message_types.get(msg_type)
            if import_from is None:
                continue
            if message_types.get(msg_type) != filename:
                imports.add(
                    f"from .{message_types.get(msg_type)}_model import {msg_type}")
        if len(ext_imports):
            imports.add(
                f"from protobuf_pydantic_gen.ext import {', '.join(ext_imports)}")

        code = applyTemplate(filename, messages, enums, imports)

        code = autopep8.fix_code(
            code,
            options={
                "max_line_length": 120,
                "in_place": True,
                "aggressive": 5,
            }
        )
        response.file.add(
            name=filename.lower() +
            '_model.py',
            content=code)


def main():
    with code_generation() as (request, response):
        generate_code(request, response)


if __name__ == "__main__":
    main()

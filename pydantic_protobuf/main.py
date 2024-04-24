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
import time
from typing import Iterator, Tuple, List
from google.protobuf.compiler import plugin_pb2
from google.protobuf import timestamp_pb2
from google.protobuf import descriptor_pb2, descriptor_pool
from google.protobuf.json_format import MessageToJson

from jinja2 import Template
from distutils.log import log
from pydantic_protobuf import options_pb2


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


class Message:
    def __init__(self, name: str, fields: list):
        self.message_name = name
        self.fields = fields
        # self.imports = imports

        def __str__(self):
            return f"Message({self.messages}, {self.fields})"


def get_field_type(field, imports: List[str]):
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
        descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE: "message",  # 保持原样，因为指向特定消息
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
            field, imports)
        if key_type and value_type:
            imports.add("Dict")
            return f"Dict[{key_type},{value_type}]"
        return "Any"
    else:
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


def applyTemplate(filename: str, messages: List[Message], imports: List[str]) -> str:
    filepath = os.path.join(os.path.dirname(__file__), "template.j2")
    with open(filepath, "r", encoding="utf-8") as f:
        tpl_str = f.read()
        tpl = Template(tpl_str)
        return tpl.render(name=filename, messages=messages, imports=imports)


def get_map_field_types(field, imports: List[str]):
    # 此函数假设您可以访问到整个文件的描述符，以便查找相应的嵌套类型
    if field.type_name and field.type_name.startswith("."):
        field.type_name = field.type_name[1:]
    message_descriptor = pool.FindMessageTypeByName(field.type_name)
    key_type = None
    value_type = None
    for field in message_descriptor.fields:
        if field.name == "key":
            key_type = get_field_type(field, imports)
        elif field.name == "value":
            value_type = get_field_type(field, imports)
    return key_type, value_type


def is_valid_expression(s):
    try:
        ast.literal_eval(s)
        return s
    except:
        return f'"{s}"'


def generate_code(request: plugin_pb2.CodeGeneratorRequest, response: plugin_pb2.CodeGeneratorResponse):
    # pool.FileDescriptorProto(timestamp_pb2.Timestamp())
    for proto_file in request.proto_file:

        messages: List[Message] = []
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
        for message in proto_file.message_type:
            fields = []
            for field in message.field:
                field_extension = field.options.Extensions[options_pb2.field]

                ext = MessageToJson(field_extension)
                type_str = get_field_type(field, type_imports)
                if type_str in ["Any", "message"]:
                    type_imports.add("Any")
                if ext:
                    ext = json.loads(ext)
                attr = ",".join(f"{key}={is_valid_expression(value)}" for key,
                                value in ext.items())
                if field.label == descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED:
                    type_imports.add("List")
                if field.label == descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL:
                    type_imports.add("Optional")
                if field.type == descriptor_pb2.FieldDescriptorProto.TYPE_ENUM:
                    imports.add("from enum import Enum")
                if type_str == "datetime.datetime":
                    imports.add("import datetime")

                f = Field(field.name, type_str, field.label == descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED,
                          ext.get("required", False), attr)
                fields.append(f)
            type_imports_str = ", ".join(type_imports)
            type_imports_str = f"from typing import {type_imports_str}" if type_imports_str else ""
            imports.add(type_imports_str)
            messages.append(Message(message.name, fields))
        filename = os.path.basename(proto_file.name).split('.')[0]
        code = applyTemplate(filename, messages, imports)
        response.file.add(name=filename.lower() + '_model.py', content=code)


def main():
    with code_generation() as (request, response):
        generate_code(request, response)


if __name__ == "__main__":
    main()

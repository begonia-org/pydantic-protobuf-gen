#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File    :   orm.py
@Time    :   2024/06/30 13:51:33
@Desc    :
'''


from typing import Any, Dict, Type, TypeVar
from pydantic import BaseModel
from datetime import datetime
from enum import Enum
from sqlmodel import SQLModel
from google.protobuf.json_format import ParseDict
from google.protobuf import message as _message
from google.protobuf.json_format import MessageToDict
from google.protobuf import descriptor_pool, message_factory
from google.protobuf.timestamp_pb2 import Timestamp
from . import pydantic_pb2


pool = descriptor_pool.Default()

ProtobufMessage = TypeVar("ProtobufMessage", bound="_message.Message")
PydanticModel = TypeVar("PydanticModel", bound="BaseModel")
PySQLModel = TypeVar("PySQLModel", bound="SQLModel")


def scalar_map_to_dict(scalar_map):
    # Check if scalar_map is an instance of Struct
    return {k: v for k, v in scalar_map.items()}


def is_map(fd):
    return fd.type == fd.TYPE_MESSAGE and fd.message_type.has_options and fd.message_type.GetOptions().map_entry


def model2protobuf(model: SQLModel, proto: _message.Message) -> _message.Message:
    def _convert_value(fd, value):
        if fd.type == fd.TYPE_ENUM:
            if isinstance(value, str):
                return value
            if isinstance(value, int):
                return fd.enum_type.values_by_number[int(value)].name
            if isinstance(value, Enum):
                return value.name

        elif fd.type == fd.TYPE_MESSAGE:
            if fd.message_type.full_name == Timestamp.DESCRIPTOR.full_name:
                if not value:
                    return None
                ts = Timestamp()
                if isinstance(value, datetime):
                    ts.FromDatetime(value)
                elif isinstance(value, str):
                    dt = datetime.fromisoformat(value)

                    ts.FromDatetime(dt)
                return ts.ToJsonString()
            elif fd.message_type.has_options and fd.message_type.GetOptions().map_entry:

                # Check if the key and value types are both strings
                # key_field = fd.message_type.fields_by_name['key']
                value_field = fd.message_type.fields_by_name['value']
                # key_type = key_field.fields_by_name['key'].type
                value_type = fd.message_type.fields_by_name['value'].type
                if value_type == value_field.TYPE_STRING:
                    return scalar_map_to_dict(value)
                else:
                    nested_proto = pool.FindMessageTypeByName(fd.message_type.full_name)
                    nested_cls = message_factory.GetMessageClass(nested_proto)
                    return {k: MessageToDict(model2protobuf(v, nested_cls())) for k, v in value.items()}
            else:
                nested_proto = pool.FindMessageTypeByName(fd.message_type.full_name)
                nested_cls = message_factory.GetMessageClass(nested_proto)
                return MessageToDict(model2protobuf(value, nested_cls()))
        else:
            return value
    if isinstance(model, dict):
        d = model
    else:
        d = model.model_dump()
        for fd in proto.DESCRIPTOR.fields:
            if fd.name in d:
                field_value = getattr(model, fd.name)
                if fd.label == fd.LABEL_REPEATED and not is_map(fd):
                    d[fd.name] = [_convert_value(fd, item) for item in field_value]
                else:
                    d[fd.name] = _convert_value(fd, field_value)
    proto = ParseDict(d, proto)
    return proto


def protobuf_dump(proto: _message.Message) -> Dict[str,Any]:
    def _convert_value(fd, value):
        if value is None:
            field_extension = fd.GetOptions().Extensions[pydantic_pb2.field]
            ext = MessageToDict(field_extension)
            default = None
            if fd.type == fd.TYPE_ENUM:
                default = 0
            elif fd.type == fd.TYPE_STRING:
                default = ""
            elif fd.type == fd.TYPE_BOOL:
                default = False
            elif fd.type == fd.TYPE_MESSAGE:
                default = None
            else:
                default = 0

            value = ext.get('default', default)
        if fd.type == fd.TYPE_ENUM:
            if value is None:
                return 0
            return value

        elif fd.type == fd.TYPE_MESSAGE:
            if fd.message_type.full_name == Timestamp.DESCRIPTOR.full_name:
                if value:
                    ts = Timestamp()
                    ts.FromJsonString(value)
                    return ts.ToDatetime()
                if value is None:
                    return None
            elif fd.message_type.has_options and fd.message_type.GetOptions().map_entry:
                return {k: _convert_value(fd.message_type.fields_by_name['value'], v) for k, v in value.items()}
            else:
                nested_proto = pool.FindMessageTypeByName(fd.message_type.full_name)
                nested_cls = message_factory.GetMessageClass(nested_proto)
                nested_instance = nested_cls()
                # model = globals().get(nested_instance.DESCRIPTOR.name, None)
                # print(f"nested_instance:{nested_instance.DESCRIPTOR.name},value:{value},model:{model}")
                nested_instance = ParseDict(value, nested_instance)
                return protobuf_dump(nested_instance)

        return value

    # Convert protobuf message to dictionary
    proto_dict = MessageToDict(proto, preserving_proto_field_name=True, use_integers_for_enums=True)

    # Get SQLModel fields
    # model_fields = model_cls.__annotations__

    # print(model_fields)
    # import typing

    # Prepare dictionary to create SQLModel instance
    model_data = {}
    for fd in proto.DESCRIPTOR.fields:
        field_name = fd.name
        # if field_name in proto_dict:
        value = proto_dict.get(field_name, None)

        if fd.label == fd.LABEL_REPEATED and not is_map(fd):
            model_data[field_name] = [_convert_value(fd, item) for item in value]
            # print(f"{field_name} model data:{model_data[field_name]}")
        else:
            model_data[field_name] = _convert_value(fd, value)
            # print(f"{field_name} model data:{model_data[field_name]}")

    # Create and return SQLModel instance
    # print(f"cls model data:{model_data}")
    # return model_cls(**model_data)
    return model_data

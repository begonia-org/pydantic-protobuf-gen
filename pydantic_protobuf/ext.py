#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File    :   orm.py
@Time    :   2024/06/30 13:51:33
@Desc    :   
'''


from typing import TypeVar

from google.protobuf import message as _message
from datetime import datetime
from enum import Enum
from sqlmodel import SQLModel
from google.protobuf.json_format import ParseDict
from google.protobuf import message
from google.protobuf.json_format import MessageToDict
from google.protobuf import descriptor_pool, message_factory
from google.protobuf.timestamp_pb2 import Timestamp


pool = descriptor_pool.Default()

ProtobufMessage = TypeVar("ProtobufMessage", bound="_message")

def scalar_map_to_dict(scalar_map):
    # Check if scalar_map is an instance of Struct
    return {k: v for k, v in scalar_map.items()}


def is_map(fd):
    return fd.type == fd.TYPE_MESSAGE and fd.message_type.has_options and fd.message_type.GetOptions().map_entry


def model2protobuf(model: SQLModel, proto: message.Message) -> message.Message:
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


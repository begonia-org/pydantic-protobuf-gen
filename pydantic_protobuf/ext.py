#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File    :   orm.py
@Time    :   2024/06/30 13:51:33
@Desc    :
'''


import importlib
from typing import Type, TypeVar, get_args
from pydantic import BaseModel
from datetime import datetime
from enum import Enum
from sqlmodel import SQLModel
from google.protobuf.json_format import ParseDict
from google.protobuf import message as _message
from google.protobuf.json_format import MessageToDict
from google.protobuf import descriptor_pool, message_factory
from google.protobuf.timestamp_pb2 import Timestamp


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

def _get_class_from_path(module_path, class_name):
    # 动态导入模块
    module = importlib.import_module(module_path)
    # 获取类对象
    cls = getattr(module, class_name)
    return cls

def _get_model_cls_by_field(model_cls: Type[SQLModel], field_name: str) -> Type[SQLModel]:
    fields = model_cls.model_fields()
    # if get_args(typ.annotation):
            # print(name,get_args(typ.annotation)[0].__module__)
    annot = fields.get(field_name)
    module = get_args(annot.annotation)[0].__module__
    cls = get_args(annot.annotation)[0].__name__
    return _get_class_from_path(module, cls)


def protobuf2model(model_cls: Type[SQLModel],proto: _message.Message) -> SQLModel:
    def _convert_value(fd, value):
        if fd.type == fd.TYPE_ENUM:
            return value

        elif fd.type == fd.TYPE_MESSAGE:
            
            if fd.message_type.full_name == Timestamp.DESCRIPTOR.full_name:
                if value:
                    ts = Timestamp()
                    ts.FromJsonString(value)
                    return ts.ToDatetime()
            elif fd.message_type.has_options and fd.message_type.GetOptions().map_entry:
                return {k: _convert_value(fd.message_type.fields_by_name['value'], v) for k, v in value.items()}
            else:
                nested_proto = pool.FindMessageTypeByName(fd.message_type.full_name)
                nested_cls = message_factory.GetMessageClass(nested_proto)
                nested_instance = nested_cls()
                ParseDict(value, nested_instance)
                model_cls=_get_model_cls_by_field(model_cls, fd.name)
                return protobuf2model(nested_instance, model_cls)

        return value

    # Convert protobuf message to dictionary
    proto_dict = MessageToDict(proto, preserving_proto_field_name=True, use_integers_for_enums=True)

    # Get SQLModel fields
    model_fields = model_cls.__annotations__

    # Prepare dictionary to create SQLModel instance
    model_data = {}
    for fd in proto.DESCRIPTOR.fields:
        field_name = fd.name
        if field_name in proto_dict and field_name in model_fields:
            value = proto_dict[field_name]
            if fd.label == fd.LABEL_REPEATED and not is_map(fd):
                model_data[field_name] = [_convert_value(fd, item) for item in value]
            else:
                model_data[field_name] = _convert_value(fd, value)

    # Create and return SQLModel instance
    return model_cls(**model_data)

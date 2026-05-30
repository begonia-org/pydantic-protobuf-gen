#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@File    :   orm.py
@Time    :   2024/06/30 13:51:33
@Desc    :
"""

import importlib
from datetime import datetime
from enum import Enum
from types import UnionType
from typing import (
    Any,
    Dict,
    Generic,
    List,
    Tuple,
    Type,
    TypeVar,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)

from google.protobuf import any_pb2, descriptor_pb2, descriptor_pool
from google.protobuf import message as _message
from google.protobuf import message_factory
from google.protobuf.json_format import MessageToDict, ParseDict
from google.protobuf.field_mask_pb2 import FieldMask
from google.protobuf.struct_pb2 import ListValue, Struct, Value
from google.protobuf.timestamp_pb2 import Timestamp
from pydantic import BaseModel
from sqlalchemy import String
from sqlmodel import SQLModel
from sqlalchemy.types import TypeDecorator

from protobuf_pydantic_gen.any_type_transformer import AnyTransformer
from protobuf_pydantic_gen.utils import is_map_field

pool = descriptor_pool.Default()

ProtobufMessage = TypeVar("ProtobufMessage", bound="_message.Message")
PydanticModel = TypeVar("PydanticModel", bound="BaseModel")
PySQLModel = TypeVar("PySQLModel", bound="SQLModel")


def scalar_map_to_dict(scalar_map):
    # Check if scalar_map is an instance of Struct
    return {k: v for k, v in scalar_map.items()}


def is_map(fd):
    return (
        fd.type == fd.TYPE_MESSAGE
        and fd.message_type.has_options
        and fd.message_type.GetOptions().map_entry
    )


E = TypeVar("E", bound=Enum)


class GenericEnumType(TypeDecorator, Generic[E]):
    """通用枚举类型，支持按 name 或 value 持久化枚举。"""

    impl = String
    cache_ok = True

    _VALID_MODES = {"name", "value"}

    def __init__(
        self,
        enum_class: Type[E],
        *,
        storage_mode: str = "value",
        read_modes: Tuple[str, ...] = ("value", "name"),
        strict: bool = True,
        **kwargs: Any,
    ):
        self.enum_class = enum_class
        self.storage_mode = storage_mode
        self.read_modes = read_modes
        self.strict = strict
        self._validate_modes()
        super().__init__(**kwargs)

    def _validate_modes(self) -> None:
        if self.storage_mode not in self._VALID_MODES:
            raise ValueError(
                f"Unsupported enum storage mode {self.storage_mode!r} for {self.enum_class.__name__}"
            )
        invalid_modes = [
            mode for mode in self.read_modes if mode not in self._VALID_MODES
        ]
        if invalid_modes:
            raise ValueError(
                f"Unsupported enum read modes {invalid_modes!r} for {self.enum_class.__name__}"
            )

    def _decode(self, value: Any, mode: str) -> Union[E, None]:
        if isinstance(value, self.enum_class):
            return value

        if mode == "name":
            if isinstance(value, str):
                try:
                    return self.enum_class[value]
                except KeyError:
                    return None
            return None

        value_candidates = [value]
        if isinstance(value, str):
            stripped_value = value.strip()
            if stripped_value != value:
                value_candidates.append(stripped_value)
            try:
                value_candidates.insert(0, int(stripped_value))
            except ValueError:
                pass

        for candidate in value_candidates:
            try:
                return self.enum_class(candidate)
            except (ValueError, TypeError):
                continue
        return None

    def _coerce_member(self, value: Any) -> Any:
        if value is None:
            return None

        for mode in ("name", "value"):
            member = self._decode(value, mode)
            if member is not None:
                return member

        if self.strict:
            raise ValueError(f"Cannot bind {value!r} as {self.enum_class.__name__}")
        return value

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        member = self._coerce_member(value)
        if member is None:
            return None
        if isinstance(member, self.enum_class):
            if self.storage_mode == "name":
                return member.name
            return str(member.value)
        return str(member)

    def process_result_value(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        for mode in self.read_modes:
            member = self._decode(value, mode)
            if member is not None:
                return member
        if self.strict:
            raise ValueError(f"Cannot decode {value!r} as {self.enum_class.__name__}")
        return value


def get_type_name(fd):
    """获取 FieldDescriptor 的 type_name"""
    if fd.type == fd.TYPE_MESSAGE and hasattr(fd, "message_type") and fd.message_type:
        return f".{fd.message_type.full_name}"
    elif fd.type == fd.TYPE_ENUM and hasattr(fd, "enum_type") and fd.enum_type:
        return f".{fd.enum_type.full_name}"
    else:
        return ""  # 基础类型没有 type_name


def _to_field_proto(fd) -> descriptor_pb2.FieldDescriptorProto:
    fd_proto = descriptor_pb2.FieldDescriptorProto()
    fd_proto.name = fd.name
    fd_proto.number = fd.number
    fd_proto.label = fd.label
    fd_proto.type_name = get_type_name(fd)
    fd_proto.type = fd.type
    return fd_proto


def _to_message_desc(proto) -> descriptor_pb2.DescriptorProto:
    descriptor = proto.DESCRIPTOR  # 这是 google.protobuf.descriptor.Descriptor 对象
    # 转为 DescriptorProto
    descriptor_proto = descriptor_pb2.DescriptorProto()
    descriptor.CopyToProto(descriptor_proto)
    return descriptor_proto


def model2protobuf(model: BaseModel, proto: ProtobufMessage) -> ProtobufMessage:
    # 转为 DescriptorProto
    descriptor_proto = _to_message_desc(proto)

    def _convert_value(fd, value):
        if value is None:
            return _get_default_value(fd, descriptor_proto)
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
            elif fd.message_type.full_name == Struct.DESCRIPTOR.full_name:
                return MessageToDict(AnyTransformer.python_to_struct(value))
            elif fd.message_type.full_name == ListValue.DESCRIPTOR.full_name:
                return MessageToDict(AnyTransformer.python_to_listvalue(value))
            elif fd.message_type.full_name == Value.DESCRIPTOR.full_name:
                return MessageToDict(AnyTransformer.python_to_value(value))
            elif fd.message_type.full_name == FieldMask.DESCRIPTOR.full_name:
                if value is None:
                    return None
                if isinstance(value, str):
                    return value
                if isinstance(value, (list, tuple)):
                    return ",".join(str(item) for item in value if str(item))
                return str(value)
            elif fd.message_type.has_options and fd.message_type.GetOptions().map_entry:
                # Check if the key and value types are both strings
                # key_field = fd.message_type.fields_by_name['key']
                value_field = fd.message_type.fields_by_name["value"]
                # key_type = key_field.fields_by_name['key'].type
                value_type = fd.message_type.fields_by_name["value"].type
                if value_type == value_field.TYPE_STRING:
                    return scalar_map_to_dict(value)
                else:
                    nested_proto = pool.FindMessageTypeByName(fd.message_type.full_name)
                    nested_cls = message_factory.GetMessageClass(nested_proto)
                    if (
                        value_type == value_field.TYPE_MESSAGE
                        and value_field.message_type == any_pb2.Any.DESCRIPTOR
                    ):
                        return {
                            k: MessageToDict(AnyTransformer.any_type_to_protobuf(v))
                            for k, v in value.items()
                        }
                    return {
                        k: MessageToDict(model2protobuf(v, nested_cls()))
                        for k, v in value.items()
                    }
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
            fd_proto = _to_field_proto(fd)
            # fd_proto.type_name = fd.type.name

            if fd.name in d:
                field_value = getattr(model, fd.name)
                if field_value is None:
                    d[fd.name] = _get_default_value(fd_proto, descriptor_proto)
                    continue
                if fd.label == fd.LABEL_REPEATED and not is_map_field(
                    fd_proto, descriptor_proto
                ):
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


def _get_detailed_type(attr_type: Type) -> Union[Type, List[Type]]:
    """获取内嵌字段的实际类型或者元素类型

    Args:
        attr_type (Type): _description_

    Returns:
        Union[Type, List[Type]]: 单个类型或类型列表
    """
    if get_origin(attr_type) in (Union, UnionType):
        # 提取 Optional 中的实际类型（去掉 None 类型）
        types = [arg for arg in get_args(attr_type) if arg is not type(None)]
        if len(types) == 1:
            return _get_detailed_type(types[0])
        else:
            return types
    elif get_origin(attr_type) in [list, List]:
        element_type = _get_detailed_type(get_args(attr_type)[0])
        return element_type
    elif get_origin(attr_type) in [dict, Dict]:
        # key_type = _(get_args(attr_type)[0])
        value_type = _get_detailed_type(get_args(attr_type)[1])
        return value_type
    else:
        return attr_type


def _get_default_value(
    fd: descriptor_pb2.FieldDescriptorProto,
    message_desc: descriptor_pb2.DescriptorProto,
) -> Any:
    if (
        fd.label == descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED
        and not is_map_field(fd, message_desc)
    ):
        return []
    elif is_map_field(fd, message_desc):
        return {}
    elif fd.type == descriptor_pb2.FieldDescriptorProto.TYPE_ENUM:
        return 0
    elif fd.type == descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE:
        return None
    elif fd.type == descriptor_pb2.FieldDescriptorProto.TYPE_STRING:
        return ""
    elif fd.type == descriptor_pb2.FieldDescriptorProto.TYPE_BYTES:
        return b""
    elif fd.type == descriptor_pb2.FieldDescriptorProto.TYPE_BOOL:
        return False
    elif fd.type in [
        descriptor_pb2.FieldDescriptorProto.TYPE_DOUBLE,
        descriptor_pb2.FieldDescriptorProto.TYPE_FIXED32,
        descriptor_pb2.FieldDescriptorProto.TYPE_FIXED64,
        descriptor_pb2.FieldDescriptorProto.TYPE_FLOAT,
    ]:
        return 0.00
    elif fd.type in [
        descriptor_pb2.FieldDescriptorProto.TYPE_INT32,
        descriptor_pb2.FieldDescriptorProto.TYPE_INT64,
        descriptor_pb2.FieldDescriptorProto.TYPE_UINT32,
        descriptor_pb2.FieldDescriptorProto.TYPE_UINT64,
        descriptor_pb2.FieldDescriptorProto.TYPE_SINT32,
        descriptor_pb2.FieldDescriptorProto.TYPE_SINT64,
    ]:
        return 0
    else:
        return None


def _get_model_cls_by_field(
    model_cls: Type[BaseModel], field_name: str
) -> Union[Type[BaseModel], List[Type]]:
    if hasattr(model_cls, "model_rebuild"):
        model_cls.model_rebuild()

    model_fields = getattr(model_cls, "model_fields", {})
    field_info = model_fields.get(field_name)
    attr_type = getattr(field_info, "annotation", None)

    if attr_type is None:
        attr_type = get_type_hints(model_cls, include_extras=True).get(field_name)

    if attr_type is None:
        annotations = getattr(model_cls, "__annotations__", {})
        raise ValueError(f"Field {field_name} not found in {model_cls} {annotations}")

    typ = _get_detailed_type(attr_type)
    return typ


def protobuf2model(
    model_cls: Type[PydanticModel], proto: _message.Message
) -> PydanticModel:
    descriptor_proto = _to_message_desc(proto)
    # print(f"Converting {proto.DESCRIPTOR.full_name} to {model_cls.__pydantic_fields__}")

    def _convert_value(fd, value, model_cls):
        if value is None:
            return None
        if fd.type == fd.TYPE_ENUM:
            return value
        elif fd.type == fd.TYPE_MESSAGE:
            if fd.message_type.full_name == Timestamp.DESCRIPTOR.full_name:
                if value:
                    ts = Timestamp()
                    ts.FromJsonString(value)
                    return ts.ToDatetime()
            elif fd.message_type.full_name == Struct.DESCRIPTOR.full_name:
                return value if value is not None else {}
            elif fd.message_type.full_name == ListValue.DESCRIPTOR.full_name:
                return value if value is not None else []
            elif fd.message_type.full_name == Value.DESCRIPTOR.full_name:
                return value
            elif fd.message_type.full_name == FieldMask.DESCRIPTOR.full_name:
                if value is None:
                    return None
                if isinstance(value, str):
                    return [item for item in value.split(",") if item]
                if isinstance(value, dict):
                    return [str(item) for item in value.get("paths", [])]
                if isinstance(value, list):
                    return [str(item) for item in value]
                return [str(value)]
            elif fd.message_type.has_options and fd.message_type.GetOptions().map_entry:
                if not value:
                    return {}
                value_field = fd.message_type.fields_by_name["value"]
                value_type = fd.message_type.fields_by_name["value"].type
                if (
                    value_type == value_field.TYPE_MESSAGE
                    and value_field.message_type == any_pb2.Any.DESCRIPTOR
                ):
                    items = {}
                    for k, v in value.items():
                        any_instance = any_pb2.Any()
                        ParseDict(v, any_instance)
                        items[k] = AnyTransformer.protobuf_any_to_python(any_instance)
                    return items
                return {
                    k: _convert_value(
                        fd.message_type.fields_by_name["value"], v, model_cls
                    )
                    for k, v in value.items()
                }
            else:
                nested_proto = pool.FindMessageTypeByName(fd.message_type.full_name)
                nested_cls = message_factory.GetMessageClass(nested_proto)
                nested_instance = nested_cls()
                nested_model_cls = _get_model_cls_by_field(model_cls, fd.name)
                # 确保返回的是单个类型而不是类型列表
                if isinstance(nested_model_cls, list):
                    # 如果是联合类型列表，取第一个类型（通常是主类型）
                    nested_model_cls = nested_model_cls[0]
                if fd.label == fd.LABEL_REPEATED:
                    values = []
                    for item in value:
                        nested_instance = nested_cls()
                        ParseDict(item, nested_instance)
                        values.append(protobuf2model(nested_model_cls, nested_instance))
                    return values
                ParseDict(value, nested_instance)
                return protobuf2model(nested_model_cls, nested_instance)

        return value

    # Convert protobuf message to dictionary
    proto_dict = (
        MessageToDict(
            proto, preserving_proto_field_name=True, use_integers_for_enums=True
        )
        if isinstance(proto, _message.Message)
        else proto
    )

    model_data = {}
    for fd in proto.DESCRIPTOR.fields:
        field_name = fd.name
        # if field_name in proto_dict:
        value = proto_dict.get(
            field_name,
            _get_default_value(_to_field_proto(fd), descriptor_proto),
        )
        model_data[field_name] = _convert_value(fd, value, model_cls)

    # Create and return SQLModel instance
    return model_cls(**model_data)

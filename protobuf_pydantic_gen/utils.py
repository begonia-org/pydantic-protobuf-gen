#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@File    :   utils.py
@Time    :   2024/04/28 11:01:31
@Desc    :
"""

import os
import inspect
import importlib.util
from google.protobuf import descriptor_pb2


def load_module_from_file(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def scan_classes_in_directory(directory):
    class_import_paths = {}
    # 遍历目录及其子目录
    if not os.path.exists(directory):
        print(f"Directory {directory} not found")
        return class_import_paths
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                # 构建模块名和文件路径
                file_path = os.path.join(root, file)
                module_name = os.path.splitext(os.path.relpath(file_path, directory))[
                    0
                ].replace(os.sep, ".")

                # 动态加载模块
                try:
                    module = load_module_from_file(module_name, file_path)
                    # 检查模块中定义的每一个类
                    for name, obj in inspect.getmembers(module, inspect.isclass):
                        # 过滤掉从其他模块导入的类
                        if obj.__module__ == module.__name__:
                            class_import_paths[name] = f"{obj.__module__}.{name}"
                except Exception as e:
                    print(f"Error loading {module_name}: {e}")

    return class_import_paths


def get_class_import_path(directory: str, class_name: str):
    classes = scan_classes_in_directory(directory)
    for class_name, path in classes.items():
        if path.endswith(class_name):
            return path


def is_repeated_field(field) -> bool:
    """Repeated-ness for either descriptor kind.

    protobuf >= 7 removed ``FieldDescriptor.label`` from the runtime descriptor
    (``is_repeated`` is the replacement), while ``FieldDescriptorProto.label``
    is still valid.
    """
    if isinstance(field, descriptor_pb2.FieldDescriptorProto):
        return field.label == descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED
    return field.is_repeated


def is_required_field(field) -> bool:
    """Required-ness for either descriptor kind (see ``is_repeated_field``)."""
    if isinstance(field, descriptor_pb2.FieldDescriptorProto):
        return field.label == descriptor_pb2.FieldDescriptorProto.LABEL_REQUIRED
    return field.is_required


def field_descriptor_to_proto(field) -> descriptor_pb2.FieldDescriptorProto:
    """Normalize a runtime ``FieldDescriptor`` into a ``FieldDescriptorProto``.

    Runtime descriptors expose ``message_type`` / ``enum_type`` instead of
    ``type_name``, so consumers keyed on ``type_name`` (type mapping,
    ``is_map_field``) cannot read them directly — every such branch would fall
    through to a fallback instead of the real type. A ``FieldDescriptorProto``
    argument is returned unchanged.
    """
    if isinstance(field, descriptor_pb2.FieldDescriptorProto):
        return field

    fd_proto = descriptor_pb2.FieldDescriptorProto()
    fd_proto.name = field.name
    fd_proto.number = field.number
    fd_proto.type = field.type
    fd_proto.label = (
        descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED
        if is_repeated_field(field)
        else descriptor_pb2.FieldDescriptorProto.LABEL_REQUIRED
        if is_required_field(field)
        else descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    )
    if field.type == descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE:
        message_type = getattr(field, "message_type", None)
        if message_type is not None:
            fd_proto.type_name = f".{message_type.full_name}"
    elif field.type == descriptor_pb2.FieldDescriptorProto.TYPE_ENUM:
        enum_type = getattr(field, "enum_type", None)
        if enum_type is not None:
            fd_proto.type_name = f".{enum_type.full_name}"
    return fd_proto


def is_map_field(
    field_desc: descriptor_pb2.FieldDescriptorProto,
    message_desc: descriptor_pb2.DescriptorProto,
):
    # if field_desc.type != descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE:
    #     return False

    type_name = field_desc.type_name
    if type_name.startswith("."):
        type_name = type_name[1:]

    nested_type_name = type_name.split(".")[-1]
    for nested in message_desc.nested_type:
        # print(f"Checking nested type: {nested.name} against {nested_type_name}")
        if nested.name == nested_type_name:
            if hasattr(nested.options, "map_entry") and nested.options.map_entry:
                return True

    return False


# 替换为你的目标目录路径
if __name__ == "__main__":
    classes = scan_classes_in_directory(
        "/data/work/begonia-org/pydantic-protobuf/example/models"
    )
    print(classes)

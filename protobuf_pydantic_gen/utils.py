#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File    :   utils.py
@Time    :   2024/04/28 11:01:31
@Desc    :   
'''

import os
import inspect
import importlib.util


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
            if file.endswith('.py'):
                # 构建模块名和文件路径
                file_path = os.path.join(root, file)
                module_name = os.path.splitext(os.path.relpath(file_path, directory))[
                    0].replace(os.sep, '.')

                # 动态加载模块
                try:
                    module = load_module_from_file(module_name, file_path)
                    # 检查模块中定义的每一个类
                    for name, obj in inspect.getmembers(module, inspect.isclass):
                        # 过滤掉从其他模块导入的类
                        if obj.__module__ == module.__name__:
                            class_import_paths[name] = f'{obj.__module__}.{name}'
                except Exception as e:
                    print(f"Error loading {module_name}: {e}")

    return class_import_paths


def get_class_import_path(directory: str, class_name: str):
    classes = scan_classes_in_directory(directory)
    for class_name, path in classes.items():
        if path.endswith(class_name):
            return path


# 替换为你的目标目录路径
if __name__ == '__main__':
    classes = scan_classes_in_directory(
        '/data/work/begonia-org/pydantic-protobuf/example/models')
    print(classes)

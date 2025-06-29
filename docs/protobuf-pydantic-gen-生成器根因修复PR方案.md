# protobuf-pydantic-gen 生成器根因修复 PR 方案

## 1. 范围

这份文档只列需要改 `protobuf-pydantic-gen` 生成器本身的点，不展开业务 SDK 侧兼容 shim，也不讨论旧生成物如何手工补丁。

目标是把当前已经确认的两个生成器根因集中整理成一份可单独提 PR 的清单：

1. `FieldMask` 特殊类型未映射
2. message 内嵌 enum 未递归生成

## 2. 问题清单

### 2.1 FieldMask 被当成普通 message 处理

症状：

- 生成结果出现 `Optional[FieldMask]`
- `_model.py` 导入时在 `model_rebuild()` 阶段失败

根因：

- `FieldMask` 没进入 `SPECIAL_PROTOBUF_TYPES`
- 运行时双向转换层没覆盖 `FieldMask`

### 2.2 message-scoped enum 没有进入模型生成流程

症状：

- proto 中合法存在的 `HealthCheckResponse.ServingStatus` 没有生成到 `_model.py`
- 对应字段注解引用未定义符号

根因：

- `extract_messages_from_file()` 只处理了 `proto_file.enum_type`
- 没有递归遍历 `DescriptorProto.enum_type` 与 `nested_type`

## 3. 需要改动的生成器文件

### 3.1 `protobuf_pydantic_gen/constants.py`

职责：补齐特殊 protobuf 类型映射。

需要新增：

```python
".google.protobuf.FieldMask": "List[str]",
```

### 3.2 `protobuf_pydantic_gen/ext.py`

职责：补齐 Python model 与 protobuf message 之间的双向转换。

需要改动：

- 导入 `FieldMask`
- `model2protobuf()` 中把 `List[str]` 转成 protobuf JSON 语义接受的逗号分隔字符串
- `protobuf2model()` 中把字符串或容错输入还原成 `List[str]`

### 3.3 `protobuf_pydantic_gen/message_processor.py`

职责：补齐 nested enum 的发现与输出。

需要改动：

- 新增递归 helper，用于提取 message 内声明的 enums
- 在每个 message 输出前，先追加其 nested enums
- 跳过 `map_entry` message，避免误生成 protobuf map 辅助结构

### 3.4 `protobuf_pydantic_gen/type_mapper.py`

职责：复用 `SPECIAL_PROTOBUF_TYPES` 现有逻辑，不一定需要新增代码，但需要确认无需额外分支。

需要确认的约束：

- `get_field_type()` 正常读取 `.google.protobuf.FieldMask`
- `get_message_info()` 遇到特殊类型时不会再生成 message import 依赖

## 4. 建议实现方式

### 4.1 FieldMask

生成阶段：

- `.google.protobuf.FieldMask -> List[str]`

运行阶段：

- model -> protobuf: `List[str] -> "a,b,c"`
- protobuf -> model: `"a,b,c" -> ["a", "b", "c"]`

### 4.2 nested enum

遍历顺序建议：

1. 先处理 file-level enums
2. 再遍历每个 top-level message
3. 对每个 message 递归提取其内部 enums
4. 最后输出 message 本身

这样做的好处：

- message 字段引用 enum 时，前面已经有对应 Python 符号
- 维持现有输出结构，改动面最小

## 5. 伪代码

```python
def extract_messages_from_file(proto_file, imports, type_mapping):
    messages = []

    for enum_desc in proto_file.enum_type:
        messages.append(_process_enum(enum_desc, ...))

    for message_desc in proto_file.message_type:
        for enum_desc in _extract_nested_enums(message_desc):
            messages.append(_process_enum(enum_desc, ...))

        messages.append(_process_message(message_desc, ...))

    return messages


def _extract_nested_enums(message_desc):
    enums = list(message_desc.enum_type)
    for nested in message_desc.nested_type:
        if nested.options.map_entry:
            continue
        enums.extend(_extract_nested_enums(nested))
    return enums
```

## 6. 测试清单

### 6.1 生成结果测试

- `FieldMask` 字段生成成 `Optional[List[str]]`
- message 内嵌 enum 在 `_model.py` 中存在 `class Xxx(_Enum)`

### 6.2 导入测试

- 直接导入依赖 `FieldMask` 的模型文件
- 直接导入依赖 nested enum 的模型文件
- 执行 `from stew import *`

### 6.3 roundtrip 测试

- `FieldMask(paths=[...]) -> model -> protobuf`
- nested enum 字段 `protobuf -> model` 正常保留枚举值

### 6.4 全量扫描测试

- 扫描所有 `*_pb2` 中 message-scoped enums
- 检查对应 `_model.py` 是否都已生成
- 期望 `MISSING_COUNT == 0`

## 7. 非目标

这份 PR 不处理：

- 旧生成物已经落盘但未重生的问题
- 业务仓库里为兼容旧生成器而加的临时 shim
- 其他尚未暴露为 import failure 的 well-known types

## 8. 建议 PR 标题

```text
Fix FieldMask and nested enum generation for Pydantic models
```

## 9. 建议 PR 描述

```markdown
## Summary

This PR fixes two generator-level issues in protobuf-pydantic-gen:

- `google.protobuf.FieldMask` is now emitted as `List[str]`
- enums declared inside protobuf messages are now recursively emitted into generated model files

## Why

These two gaps still break generated Python SDK imports under Pydantic v2:

- `FieldMask` was emitted as `Optional[FieldMask]`
- nested enums were missing from `_model.py`

## Validation

- direct model imports pass
- `FieldMask` roundtrip passes
- nested enum scan reports no missing generated enums
```
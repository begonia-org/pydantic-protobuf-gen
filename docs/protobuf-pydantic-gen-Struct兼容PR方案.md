# protobuf-pydantic-gen 针对 Pydantic v2 的 Struct 兼容 PR 方案

## 1. 背景

当前 Python SDK 的生成模型在直接导入部分 `_model.py` 文件时，会因为 `google.protobuf.Struct`、`google.protobuf.ListValue`、`google.protobuf.Value` 的类型生成策略不兼容 Pydantic v2 而失败。

典型表现包括：

- `NameError: name 'Struct' is not defined`
- `PydanticUndefinedAnnotation: name 'Struct' is not defined`
- `PydanticSchemaGenerationError: Unable to generate pydantic-core schema for <class 'google.protobuf.struct_pb2.Struct'>`

这类问题不是业务代码问题，而是 `protobuf_pydantic_gen` 对 protobuf JSON well-known types 的建模方式不正确导致的生成器问题。

## 2. 现象与复现

以生成后的 `payment_model.py`、`entitlement_model.py`、`authorization_model.py` 为例，存在如下字段：

- `metadata: Optional[Struct]`
- `config: Optional[Struct]`
- `claims: Optional[Struct]`

在当前生成策略下，模块导入后会立刻执行：

```python
SomeModel.model_rebuild()
```

而 `Struct` 又被作为 protobuf 运行时类型暴露给 Pydantic 模型，导致：

1. 生成文件若缺少 `Struct` 导入，会先在注解求值阶段失败。
2. 即便补上导入，Pydantic v2 仍无法为 `google.protobuf.struct_pb2.Struct` 自动生成 schema。
3. `protobuf2model` / `model2protobuf` 还会继续把这类字段当作“嵌套 Pydantic 子模型”处理，进一步放大问题。

## 3. 根因分析

问题链条主要有三段。

### 3.1 特殊类型映射不完整

在生成器常量中，当前仅把 `Timestamp` 视为特殊 protobuf 类型：

- `.google.protobuf.Timestamp -> datetime.datetime`

但 `Struct`、`ListValue`、`Value` 仍按普通 message 处理。

这会导致生成器输出：

- `Optional[Struct]`
- `Optional[ListValue]`
- `Optional[Value]`

而不是更适合 Pydantic 的 JSON 原生类型。

### 3.2 模板在导入阶段立即重建模型

模板会对每个模型执行：

```python
ModelName.model_rebuild()
```

这意味着只要注解里出现不可求值或不可建 schema 的类型，模块在导入阶段就会直接失败。

### 3.3 运行时转换把 Struct 当普通嵌套 message 处理

`protobuf2model()` 和 `model2protobuf()` 当前对大多数 message 使用统一递归逻辑：

- message -> 嵌套模型
- repeated message -> 模型列表
- map message -> 递归 map value

但 `Struct/ListValue/Value` 本质上是 JSON 容器，不应走“嵌套 Pydantic 子模型”的路径。

## 4. 设计目标

本 PR 的目标不是给生成结果打补丁，而是在生成器层面修正类型建模。

目标如下：

1. 让 `Struct/ListValue/Value` 在生成结果中表现为 JSON 原生类型。
2. 避免要求业务方为 Pydantic v2 单独开启 `arbitrary_types_allowed`。
3. 保持 `Timestamp` 的现有行为不变。
4. 保持 `model2protobuf` 和 `protobuf2model` 的 roundtrip 语义不变。
5. 让生成结果可直接导入，不依赖后置手工修补。

## 5. 推荐方案

推荐方案是：

- 在生成阶段把 protobuf JSON well-known types 映射为 Python 原生 JSON 类型。
- 在运行阶段为这些类型提供专门的双向转换逻辑。

### 5.1 生成阶段类型映射

建议将下列 protobuf 类型纳入特殊映射：

| Protobuf 类型 | 生成后的 Python 类型 |
|---|---|
| `.google.protobuf.Struct` | `Dict[str, Any]` |
| `.google.protobuf.ListValue` | `List[Any]` |
| `.google.protobuf.Value` | `Any` |
| `.google.protobuf.Timestamp` | `datetime.datetime` |

这样生成后的字段将变为：

```python
metadata: Optional[Dict[str, Any]] = _Field(default=None)
config: Optional[Dict[str, Any]] = _Field(default=None)
payload: Optional[List[Any]] = _Field(default=None)
value: Optional[Any] = _Field(default=None)
```

而不再暴露 protobuf 运行时类型。

### 5.2 运行阶段转换逻辑

在 `model2protobuf()` 和 `protobuf2model()` 中，对三类 JSON well-known types 做专门分支：

- `Struct` 接收和返回 `dict`
- `ListValue` 接收和返回 `list`
- `Value` 接收和返回 Python 标量 / `dict` / `list`

这些类型不再进入“递归构造嵌套 Pydantic 模型”的通用分支。

## 6. 代码改动建议

### 6.1 修改 constants.py

文件：`protobuf_pydantic_gen/constants.py`

将 `SPECIAL_PROTOBUF_TYPES` 从：

```python
SPECIAL_PROTOBUF_TYPES = {
    ".google.protobuf.Timestamp": "datetime.datetime",
}
```

扩展为：

```python
SPECIAL_PROTOBUF_TYPES = {
    ".google.protobuf.Timestamp": "datetime.datetime",
    ".google.protobuf.Struct": "Dict[str, Any]",
    ".google.protobuf.ListValue": "List[Any]",
    ".google.protobuf.Value": "Any",
}
```

同时确保生成器会补齐对应的 typing import：

- `Any`
- `Dict`
- `List`

### 6.2 修改 type_mapper.py

文件：`protobuf_pydantic_gen/type_mapper.py`

#### 改动点 A

在 `get_field_type()` 中，命中特殊类型时直接返回映射后的 Python 类型。

#### 改动点 B

在 `get_message_info()` 中，如果字段类型属于 `SPECIAL_PROTOBUF_TYPES`，直接返回空字典：

```python
if field.type_name in SPECIAL_PROTOBUF_TYPES:
    return {}
```

目的：避免后续生成链把这些字段继续当成“嵌套 message 依赖”。

### 6.3 修改 ext.py

文件：`protobuf_pydantic_gen/ext.py`

#### 在 model2protobuf() 中新增 JSON well-known type 分支

在 message 分支里优先处理：

- `fd.message_type.full_name == Struct.DESCRIPTOR.full_name`
- `fd.message_type.full_name == ListValue.DESCRIPTOR.full_name`
- `fd.message_type.full_name == Value.DESCRIPTOR.full_name`

建议逻辑：

```python
elif fd.type == fd.TYPE_MESSAGE:
    if fd.message_type.full_name == Struct.DESCRIPTOR.full_name:
        return value
    if fd.message_type.full_name == ListValue.DESCRIPTOR.full_name:
        return value
    if fd.message_type.full_name == Value.DESCRIPTOR.full_name:
        return value
```

这些值最终可以继续交给 `ParseDict()` 写回 protobuf。

#### 在 protobuf2model() 中新增 JSON well-known type 分支

在 `_convert_value()` 中优先处理：

```python
if fd.message_type.full_name == Struct.DESCRIPTOR.full_name:
    return value or {}
if fd.message_type.full_name == ListValue.DESCRIPTOR.full_name:
    return value or []
if fd.message_type.full_name == Value.DESCRIPTOR.full_name:
    return value
```

这样这些字段直接保持 JSON 原生语义，不再走 `nested_model_cls` 递归逻辑。

### 6.4 模板层不建议引入 arbitrary_types_allowed

文件：`protobuf_pydantic_gen/template.j2`

不建议在模板中把：

```python
model_config = ConfigDict(protected_namespaces=())
```

改成：

```python
model_config = ConfigDict(protected_namespaces=(), arbitrary_types_allowed=True)
```

原因：

1. 这只是放宽校验，不是修正类型建模。
2. 即便允许 arbitrary types，业务模型仍会暴露 protobuf 运行时类型，体验较差。
3. 这会掩盖 `Struct/ListValue/Value` 被错误建模的问题。

因此推荐保留模板主体不变，把问题收敛在类型映射和转换层。

## 7. 参考改动草案

### 7.1 constants.py

```python
SPECIAL_PROTOBUF_TYPES: Dict[str, str] = {
    ".google.protobuf.Timestamp": "datetime.datetime",
    ".google.protobuf.Struct": "Dict[str, Any]",
    ".google.protobuf.ListValue": "List[Any]",
    ".google.protobuf.Value": "Any",
}
```

### 7.2 type_mapper.py

```python
def get_message_info(self, field):
    if getattr(field, "type_name", "") in SPECIAL_PROTOBUF_TYPES:
        return {}
    ...
```

### 7.3 ext.py 中 protobuf2model()

```python
if fd.type == fd.TYPE_MESSAGE:
    if fd.message_type.full_name == Struct.DESCRIPTOR.full_name:
        return value or {}
    if fd.message_type.full_name == ListValue.DESCRIPTOR.full_name:
        return value or []
    if fd.message_type.full_name == Value.DESCRIPTOR.full_name:
        return value
```

### 7.4 ext.py 中 model2protobuf()

```python
elif fd.type == fd.TYPE_MESSAGE:
    if fd.message_type.full_name == Struct.DESCRIPTOR.full_name:
        return value
    if fd.message_type.full_name == ListValue.DESCRIPTOR.full_name:
        return value
    if fd.message_type.full_name == Value.DESCRIPTOR.full_name:
        return value
```

## 8. 测试方案

建议在生成器仓库里新增三类测试。

### 8.1 导入测试

目标：验证生成结果可直接导入。

用例：

- 含 `Struct` 字段的模型文件可直接 `import`
- 含 `ListValue` 字段的模型文件可直接 `import`
- 含 `Value` 字段的模型文件可直接 `import`

通过标准：模块导入阶段不触发：

- `NameError`
- `PydanticUndefinedAnnotation`
- `PydanticSchemaGenerationError`

### 8.2 protobuf -> model 转换测试

目标：验证 `protobuf2model()` 输出的是 JSON 原生类型。

用例：

- `Struct` -> `dict`
- `ListValue` -> `list`
- `Value` -> 标量 / `dict` / `list`

### 8.3 model -> protobuf roundtrip 测试

目标：验证 `model2protobuf()` 和 `protobuf2model()` 往返后语义一致。

用例：

```python
{"a": 1, "b": True, "c": [1, 2], "d": {"nested": "x"}}
```

通过标准：

- roundtrip 后结构不丢失
- 基本标量类型保持一致

## 9. 兼容性评估

本方案对外兼容性总体较好。

### 正向影响

1. 生成模型更符合 Python / Pydantic 的自然使用方式。
2. 业务代码不再需要感知 protobuf `Struct` 运行时类型。
3. 避免了 Pydantic v2 对 arbitrary protobuf types 的 schema 限制。

### 潜在变化

1. 之前如果业务代码显式依赖 `Struct` 运行时对象类型，升级后会改为使用 `dict`。
2. 但从生成 SDK 的使用体验和 API 边界看，这种变化是合理且推荐的。

结论：这属于“修正生成器类型抽象”的兼容性改善，而非破坏性设计变更。

## 10. 不推荐的替代方案

以下方案不建议作为正式 PR 主方案：

### 10.1 只补导入

例如给生成文件补：

```python
from google.protobuf.struct_pb2 import Struct
```

这只能解决未定义符号，不能解决 Pydantic v2 schema 生成问题。

### 10.2 全局开启 arbitrary_types_allowed

例如：

```python
model_config = ConfigDict(
    protected_namespaces=(),
    arbitrary_types_allowed=True,
)
```

这只是放宽限制，不是修正建模错误。

### 10.3 在生成结果上逐文件打补丁

这会导致：

- 无法稳定回归
- 每次重新生成都会丢失修复
- 无法作为生成器层面的长期解法提交

## 11. 建议的 PR 标题

可选标题：

```text
Treat protobuf Struct/ListValue/Value as native JSON types in generated Pydantic models
```

或：

```text
Fix Pydantic v2 compatibility for protobuf JSON well-known types
```

## 12. 建议的 PR 描述摘要

可直接用于提交说明：

```markdown
## Summary

This PR fixes Pydantic v2 compatibility for protobuf JSON well-known types in generated models.

Instead of emitting google.protobuf.Struct/ListValue/Value as arbitrary protobuf runtime types, the generator now maps them to native Python JSON types:

- Struct -> Dict[str, Any]
- ListValue -> List[Any]
- Value -> Any

The runtime conversion layer is updated accordingly so model2protobuf/protobuf2model still roundtrip correctly.

## Why

Generated models currently fail during import or model_rebuild() under Pydantic v2 because protobuf Struct types are treated as arbitrary message classes instead of JSON containers.

## Result

- Generated models import cleanly under Pydantic v2
- No need to enable arbitrary_types_allowed globally
- JSON-like protobuf fields behave like native Python dict/list/scalar values
```

## 13. 结论

推荐把这次修复定义为：

- 生成器层面的类型建模修正
- 运行时转换层面的 JSON 容器特判

而不是：

- 模板层的宽松兜底
- 生成结果层的手工修补

这样提交出去的 PR 更稳，也更容易被上游接受。
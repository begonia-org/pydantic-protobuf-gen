# protobuf-pydantic-gen FieldMask 兼容 PR 方案

## 1. 目标

这份 PR 不是重新修 `Struct`。

当前本地已升级的生成器版本已经完成了以下能力：

- `.google.protobuf.Struct -> Dict[str, Any]`
- `.google.protobuf.ListValue -> List[Any]`
- `.google.protobuf.Value -> Any`
- `model2protobuf()` / `protobuf2model()` 已对上述 JSON well-known types 做了特判

当前剩余的生成器问题已经转移为：

- `google.protobuf.FieldMask` 仍按普通 message 生成
- 生成结果中出现 `Optional[FieldMask]`
- `_model.py` 在 `model_rebuild()` 阶段因 `FieldMask` 未定义而失败

因此，这份 PR 的目标是：

1. 在现有 `Struct/ListValue/Value` 修复方案基础上，按同样思路补齐 `FieldMask`
2. 让生成后的 Python SDK 模型将 `FieldMask` 暴露为自然的 Python 类型，而不是 protobuf runtime type
3. 消除 `user_model.py` 等文件在导入阶段的 `FieldMask` 未定义问题

## 2. 当前现象

以生成后的 [proto/sdk/python/stew/api/v1/user_model.py](proto/sdk/python/stew/api/v1/user_model.py) 为例，当前存在如下字段：

```python
update_mask: Optional[FieldMask] = _Field(default=None)
```

而模板会在模块末尾立即执行：

```python
PostUserRequest.model_rebuild()
PatchUserRequest.model_rebuild()
```

结果在直接导入时触发：

```text
PydanticUndefinedAnnotation: name 'FieldMask' is not defined
```

这说明：

- `FieldMask` 还没有像 `Struct` 一样进入生成器的特殊类型处理链
- 当前失败点已经不是 `Struct`，而是 `FieldMask`

## 3. 设计原则

### 3.1 不暴露 protobuf runtime 类型

生成后的 Pydantic 模型不应把 `google.protobuf.FieldMask` 暴露给业务代码。

### 3.2 使用 Python 自然类型表达更新路径

`FieldMask` 的 protobuf 定义本质是：

```proto
message FieldMask {
  repeated string paths = 1;
}
```

因此，在 Python SDK 边界上最自然的表达是：

```python
List[str]
```

而不是 `FieldMask` message 本身。

### 3.3 与现有 TS SDK 语义保持一致

当前 TypeScript 生成物已经把 `FieldMask` 暴露为 `string[]`，并通过 `wrap/unwrap` 做消息层转换。

因此 Python 侧最合理的对应是：

- Python model: `List[str]`
- protobuf message: `google.protobuf.FieldMask`

## 4. 推荐方案

推荐把 `FieldMask` 纳入特殊 protobuf 类型映射，并在运行时转换层增加专门分支。

### 4.1 生成阶段映射

将：

```text
.google.protobuf.FieldMask
```

映射为：

```text
List[str]
```

生成后模型应表现为：

```python
update_mask: Optional[List[str]] = _Field(default=None)
```

### 4.2 运行阶段转换

在 `model2protobuf()` 中：

- `List[str]` -> `"path1,path2,path3"`

在 `protobuf2model()` 中：

- `"path1,path2,path3"` -> `List[str]`

原因是 protobuf JSON 语义里 `FieldMask` 的 JSON 表达是逗号分隔字符串，而不是对象结构。

## 5. 代码改动建议

### 5.1 修改 constants.py

文件：`protobuf_pydantic_gen/constants.py`

在 `SPECIAL_PROTOBUF_TYPES` 中新增：

```python
".google.protobuf.FieldMask": "List[str]",
```

变更后建议如下：

```python
SPECIAL_PROTOBUF_TYPES: Dict[str, str] = {
    ".google.protobuf.Timestamp": "datetime.datetime",
    ".google.protobuf.Struct": "Dict[str, Any]",
    ".google.protobuf.ListValue": "List[Any]",
    ".google.protobuf.Value": "Any",
    ".google.protobuf.FieldMask": "List[str]",
}
```

这一步的作用是：

- 生成结果直接产出 `Optional[List[str]]`
- 避免继续生成 `Optional[FieldMask]`

### 5.2 修改 type_mapper.py

文件：`protobuf_pydantic_gen/type_mapper.py`

当前 `Struct/ListValue/Value` 已通过 `SPECIAL_PROTOBUF_TYPES` 进入特殊路径，`FieldMask` 应复用同一机制。

如果 `SPECIAL_PROTOBUF_TYPES` 中加入 `FieldMask`，下面两处逻辑会自动吃到：

1. `get_field_type()`
2. `get_message_info()`

因此这一步通常不需要额外分支，只需确保：

```python
if getattr(field, "type_name", "") in SPECIAL_PROTOBUF_TYPES:
    return {}
```

继续适用于 `FieldMask`。

### 5.3 修改 ext.py

文件：`protobuf_pydantic_gen/ext.py`

这是这次 PR 的核心增量。

#### 5.3.1 model2protobuf()

在 `fd.type == fd.TYPE_MESSAGE` 分支中，增加：

```python
elif fd.message_type.full_name == FieldMask.DESCRIPTOR.full_name:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        return ",".join(str(item) for item in value if str(item))
    return str(value)
```

说明：

- Python model 层暴露 `List[str]`
- 进入 `ParseDict()` 前转成 protobuf JSON 语义接受的字符串

#### 5.3.2 protobuf2model()

在 `_convert_value()` 中增加：

```python
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
```

说明：

- 标准 `MessageToDict()` 路径下，`FieldMask` 通常会被序列化为逗号分隔字符串
- 为了兼容不同调用面，保留对 dict/list 输入的容错支持

### 5.4 ext.py 需要补充导入

如果当前 `ext.py` 尚未导入 `FieldMask`，则需补充：

```python
from google.protobuf.field_mask_pb2 import FieldMask
```

## 6. 为什么不映射成 str

也可以把 `FieldMask` 生成为 `str`，但不推荐。

原因：

1. `FieldMask` 的结构本体是 `repeated string paths`
2. 使用层更自然的输入是：

```python
["name", "email", "avatar"]
```

而不是：

```python
"name,email,avatar"
```

3. 现有 TS SDK 已经把它处理成 `string[]`

因此 Python SDK 保持 `List[str]` 更一致。

## 7. 与 Struct 方案的关系

这次 PR 不应重复宣称“修复 Struct 兼容”。

更准确的定位应是：

- 第一阶段已完成：`Struct/ListValue/Value`
- 第二阶段补齐：`FieldMask`

也就是说，这是一份 **增量 PR**。

## 8. 预期生成结果

以 `PostUserRequest` / `PatchUserRequest` 为例，生成后应变成：

```python
class PostUserRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    ...
    update_mask: Optional[List[str]] = _Field(default=None)

class PatchUserRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    ...
    update_mask: Optional[List[str]] = _Field(default=None)
```

这将直接消除 `FieldMask` 未定义注解问题。

## 9. 测试方案

### 9.1 导入测试

目标：验证 `_model.py` 不再因 `FieldMask` 失败。

用例：

- 直接导入 `user_model.py`
- 直接导入依赖 `user_model.py` 的 `authorization_model.py`

通过标准：

- 不再触发 `PydanticUndefinedAnnotation: name 'FieldMask' is not defined`

### 9.2 注解测试

目标：验证生成结果类型符合预期。

断言示例：

```python
PostUserRequest.model_fields["update_mask"].annotation == Optional[List[str]]
PatchUserRequest.model_fields["update_mask"].annotation == Optional[List[str]]
```

### 9.3 protobuf -> model 测试

给 `FieldMask(paths=["name", "email"])`，断言：

```python
model.update_mask == ["name", "email"]
```

### 9.4 model -> protobuf 测试

给模型：

```python
PatchUserRequest(update_mask=["name", "email"])
```

断言转回 protobuf 后：

```python
proto.update_mask.paths == ["name", "email"]
```

## 10. 兼容性说明

这项改动属于生成器类型抽象修正，兼容性风险较低。

### 正向收益

1. 生成模型不再暴露 `FieldMask` protobuf runtime type
2. 直接导入 `_model.py` 可通过
3. SDK 使用层接口更自然
4. 与 TS 侧 `string[]` 语义保持一致

### 行为变化

若已有业务代码显式依赖：

```python
google.protobuf.field_mask_pb2.FieldMask
```

作为模型字段值，则升级后需要改为：

```python
["field_a", "field_b"]
```

这属于合理且推荐的 API 收敛。

## 11. 建议 PR 标题

可选标题：

```text
Add FieldMask native list[str] support for generated Pydantic models
```

或：

```text
Fix Pydantic model generation for protobuf FieldMask
```

## 12. 建议 PR 描述

可直接用于提交：

```markdown
## Summary

This PR extends the existing well-known type compatibility layer by adding native `FieldMask` support to generated Pydantic models.

`google.protobuf.FieldMask` is now treated as `List[str]` at the Python model boundary, instead of being emitted as a protobuf runtime type.

The runtime conversion layer is updated accordingly:

- model -> protobuf: `List[str]` becomes a comma-separated FieldMask JSON string
- protobuf -> model: FieldMask JSON string becomes `List[str]`

## Why

After `Struct/ListValue/Value` support was added, the next import-time failure moved to `FieldMask`, which is still generated as `Optional[FieldMask]` and fails during `model_rebuild()`.

## Result

- `user_model.py` can be imported directly under Pydantic v2
- `update_mask` becomes `Optional[List[str]]`
- Python SDK behavior matches the existing TypeScript `string[]` wrapper semantics
```

## 13. 结论

这份 PR 应该被描述为：

- 对当前 well-known type 兼容层的继续补齐
- 重点修复 `FieldMask`
- 不再重复包装成 `Struct` 主修复 PR

如果后续还有 `Duration`、`BytesValue`、`StringValue` 等 well-known types 的一致性治理，可以继续沿着同一套模式推进：

- 生成阶段映射为自然 Python 类型
- 运行阶段补齐双向转换
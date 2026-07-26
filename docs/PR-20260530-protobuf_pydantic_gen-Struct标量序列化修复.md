# PR 文档（protobuf_pydantic_gen 侧）：修复 google.protobuf.Struct 标量值序列化失败

日期：2026-05-30
状态：待提交到 protobuf_pydantic_gen 仓库
关联业务仓排查：排查-20260530-OOB计费上报protobuf序列化失败

## 1. 背景

业务侧使用 protobuf_pydantic_gen 生成的 Pydantic 模型，并通过生成的 `to_protobuf()` 方法将模型转换为 protobuf message。

在线上 OOB 计费主动上报链路中，`BillingReport` 的以下字段在 proto 中定义为 `google.protobuf.Struct`：

1. `business_factors`
2. `provider_usage_facts`
3. `execution_hints`

当这些字段包含普通标量值（如 `int`、`bool`、`str`）时，`to_protobuf()` 当前会抛出：

```text
AttributeError: 'int' object has no attribute 'model_dump'
```

这说明问题不在业务侧组装层，而在 protobuf_pydantic_gen 的 `Struct` 序列化运行时边界。

## 2. 最小复现

```python
from stew.api.v1 import billing_common_model as billing_model

report = billing_model.BillingReport(
    business_id="b",
    request_id="r",
    user_id="u",
    usage_source=billing_model.BillingUsageSource.BILLING_USAGE_SOURCE_ACTUAL,
    final_status=billing_model.BillingFinalStatus.BILLING_FINAL_STATUS_SUCCESS,
    dedupe_key="d",
    raw_usage_totals=billing_model.BillingUsageTotals(meters={"x": 1}),
    cost_breakdown=billing_model.BillingCostBreakdown(line_items={"x": 1}, total_cost_micros=1),
    business_factors={"chunk_count": 1},
)

report.to_protobuf()  # -> AttributeError: 'int' object has no attribute 'model_dump'
```

复现条件很小：只要 `google.protobuf.Struct` 对应的 `Dict[str, Any]` 中出现标量值即可。

## 3. 根因

根因位于 protobuf_pydantic_gen 的 `Dict[str, Any] -> google.protobuf.Struct` 转换逻辑。

当前实现等价于把字典中的 value 普遍视为“可继续 `model_dump()` 的对象”，但 `Struct` 的值域本质上应当是 protobuf `Value` 联合类型，对应以下 Python 运行时类型：

1. `None`
2. `bool`
3. `int` / `float`
4. `str`
5. `dict` / `Mapping`
6. `list` / `Sequence`

也就是说，`Struct` 不是“字典值必须是 Pydantic model”的语义，而是“字典值必须是 JSON-like value”的语义。当前缺陷是缺少对标量值的显式分派，导致标量错误进入 Pydantic 递归分支并调用 `model_dump()`。

另一个容易遗漏的边界是：`bool` 在 Python 中是 `int` 的子类，因此分支顺序必须先判断 `bool`，再判断数字。

## 4. 目标

1. `google.protobuf.Struct` 字段可以稳定序列化任意 JSON-like Python 值。
2. 保留对嵌套 `dict` / `list` 的递归支持。
3. 若 `Struct` 内部嵌套的是 Pydantic 模型，仍允许先 `model_dump()` 后递归转换。
4. 不要求业务调用方手写 `Struct` 适配或规避标量值。
5. 对不支持的类型给出清晰错误，而不是泄漏 `AttributeError`。

## 5. 拟议改动

### 5.1 为 Struct/Value 增加统一的 Python 值分派函数

建议在运行时转换层增加一个统一辅助函数，例如：

```python
def _python_value_to_proto_value(value):
    ...
```

其语义应为：

1. `None` -> `Value(null_value=NullValue.NULL_VALUE)`
2. `bool` -> `Value(bool_value=value)`
3. `int | float` -> `Value(number_value=float(value))`
4. `str` -> `Value(string_value=value)`
5. `Mapping` -> 递归构造 `Struct`
6. `Sequence`（排除 `str` / `bytes` / `bytearray`）-> 递归构造 `ListValue`
7. 仅当对象真的暴露 `model_dump()` 时，先 `model_dump()` 再继续递归
8. 对其余类型抛出带类型信息的 `TypeError` 或 `ValueError`

### 5.2 由 Dict[str, Any] -> Struct 路径统一复用该函数

建议不要在 `Struct`、嵌套 `dict`、嵌套 `list` 上分别维护多套分支逻辑，而是统一走：

1. `dict` 的每个 value 调 `_python_value_to_proto_value()`
2. `list` 的每个 item 调 `_python_value_to_proto_value()`
3. `Pydantic model` 先 dump 成普通 Python 数据，再走相同递归

这样可以避免“顶层 dict 能过、嵌套 list 失败”这类分支漂移问题。

### 5.3 不建议的修复方式

以下方案不建议采用：

1. 遇到标量时直接 `str(value)`
2. 对 `Struct` 字段整体做 JSON 字符串化
3. 在调用方文档中要求手写 `google.protobuf.Struct`
4. catch `AttributeError` 后静默跳过字段

这些方式都属于绕过症状，不是修复 `Struct` 运行时语义。

## 6. 建议实现草图

以下伪代码描述期望修复语义：

```python
from collections.abc import Mapping, Sequence
from google.protobuf.struct_pb2 import ListValue, NullValue, Struct, Value


def _python_value_to_proto_value(value):
    if value is None:
        return Value(null_value=NullValue.NULL_VALUE)

    if isinstance(value, bool):
        return Value(bool_value=value)

    if isinstance(value, (int, float)):
        return Value(number_value=float(value))

    if isinstance(value, str):
        return Value(string_value=value)

    if hasattr(value, "model_dump"):
        return _python_value_to_proto_value(value.model_dump())

    if isinstance(value, Mapping):
        struct_value = Struct()
        for key, item in value.items():
            struct_value.fields[key].CopyFrom(_python_value_to_proto_value(item))
        return Value(struct_value=struct_value)

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        list_value = ListValue()
        for item in value:
            list_value.values.add().CopyFrom(_python_value_to_proto_value(item))
        return Value(list_value=list_value)

    raise TypeError(f"Unsupported Struct value type: {type(value)!r}")
```

若当前项目中已经存在通用的“Python 值 -> protobuf scalar/container”辅助函数，优先复用现有实现，避免在 `Struct` 路径再复制一套逻辑。

## 7. 验收标准

修复后应满足：

1. `Dict[str, Any]` 中包含 `int` / `bool` / `float` / `str` / `None` 时，`to_protobuf()` 不再抛错。
2. 嵌套 `dict` / `list` 可以正确递归序列化为 `Struct` / `ListValue`。
3. `Struct` 内部如果嵌套 Pydantic model，可以先 dump 再正确落到 protobuf。
4. 不支持的类型报出清晰错误信息，错误中至少包含运行时类型。
5. 现有非 `Struct` 字段的 `to_protobuf()` 行为不回归。

## 8. 建议测试用例

建议至少增加以下回归测试：

### 8.1 标量值

```python
payload = {
    "i": 1,
    "b": True,
    "f": 1.5,
    "s": "ok",
    "n": None,
}
```

断言：`to_protobuf()` 成功，且 protobuf `Struct` 中字段类型分别落到 `number_value` / `bool_value` / `string_value` / `null_value`。

### 8.2 嵌套 dict/list

```python
payload = {
    "outer": {
        "count": 2,
        "flags": [True, False],
        "items": [{"name": "a"}, {"name": "b"}],
    }
}
```

断言：嵌套 `Struct` 和 `ListValue` 均可构造成功。

### 8.3 Pydantic model 嵌套在 Struct 中

```python
class Facts(BaseModel):
    retries: int
    success: bool


payload = {"facts": Facts(retries=2, success=True)}
```

断言：模型先 dump，再正确写入 `Struct`。

### 8.4 bool 分支优先级

```python
payload = {"ok": True}
```

断言：最终落到 `bool_value`，而不是 `number_value=1`。

### 8.5 非法类型报错清晰

```python
payload = {"bad": object()}
```

断言：抛出明确的 `TypeError` 或 `ValueError`，而不是 `AttributeError`。

## 9. 兼容性说明

1. 本修复不改变 proto 契约，也不要求重新生成业务 proto。
2. 对现有 `Struct` 使用者是向后兼容的增强修复。
3. `google.protobuf.Value.number_value` 的底层语义本来就是 double，因此 `int` 在 protobuf 层表现为数值类型而非独立整数类型，这属于 `Struct` 标准语义，不是本次修复引入的新行为。

## 10. 建议 PR 标题

`fix: handle scalar values correctly when serializing Dict[str, Any] to google.protobuf.Struct`

## 11. 建议评审点

1. `bool` 与数字分支顺序是否正确。
2. `Mapping` / `Sequence` 的判定是否排除了字符串和字节串。
3. 是否只在对象真实支持 `model_dump()` 时才进入 Pydantic 分支。
4. 不支持类型是否显式失败，而非静默字符串化。
5. 修复是否覆盖所有 `Struct` 递归入口，而不是仅修补顶层字典。

# Runtime Conversion / 运行时转换

## English

### Generated Convenience Methods

Every generated model class gets:

- `to_protobuf()`
- `from_protobuf()`

Example:

```python
from example.models.example_model import Example

model = Example(name="demo", age=1)
proto = model.to_protobuf()
clone = Example.from_protobuf(proto)
```

### Runtime Helper Functions

The generated methods call helpers from `protobuf_pydantic_gen.ext`:

- `model2protobuf(model, proto)`
- `protobuf2model(model_cls, proto)`

These helpers handle nested messages, map fields, timestamps, enums, and repeated message fields.

### Forward References

Generated files postpone annotation evaluation and call `model_rebuild()` after all classes are declared. That keeps same-file forward references import-safe.

If you write your own Pydantic model and use `protobuf2model()` directly, rebuild forward references yourself when needed:

```python
class ForwardRefExample(BaseModel):
    examples: list["ForwardRefExample2"] | None = None

ForwardRefExample.model_rebuild()
```

The repository includes a regression test for this pattern in `example/tests/test_ext_forward_refs.py`.

### Enum Storage

The runtime ships `GenericEnumType` for generated enum-backed SQLAlchemy columns. The generator can emit value-based or name-based enum storage for table fields.

## 中文

### 生成类自带的方法

每个生成模型都会带有：

- `to_protobuf()`
- `from_protobuf()`

示例：

```python
from example.models.example_model import Example

model = Example(name="demo", age=1)
proto = model.to_protobuf()
clone = Example.from_protobuf(proto)
```

### 运行时辅助函数

这些方法内部调用 `protobuf_pydantic_gen.ext` 中的辅助函数：

- `model2protobuf(model, proto)`
- `protobuf2model(model_cls, proto)`

这些辅助函数会处理嵌套消息、map 字段、时间戳、枚举以及 repeated message 字段。

### 前向引用

生成文件会延后注解求值，并在所有类声明完成后调用 `model_rebuild()`，从而保证同文件前向引用在导入时仍然安全。

如果你自己手写 Pydantic 模型并直接调用 `protobuf2model()`，需要在必要时手动重建前向引用：

```python
class ForwardRefExample(BaseModel):
    examples: list["ForwardRefExample2"] | None = None

ForwardRefExample.model_rebuild()
```

仓库中对此有回归测试，见 `example/tests/test_ext_forward_refs.py`。

### 枚举存储

运行时提供了 `GenericEnumType`，用于支持生成的枚举 SQLAlchemy 列。生成器可以为表字段输出基于 `value` 或基于 `name` 的枚举持久化方式。
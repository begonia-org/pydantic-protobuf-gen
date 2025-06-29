# SQLModel Guide / SQLModel 指南

## English

### When A Message Becomes A Table Model

Set `(pydantic.database).as_table = true` on a message to emit a SQLModel table class.

Example:

```protobuf
message Example {
  option (pydantic.database) = {
    as_table: true
    table_name: "example_table"
  };
}
```

This produces a generated class shaped like:

```python
class Example(SQLModel, table=True):
    __tablename__ = "example_table"
```

### Table Name Behavior

- If `table_name` is provided, it is used directly.
- If `table_name` is omitted, the generator falls back to the snake_case form of the message name.

### Compound Constraints And Indexes

`compound_index` entries become:

- `UniqueConstraint(...)` when `index_type = "UNIQUE"`
- `PrimaryKeyConstraint(...)` when `index_type = "PRIMARY"`
- `Index(...)` for any other `index_type`

The generator also appends `{"extend_existing": True}` to `__table_args__`.

### Field-Level SQLAlchemy Hints

The most common SQL-oriented annotations are:

- `primary_key`
- `unique`
- `index`
- `nullable`
- `foreign_key`
- `sa_column_type`

`sa_column_type` is how the example schema requests JSON and vector columns:

```protobuf
repeated Example2 examples = 9 [(pydantic.field) = {
  description: "Nested message"
  sa_column_type: "JSON"
}];

repeated float embeddings = 11 [(pydantic.field) = {
  description: "Embedding vector for the example"
  sa_column_type: "Vector(1563)"
}];
```

### `tables.py` Anti-Corruption Layer

When at least one generated message is a table model and `PROTOBUF_PYDANTIC_GENERATE_TABLES=true`, the plugin emits `tables.py`.

That file re-exports table classes with an alias suffix so business code can avoid importing generated modules directly.

Example from this repository:

```python
from .example_model import Example as ExampleRow
```

The suffix is controlled by `PROTOBUF_PYDANTIC_TABLE_ALIAS_SUFFIX` and defaults to `Row`.

## 中文

### 什么时候会生成表模型

当 message 上设置 `(pydantic.database).as_table = true` 时，会生成 SQLModel 表类。

示例：

```protobuf
message Example {
  option (pydantic.database) = {
    as_table: true
    table_name: "example_table"
  };
}
```

生成结果的核心形态类似：

```python
class Example(SQLModel, table=True):
    __tablename__ = "example_table"
```

### 表名规则

- 如果声明了 `table_name`，就直接使用该值。
- 如果省略了 `table_name`，生成器会退回到 message 名称的 snake_case 形式。

### 复合约束与索引

`compound_index` 会被转换为：

- 当 `index_type = "UNIQUE"` 时生成 `UniqueConstraint(...)`
- 当 `index_type = "PRIMARY"` 时生成 `PrimaryKeyConstraint(...)`
- 其他 `index_type` 会生成普通 `Index(...)`

生成器还会在 `__table_args__` 中附加 `{"extend_existing": True}`。

### 字段级 SQLAlchemy 提示

最常见的 SQL 相关注解有：

- `primary_key`
- `unique`
- `index`
- `nullable`
- `foreign_key`
- `sa_column_type`

示例 schema 中，JSON 和向量列就是通过 `sa_column_type` 请求的：

```protobuf
repeated Example2 examples = 9 [(pydantic.field) = {
  description: "Nested message"
  sa_column_type: "JSON"
}];

repeated float embeddings = 11 [(pydantic.field) = {
  description: "Embedding vector for the example"
  sa_column_type: "Vector(1563)"
}];
```

### `tables.py` 反腐层

当至少有一个 message 被生成为表模型，且 `PROTOBUF_PYDANTIC_GENERATE_TABLES=true` 时，插件会输出 `tables.py`。

这个文件会用统一别名重新导出表类，避免业务代码直接依赖生成模块路径。

仓库中的示例：

```python
from .example_model import Example as ExampleRow
```

别名后缀由 `PROTOBUF_PYDANTIC_TABLE_ALIAS_SUFFIX` 控制，默认值是 `Row`。
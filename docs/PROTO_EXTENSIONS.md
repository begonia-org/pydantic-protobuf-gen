# Proto Extensions / Proto 扩展参考

## English

This document covers the model-generation annotations that are part of the verified release workflow.

### Field Option: `(pydantic.field)`

Defined in `protos/protobuf_pydantic_gen/pydantic.proto` as `Annotation`.

| Field | Purpose |
| --- | --- |
| `description` | Field description used in generated schema and SQLAlchemy comments/docs when applicable |
| `example` | Example value stored in generated schema metadata |
| `default` | Default value expression or literal consumed during generation |
| `alias` | Pydantic field alias |
| `title` | Pydantic field title |
| `required` | Marks the field as required in generated type hints and defaults |
| `nullable` | Controls SQLAlchemy column nullability when a SQL column is emitted |
| `primary_key` | Marks table fields as primary keys |
| `unique` | Marks table fields as unique |
| `index` | Marks table fields as indexed |
| `const` | Passes through as a field validation option |
| `field_type` | Forces a SQLAlchemy type shortcut that is later mapped into column generation |
| `sa_column_type` | Explicit SQLAlchemy column type expression, such as `JSON` or `Vector(1563)` |
| `min_length` | String length validation |
| `max_length` | String length validation |
| `gt`, `ge`, `lt`, `le` | Numeric validation bounds |
| `foreign_key` | Foreign key target for SQL columns |
| `label` | Stored in schema metadata as a UI-facing label |
| `default_factory` | Factory expression used for generated Pydantic defaults |
| `enum_storage` | Enum persistence mode for generated table fields |

### Message Option: `(pydantic.database)`

Defined in `DatabaseAnnotation`.

| Field | Purpose |
| --- | --- |
| `table_name` | Explicit SQL table name |
| `compound_index` | Repeated compound index or constraint definitions |
| `as_table` | Generate the message as `SQLModel, table=True` |

### Compound Index Shape

Each `compound_index` entry supports:

- `indexs`: ordered field names
- `index_type`: `UNIQUE`, `PRIMARY`, or any other value for a plain SQLAlchemy `Index`
- `name`: explicit constraint or index name

### Example

```protobuf
message Example {
  option (pydantic.database) = {
    as_table: true
    table_name: "example_table"
    compound_index: {
      indexs: ["name", "age"]
      index_type: "UNIQUE"
      name: "uni_name_age"
    }
  };

  string name = 1 [(pydantic.field) = {
    description: "Name of the example"
    alias: "full_name"
    label: "名称"
  }];

  repeated float embeddings = 11 [(pydantic.field) = {
    description: "Embedding vector for the example"
    sa_column_type: "Vector(1563)"
  }];
}
```

### Scope Note

The proto schema still contains legacy service and method auth extensions that were used by the deprecated gateway workstream. They are not part of the verified GA documentation path for this release, so they are intentionally not expanded here.

## 中文

本文档只覆盖当前正式发布流程中已经验证过的模型生成注解。

### 字段级选项：`(pydantic.field)`

定义于 `protos/protobuf_pydantic_gen/pydantic.proto` 的 `Annotation`。

| 字段 | 作用 |
| --- | --- |
| `description` | 字段描述；在生成 schema 以及适用时的 SQLAlchemy comment/doc 中使用 |
| `example` | 示例值，写入生成的 schema 元数据 |
| `default` | 生成阶段消费的默认值表达式或字面量 |
| `alias` | Pydantic 字段别名 |
| `title` | Pydantic 字段标题 |
| `required` | 控制生成类型提示与默认值时是否必填 |
| `nullable` | 当会生成 SQL 列时，控制 SQLAlchemy 列的可空性 |
| `primary_key` | 将表字段标记为主键 |
| `unique` | 将表字段标记为唯一 |
| `index` | 将表字段标记为索引 |
| `const` | 透传为字段校验选项 |
| `field_type` | 强制使用 SQLAlchemy 类型快捷值，随后参与列生成 |
| `sa_column_type` | 显式 SQLAlchemy 列类型表达式，如 `JSON`、`Vector(1563)` |
| `min_length` | 字符串最小长度校验 |
| `max_length` | 字符串最大长度校验 |
| `gt`、`ge`、`lt`、`le` | 数值边界校验 |
| `foreign_key` | SQL 列的外键目标 |
| `label` | 作为面向 UI 的标签写入 schema 元数据 |
| `default_factory` | 生成 Pydantic 默认工厂时使用的表达式 |
| `enum_storage` | 生成表字段时的枚举持久化方式 |

### 消息级选项：`(pydantic.database)`

定义于 `DatabaseAnnotation`。

| 字段 | 作用 |
| --- | --- |
| `table_name` | 显式指定 SQL 表名 |
| `compound_index` | 重复定义复合索引或约束 |
| `as_table` | 将 message 生成为 `SQLModel, table=True` |

### `compound_index` 结构

每个 `compound_index` 支持：

- `indexs`：有序字段名列表
- `index_type`：`UNIQUE`、`PRIMARY`，其他值会生成普通 SQLAlchemy `Index`
- `name`：显式约束或索引名

### 示例

```protobuf
message Example {
  option (pydantic.database) = {
    as_table: true
    table_name: "example_table"
    compound_index: {
      indexs: ["name", "age"]
      index_type: "UNIQUE"
      name: "uni_name_age"
    }
  };

  string name = 1 [(pydantic.field) = {
    description: "Name of the example"
    alias: "full_name"
    label: "名称"
  }];

  repeated float embeddings = 11 [(pydantic.field) = {
    description: "Embedding vector for the example"
    sa_column_type: "Vector(1563)"
  }];
}
```

### 范围说明

proto schema 中仍保留了曾供已废弃网关工作流使用的 service 和 method 鉴权扩展。这些内容不属于本次正式 GA 文档的已验证路径，因此这里不展开描述。
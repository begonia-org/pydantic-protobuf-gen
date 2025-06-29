# protobuf_pydantic_gen: `sa_auto_update` 功能开发文档

> 目标读者：protobuf_pydantic_gen 维护开发者
> 日期：2026-04-08

---

## 1. 背景与需求

我们的业务 proto 定义了带 `updated_at` 字段的 ORM 表模型（通过 `(pydantic.database)` 选项）。目前 `updated_at` 的更新完全依赖调用方在 Repository 层手动赋值，容易遗漏且不统一。

**目标**：在 proto 字段级别新增 `sa_auto_update` 选项，代码生成器为标记了 `sa_auto_update:true` 的 datetime 字段自动在生成的 `Column()` 中注入 `onupdate=func` 参数，使 SQLAlchemy 在 UPDATE 时自动刷新该字段。

### 期望的 Proto 写法

```protobuf
google.protobuf.Timestamp updated_at = 9 [json_name="updated_at", (pydantic.field) = {
  description: "更新时间",
  label: "更新时间",
  sa_auto_update:true
}];
```

### 期望的生成代码

```python
updated_at: Optional[datetime.datetime] = Field(
    description="更新时间",
    default=None,
    sa_column=Column(
        TIMESTAMP(timezone=True),
        nullable=True,
        doc="更新时间",
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc),  # ← 自动注入
    ),
    schema_extra={"label": "更新时间"},
)
```

---

## 2. Proto 定义变更（已完成）

`protobuf_pydantic_gen/pydantic.proto` 中 `Annotation` message 已新增：

```protobuf
message Annotation {
    // ... 现有字段 ...
    string default_factory=22[json_name="default_factory"];
    string enum_storage=23[json_name="enum_storage"];
   bool sa_auto_update=24[json_name="sa_auto_update"];    // ← 新增
}
```

**下一步**：需要重新编译 `pydantic.proto` 生成 `pydantic_pb2.py` / `pydantic_pb2.pyi`，使 Python 端能解析该字段。

---

## 3. 代码生成器改动点

### 3.1 涉及文件

| 文件 | 方法 | 行号范围 | 改动说明 |
|------|------|----------|----------|
| `message_processor.py` | `_process_field_ext()` | 317-330 | datetime 自动注入 Column 分支 |
| `message_processor.py` | `_process_field_ext()` | 353-399 | `sa_column_type` 驱动的 Column 分支 |

### 3.2 改动 A — datetime 自动注入 Column 分支

**位置**：`_process_field_ext()` 约 line 317-330

**现有逻辑**：当 `as_table=True` 且字段类型为 `datetime.datetime`、且没有显式 `sa_column` / `sa_column_type` 时，自动生成 `Column(TIMESTAMP(timezone=True), ...)`。

**改动**：在 `col_extra` 构建完成、生成 `ext["sa_column"]` 之前，检查 `sa_auto_update`：

```python
# 现有代码 (line 325-330)
nullable_val = ext.pop("nullable", True)
col_extra: List[str] = [f"nullable={nullable_val}"]
if ext.get("description"):
    _doc = str(ext["description"]).replace('"', "")
    col_extra.append(f"doc={repr(_doc)}")

# ── 新增 ──
if ext.pop("sa_auto_update", False):
    col_extra.append("onupdate=lambda: datetime.datetime.now(datetime.timezone.utc)")

ext["sa_column"] = f"Column(TIMESTAMP(timezone=True), {', '.join(col_extra)})"
```

### 3.3 改动 B — `sa_column_type` 驱动的 Column 分支

**位置**：`_process_field_ext()` 约 line 371-399，`column_kwargs` 构建区域

**现有逻辑**：将 `index` / `unique` / `nullable` / `primary_key` / `foreign_key` 从 `ext` 移入 `column_kwargs`。

**改动**：在 `foreign_key` 处理之后、`doc` 处理之前，增加 `sa_auto_update` 处理：

```python
# 现有代码 (line 389-391)
if ext.get("foreign_key"):
    column_kwargs.append(f"foreign_key={ext['foreign_key']}")
    ext.pop("foreign_key", None)

# ── 新增 ──
if ext.pop("sa_auto_update", False):
    column_kwargs.append("onupdate=lambda: datetime.datetime.now(datetime.timezone.utc)")

# 现有代码 (line 393-395)
if ext.get("description"):
    column_kwargs.append(f"doc={ext['description']}")
```

**关键**：使用 `ext.pop("sa_auto_update", False)` 确保从 ext 中移除，避免该字段泄漏到后续 `Field()` 参数中。

---

## 4. 处理流程总览

```
Proto 定义
  │
  ▼
_extract_field_extensions()
  │  从 proto options 提取 ext dict:
  │  {"description": "更新时间", "label": "更新时间", "sa_auto_update": true}
  ▼
set_default_value()           ← type_mapper.py
  │  对 datetime 类型: default → default_factory
  │  sa_auto_update 不受影响，原样保留在 ext 中
  ▼
_process_field_ext()          ← message_processor.py
  │
  ├─ 分支 A: datetime 自动注入 Column
  │    检测 sa_auto_update → 注入 onupdate=lambda: datetime.datetime.now(...)
  │    pop sa_auto_update 防止泄漏
  │
  └─ 分支 B: sa_column_type 驱动
       检测 sa_auto_update → 注入 onupdate=lambda: datetime.datetime.now(...)
       pop sa_auto_update 防止泄漏
  │
  ▼
safe_python_value()
  │  sa_auto_update 已被 pop，不会进入此环节
  ▼
template.j2 渲染 Field(attributes)
  │
  ▼
最终生成:
  sa_column=Column(TIMESTAMP(timezone=True), nullable=True,
                   doc="更新时间",
                   onupdate=lambda: datetime.datetime.now(datetime.timezone.utc))
```

---

## 5. 关于 `onupdate` 的 callable 选择

生成的 callable 为 `lambda: datetime.datetime.now(datetime.timezone.utc)`。

**选择理由**：

| 候选方案 | 是否可用 | 说明 |
|----------|----------|------|
| `datetime.datetime.utcnow` | ⚠️ deprecated | Python 3.12+ 已标记废弃，未来版本移除 |
| `datetime.datetime.now(datetime.timezone.utc)` | ❌ 不可用 | call expression，加载时立即求值，得到固定 datetime 对象，不可调用 |
| `lambda: datetime.datetime.now(datetime.timezone.utc)` | ✅ 正确 | lambda 是 callable，每次调用返回当前时间 |
| `sqlalchemy.func.now()` | ❌ 不适用 | 返回服务端 `now()`，类型为 `ColumnElement` 而非 `datetime`，ORM 层 `onupdate` 需要纯 Python callable |

**注意**：`onupdate` 与 `default_factory` 语义一致——都需要传入 `NoArgAnyCallable`（无参可调用对象）。

---

## 6. 已知问题：`default_factory` 生成值是 call expression 而非 callable

### 问题描述

当前部分 proto 字段使用 `default:"datetime.datetime.now(datetime.timezone.utc)"`。
经 `set_default_value()` 转换后，ext dict 中 `default_factory` 的值为字符串
`"datetime.datetime.now(datetime.timezone.utc)"`。

`safe_python_value()` 无法通过 `json.loads` 或 `ast.literal_eval` 解析此字符串，
最终原样输出。生成的代码为：

```python
default_factory=datetime.datetime.now(datetime.timezone.utc)   # ← call expression，不是 callable
```

**`Field(default_factory=...)` 类型签名为 `default_factory: NoArgAnyCallable | None`**，
要求传入无参可调用对象。但 `datetime.datetime.now(datetime.timezone.utc)` 在模块加载时
立即求值，返回一个固定的 `datetime` 对象。Pydantic 调用 `fac()` 时会因 `datetime`
对象不可调用而报 `TypeError`。

### 正确行为

`default_factory` 的值必须是 **callable**（函数引用或 lambda），不是 call expression：

```python
# ✅ 正确 — callable reference（函数引用）
default_factory=datetime.datetime.utcnow

# ✅ 正确 — lambda（推荐，避免 deprecated API）
default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)

# ❌ 错误 — call expression（加载时求值，得到不可调用的 datetime 对象）
default_factory=datetime.datetime.now(datetime.timezone.utc)
```

### 建议修复

**方案 1（最小改动）**：将 `default_factory` 加入 `_CODE_EXPR_KEYS`，使其作为代码表达式原样输出：

```python
# message_processor.py line 253
_CODE_EXPR_KEYS = frozenset({"sa_column", "sa_column_kwargs", "default_factory"})
```

然后 proto 中使用 `default_factory:"lambda: datetime.datetime.now(datetime.timezone.utc)"`。

**方案 2（自动转换）**：在 `set_default_value()` 中，当 `type_str == "datetime.datetime"` 且 proto 使用 `default` 时，自动生成 lambda 表达式而非原样传递：

```python
# type_mapper.py set_default_value() line 170-173
elif type_str == "datetime.datetime":
    # 生成 tz-aware callable，而非原样传递 call expression
    ext["default_factory"] = "lambda: datetime.datetime.now(datetime.timezone.utc)"
    ext.pop("default", None)
```

这样 proto 只需写 `default:"now"` 或任意占位值，codegen 自动替换为正确的 callable 字符串。

**推荐方案 2**，理由：proto 作者无需关心 callable vs call expression 的区别，codegen 统一保证输出正确。

---

## 7. 参考对照：现有 `sa_column_type` 处理模式

供开发者参考，以下是 `sa_column_type` 从 proto 到生成代码的完整链路：

### Proto 输入
```protobuf
map<string, google.protobuf.Any> metadata_json = 6 [(pydantic.field) = {
  sa_column_type: "JSONB"
}];
```

### 处理步骤

1. **`_extract_field_extensions()`** → `ext = {"sa_column_type": "JSONB", ...}`

2. **`_process_field_ext()` line 353-399**:
   ```python
   if ext.get("sa_column_type") and msg_ext.get("as_table"):
       sa_column_type = ext.get("sa_column_type", "")     # "JSONB"
       sa_column_type = self._get_sa_type_import(sa_column_type, imports)
       # → imports.add("from sqlalchemy.dialects.postgresql import JSONB")
       # → sa_column_type = "JSONB"

       column_args = ["JSONB"]
       column_kwargs = ["nullable=...", "doc=..."]

       ext["sa_column"] = "Column(JSONB, nullable=..., doc=...)"
       ext.pop("sa_column_type")   # 消费掉，不再传入 Field()
   ```

3. **`safe_python_value()`**: `sa_column` 在 `_CODE_EXPR_KEYS` 中，原样输出

4. **模板渲染**: `sa_column=Column(JSONB, nullable=..., doc=...)`

### 关键设计模式

| 步骤 | 模式 |
|------|------|
| 从 ext 提取值 | `ext.get("sa_column_type")` |
| 转换/增强 | 构建 Column() 字符串 |
| **消费原始 key** | `ext.pop("sa_column_type")` — 防止泄漏到 Field() |
| 输出到 `_CODE_EXPR_KEYS` | `ext["sa_column"] = "Column(...)"` — 避免 repr() |

`sa_auto_update` 应遵循完全相同的模式：提取 → 注入到 Column kwargs → pop 原始 key。

---

## 8. 验证方法

改动完成后，使用以下 proto 定义进行验证：

```protobuf
message TestAutoUpdate {
  option (pydantic.database) = {
    as_table: true
    table_name: "test_auto_update"
    compound_index: { indexs: ["id"], name: "pk_test", index_type: "PRIMARY" }
  };

  string id = 1 [(pydantic.field) = { primary_key: true, required: true, max_length: 64 }];
  google.protobuf.Timestamp created_at = 2 [(pydantic.field) = {
    description: "创建时间",
    label: "创建时间",
    default_factory:"lambda: datetime.datetime.now(datetime.timezone.utc)"
  }];
  google.protobuf.Timestamp updated_at = 3 [(pydantic.field) = {
    description: "更新时间",
    label: "更新时间",
    sa_auto_update:true
  }];
}
```

### 期望生成结果

```python
class TestAutoUpdate(SQLModel, table=True):
    __tablename__ = "test_auto_update"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_test"),
        {"extend_existing": True},
    )

    id: str = Field(
        description="...",
        primary_key=True,
        max_length=64,
        default="",
    )
    created_at: Optional[datetime.datetime] = Field(
        description="创建时间",
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc),  # callable
        sa_column=Column(TIMESTAMP(timezone=True), nullable=True, doc="创建时间"),
        schema_extra={"label": "创建时间"},
    )
    updated_at: Optional[datetime.datetime] = Field(
        description="更新时间",
        default=None,
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=True,
            doc="更新时间",
            onupdate=lambda: datetime.datetime.now(datetime.timezone.utc),     # ← sa_auto_update 生效
        ),
        schema_extra={"label": "更新时间"},
    )
```

### 验证清单

- [ ] `sa_auto_update` 不出现在 `Field()` 的直接参数中（已被消费到 Column 内）
- [ ] `onupdate=...` 的值是 callable（lambda 或函数引用，无直接调用）
- [ ] `default_factory=...` 的值是 callable（不是 call expression）
- [ ] 无 `sa_auto_update` 标记的字段不生成 `onupdate`
- [ ] 与 `sa_column_type` 共存时（显式指定列类型 + sa_auto_update），`onupdate` 仍正确注入
- [ ] 重新编译 `pydantic.proto` 后 `pydantic_pb2.py` 包含 `sa_auto_update` 字段定义
- [ ] 生成的模型可正常实例化（`TestAutoUpdate(id="test")` 不报错，`created_at` 自动填充）
- [ ] SQLAlchemy UPDATE 时 `updated_at` 自动更新为当前时间

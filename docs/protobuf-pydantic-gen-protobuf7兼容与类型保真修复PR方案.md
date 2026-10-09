# protobuf-pydantic-gen protobuf 7.x 兼容与类型保真修复 PR 方案

## 0. 证据链（本方案针对哪个基线）

**确认基线**：`develop` @ `7401a654305d650c685c0912abbe6bb562afeac4`（`Update pyproject.toml`，2026-07-26），其父提交为 `e90259ae`。

下游消费方（zenmpai）通过 `uv.lock` 锁定该分支：

```toml
protobuf-pydantic-gen = { git = "https://github.com/begonia-org/pydantic-protobuf-gen.git", rev = "develop" }
```

安装后 `dist-info/direct_url.json` 记录如下（**本机未找到实物，见复核记录 R4**；`uv.lock` 一条已实测确认）：

```json
{
  "url": "https://github.com/begonia-org/pydantic-protobuf-gen.git",
  "vcs_info": {
    "vcs": "git",
    "commit_id": "7401a654305d650c685c0912abbe6bb562afeac4",
    "requested_revision": "develop"
  }
}
```

即 **下游下一次 `uv sync` 安装到的就是 develop HEAD（`7401a65`）**。

> **范围修正（复核 R5）**：`7401a65` 是下游声明并锁定的提交，但「在下游现网 schema 上复现」只对 **2.1** 成立 —— `zenmpai.proto` 只有 27 行 / 2 个 message（无 `map` / `oneof` / `optional`），`stew/api/v1/context.proto` 只有 2 个 `map<string, google.protobuf.Any>`，且不在 Python 生成集合内（`Makefile` 的 `PY_PROTO_FILES = $(wildcard $(PROTO_DIR)/zenmpai*.proto)`）。**2.2 / 2.3 / 2.4 是生成器层面的潜在缺陷，需要合成 probe 才能复现**（本文档 §附即为此用途），不是下游现网正在踩的坑。

**注意一处容易误判的地方**：本地检出 `/data/work/begonia-org/pydantic-protobuf-gen` 位于 `e90259ae`，比远端 develop 落后一个提交；`git status -sb` → `## develop...origin/develop [落后 1]`。

> **复核修正（R1，2026-10-09）**：本节初稿写的是「`origin/develop` 尚未 fetch，故 status 无 ahead/behind 标记；`git fetch --dry-run` → `e90259a..7401a65`」，实测**不成立**：`refs/remotes/origin/develop` 已存在且 `= 7401a654305d650c685c0912abbe6bb562afeac4`（与 `git ls-remote` 一致），status 显示 `[落后 1]`，`git fetch --dry-run` **无输出、exit 0**（跟踪引用已是最新）。结论（本地落后一个提交、代码差异只有一行）不变，但这三条证据是错的。

**而 `7401a65` 与 `e90259ae` 的代码差异只有一行**：

```diff
--- a/pyproject.toml
+++ b/pyproject.toml
@@ -11,7 +11,7 @@ license = "Apache-2.0"
    dependencies = [
     "grpcio>=1.50.0",
     "grpcio-tools>=1.50.0",
-    "protobuf>=5.27.0,<7.0.0",
+    "protobuf>=7.0.0",
```

因此：**2.1–2.5 的代码事实在 `e90259ae` 与 `7401a65` 上都成立**，行号在两者上完全一致（下文的行号对两者都有效）。但「在下游现网 schema 上复现」只对 2.1 成立，见上面的范围修正（R5）。

**复现环境**：Python 3.12 / protobuf **7.36.2** / `grpcio-tools`（`python3 -m grpc_tools.protoc`）/ `protoc-gen-pydantic` 0.1.9。

---

## 1. 范围

这份文档只列需要改 `protobuf-pydantic-gen` 生成器与运行时转换层的点，不展开下游业务仓库的兼容 shim，也不讨论已落盘生成物的手工补丁。

目标是把当前已确认的根因整理成可单独提 PR 的清单：

1. `protobuf>=7.0.0` 的声明与运行时 descriptor API 不一致 → 生成模型的 `to_protobuf()` / `from_protobuf()` 全部不可用（**由 develop 最新提交直接造成**）
2. `map<...>` 的 value 类型解析失效：message 值退化为 `Any`，enum 值更糟 —— 生成一个不存在的 entry 类型名（复核 R2）
3. `None` 被当作默认值写回 wire → 生成模型无法表达「没有值」
4. `oneof` 未处理
5. 版本常量与文档/分支声明漂移

其中 **1、2、3、5 是「声明与实现不一致」类缺陷**（有明确正解）；**4 既是缺陷也是设计决策**：`to_protobuf()` 在含 oneof 的模型上直接抛 `ParseError`（2026-10-09 实测，见 §2.4），必须先修掉「把所有 oneof 成员都写进报文」这一点，再定模型侧表达方式，见 §4.4。

---

## 2. 问题清单

### 2.1 `protobuf>=7.0.0` 声明与运行时 API 不一致

症状：

- 生成模型上的 `to_protobuf()` 抛 `AttributeError`
- 生成模型上的 `from_protobuf()` 抛 `AttributeError`

```text
AttributeError: 'google._upb._message.FieldDescriptor' object has no attribute 'label'
```

复现（下游最小用例）：

```python
import probe_pb2 as pb            # 任意由本生成器产出的 pb2
from probe_model import Union     # 对应生成模型
Union(metric='M', text_value='a').to_protobuf()
#   File ".../protobuf_pydantic_gen/ext.py", line 270, in model2protobuf
#     fd_proto = _to_field_proto(fd)
#   File ".../protobuf_pydantic_gen/ext.py", line 180, in _to_field_proto
#     fd_proto.label = fd.label
# AttributeError: 'google._upb._message.FieldDescriptor' object has no attribute 'label'
```

根因：

- `protobuf_pydantic_gen/ext.py:180` 读运行时 `FieldDescriptor.label`，而 protobuf 7.x 已从运行时 descriptor 移除该属性；替代 API 是 `is_repeated` / `is_required`
- 同类用法还有 `ext.py:278`（`model2protobuf`）与 `ext.py:448`（`protobuf2model`）
- `ext.py:328` 的 `fd.label` **不是问题** —— 那里的 `fd` 是 `descriptor_pb2.FieldDescriptorProto`（proto message，仍有 `label`）

实测（protobuf 7.36.2）：

```text
has label        : False
has is_repeated  : True
has is_required  : True
fd.label access  : RAISES AttributeError

PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python  →  impl = python, has label = False
```

即 **upb 与纯 Python 实现都已移除，无法用实现开关规避**。

**为什么这条是「声明与实现不一致」而不是「下游版本选错」**：`7401a65` 把下限提到 `>=7.0.0`（父提交 `e90259ae` 是 `>=5.27.0,<7.0.0`），而代码未同步迁移 —— 也就是**当前声明的下限本身是坏的**。

> **已修（2026-10-09）**：`ext.py` 不再读运行时 `FieldDescriptor.label` —— 新增 `is_repeated_field()` / `is_required_field()`（proto 描述符读 `label`，运行时描述符读 `is_repeated` / `is_required`）与 `field_descriptor_to_proto()` 规范化，`_to_field_proto()` / `model2protobuf` / `protobuf2model` / `_get_default_value` 的调用点、`type_mapper` 与 `message_processor` 的 repeated 判定统一走它们。实测：7.36.2 与 7.34.0 上往返正常（见附二·六）。

### 2.2 `map<string, Msg>` 的 value 类型退化为 `Any`

症状（类级对照，不是个例）：

| proto 字段 | 生成类型 |
|---|---|
| `map<string, string>` | `dict[str, str]` ✅ |
| `map<string, int32>` | `dict[str, int]` ✅ |
| `map<string, Inner>` | `dict[str, Any]` ❌ 嵌套类型丢失 |

标量 map 正常，是因为标量的数字类型码能命中 `FIELD_TYPE_MAPPING`；message 值落到兜底 `Any`；**enum 值走的是另一条更坏的路径**，不是 `Any`（见下方复核补注 R2）。

**2026-10-09 补充（实测）**：`map<string, Msg>` / `map<string, int32>` 这类**非 string 值**的 map 在**运行时**也是坏的 —— `to_protobuf()` 抛 `ParseError`、`from_protobuf()` 抛 `ValueError`（见附二·六 R11 / R12）。即 2.2 不只是「类型不精确」，而是**这些 map 根本无法往返**。

> **已修（2026-10-09）**：map 类型解析与 map 运行时都已修正 —— `type_mapper.get_field_type()` 入口规范化运行时描述符（根因）、map value 解析改从 **value 字段**取类型、`model2protobuf` / `protobuf2model` 的 map 分支改为按 value 类型分派（message / enum / bytes / 标量）、`protobuf2model` 的 map 分支把 **map 字段名**（而非 value 字段名）传给模型字段解析。生成物对照：`map<string, Inner>` → `Dict[str, Inner]`、`map<string, Level>` → `Dict[str, Level]`（原为 `Optional[LevelsEntry]`）、标量 map 不变。

根因：

- `protobuf_pydantic_gen/type_mapper.py:137` `_get_map_field_types()` 遍历的是 `message_descriptor.fields`，即 **运行时 `FieldDescriptor`** 对象
- 而它调用的 `get_field_type()` 是为 **`FieldDescriptorProto`** 写的：判据在 `type_mapper.py:76` 与 `:88`，都是 `hasattr(field, "type_name")`
- 运行时 `FieldDescriptor` **没有 `type_name`** 属性（它提供 `message_type` / `enum_type` / `full_name`），因此 message 分支与 enum 分支整段跳过
- 最终落到 `type_mapper.py:110` 的兜底：`return FIELD_TYPE_MAPPING.get(field.type, "Any")`，而 `TYPE_MESSAGE`(=11) 不在表里 → `"Any"`

实测：

```text
runtime descriptor type : google._upb._message.FieldDescriptor
hasattr(type_name)      : False        ← 分支判据因此不成立
vf.type                 : 11 (TYPE_MESSAGE)
vf.message_type.full_name: zenmpai.v1.Inner
=> FIELD_TYPE_MAPPING.get(11) -> "Any" (兜底)
```

**复核补注（R2，读码推断，未实测）**：`message` 与 `enum` 值走的是**两条不同的坏路径**，把它们并列成「都落到 `Any`」会漏掉后一条：

- **message 值**：`get_field_type` 的两处判据（`:76`、`:88`）都要求 `hasattr(field, "type_name")`，运行时 `FieldDescriptor` 不满足 → 落到 `:110` 的 `FIELD_TYPE_MAPPING.get(field.type, "Any")`，而 `TYPE_MESSAGE`(11) 不在表里 → `Any`。
- **enum 值**：`:106` 的判据只有 `field.type == TYPE_ENUM`，**不检查 `type_name`** → `:107 type_name = field.type_name.split(".")[-1]` 在运行时 `FieldDescriptor` 上抛 `AttributeError` → 被 `_get_map_field_types` 的 `except Exception`（`:148-150`）**静默吞掉**、返回 `(None, None)` → 调用方 `:96 if key_type and value_type` 不成立 → 掉进 `:100-101`「Regular message type」→ 返回 **map entry 的类型名**（如 `FooEntry`），生成一个**不存在的类名注解**。

即 `map<string, SomeEnum>` 比 `Dict[str, Any]` 更糟（`NameError`/无效导入级别），**且 §3.2 原定修法（只改 `_get_map_field_types` + 让兜底不静默）拦不住它** —— 必须同时让 `:106-107` 对「没有 `type_name` 的运行时描述符」显式失败或诊断。

### 2.3 `None` 被当作默认值写回 wire（生成模型无法表达「没有值」）

症状：

- 生成模型上 `optional double` 与普通 `double` **同样**降成 `float | None = _Field(default=0.0)`，presence 丢失
- 反向转换时 `None` 不是「不设置」，而是被替换成默认值并**真正写进报文**

根因：

- **顶层字段**（`model2protobuf` 主循环，`protobuf_pydantic_gen/ext.py:273-277`）：None→默认值**在这里**被写回 `d`：

```python
for fd in proto.DESCRIPTOR.fields:
    fd_proto = _to_field_proto(fd)
    if fd.name in d:
        field_value = getattr(model, fd.name)
        if field_value is None:
            d[fd.name] = _get_default_value(fd_proto, descriptor_proto)   # ← 默认值在这里被写回
            continue
```

- **`_convert_value`（`ext.py:198-200`）是次要位置**：顶层 `None` 被上面的 `continue` 挡住，这条分支只在 **repeated 元素为 `None`** 时才可达：

```python
def _convert_value(fd, value):
    if value is None:
        return _get_default_value(fd, descriptor_proto)
```

- 配合生成阶段把 `optional` 标量的默认值也填成非 `None`（`type_mapper.set_default_value`，`:152-183`，取 `DEFAULT_VALUES["float"] == "0.0"`），于是「字段没被观测到」与「字段值就是 0」在模型里不可区分

> **复核补注（R3）**：所以 §4.3 方案 A、§5 伪代码把「跳过赋值」打在 `_convert_value` 上是**打空**的 —— 顶层 `optional` 字段的 `None` 根本进不到那里；真正的改动点在 `:275-277`（遇 `None` 时**不要写 `d`**：`d.pop(fd.name, None)` 后 `continue`），生成侧对应 `set_default_value`。

影响面：任何「值可缺省」的契约（指标无值 / 可选结果 / 部分更新语义）经生成模型往返后都会得到错误的事实。

> **已修（2026-10-09，方案 A）**：生成侧 `optional` 标量默认值改为 `None`（`type_mapper.set_default_value` 增加 `proto3_optional` 分支）；`model2protobuf` 对 proto3 `optional` 字段遇 `None` 时 `d.pop(fd.name)`、不写默认值；`protobuf2model` 对报文中未设置的 proto3 `optional` 字段回填 `None`（按 `HasField` 判定）。`probe3` 实测（protobuf 7.36.2）：

```text
[unset]            HasField('opt_score')=False bytes=b'\n\x01M'
[opt_score=None]   HasField('opt_score')=False bytes=b'\n\x01M'
[opt_score=0.0]    HasField('opt_score')=True  bytes=b'\n\x01M\x11\x00\x00\x00\x00\x00\x00\x00\x00'
from_protobuf(<empty message>) -> opt_score=None
```

> 回归：`example/tests/test_presence_and_bytes.py`（presence 部分 6 项）。

### 2.4 `oneof` 未处理

症状：

- `oneof` 成员被当作普通可选字段逐个发出，选择语义丢失
- 生成模型里两个成员各自默认非 `None`，因此无法表达「一个都没选」

根因：

- 生成器自身代码中 **`grep oneof` 零命中**（`message_processor.py` / `type_mapper.py` / `generator.py` / `models.py` / `ext.py` / `utils.py` / `template.j2` 都没有）；仓库里出现的 `oneof` 只在 vendored 的 `google/protobuf/descriptor.proto`、`google/api/http.proto` 与给 **TypeScript** 生成器的 `--ts_proto_opt=oneof=unions`
- 既没有读 `DescriptorProto.oneof_decl`，也没有用 `FieldDescriptorProto.oneof_index`

对照事实（报文侧是正常的，问题只在生成模型这一层）：

```text
未设          → MessageToDict = {'metric': 'M'}                         （JSON 无键）
显式 0.0      → MessageToDict = {'metric': 'M', 'numericValue': 0.0}
WhichOneof('value') 可用
```

**声明边界（2026-10-09 实测，原推断被推翻）**：`model2protobuf` 遍历全部 descriptor 字段、`model_dump()` 又包含所有字段 —— 结果不是「只保留最后设置的那个」，而是 `ParseDict` **直接抛错**：

```text
google.protobuf.json_format.ParseError: Message type "probe2.v1.Union" should not have multiple "value" oneof fields at "Union".
```

即含 oneof 的模型在 `to_protobuf()` 上是**硬失败**（不是静默丢语义），严重度与 2.1 同级，证据与复现脚本见 `tmp/probe-enum-map/`。该次运行受宿主环境限制解析到了仓库外的旧版 `protobuf_pydantic_gen`（见附二·四），后已在容器内用仓库源码复测确认。

> **已修（2026-10-09，方案 A）**：生成侧新增 `_process_oneof_field()` —— 读 `DescriptorProto.oneof_decl` + `FieldDescriptorProto.oneof_index`，**跳过 proto3 `optional` 产生的 synthetic oneof**，把成员合并为一个字段（名为 oneof 名、类型 `Optional[_Union[...]]`，成员不再各自成字段）；运行时 `model2protobuf` 对每个真实 oneof **只设置被选中的那个成员**（按值的 Python 类型匹配，精确匹配优先、声明序决胜），`protobuf2model` 用 `WhichOneof()` 读回。protoc 全链路实测（7.36.2）：`value="a"` → `WhichOneof='text_value'`；`value=1.5` → `WhichOneof='numeric_value'`；不设 → `WhichOneof=None` 且报文字节仅 `metric`。回归：`example/tests/test_oneof.py`（7 项）。

### 2.5 版本常量与分支/文档声明漂移

- `protobuf_pydantic_gen/constants.py:8` `__version__ = "0.1.8"`，而包版本是 `0.1.9`
- `develop` 的 `pyproject.toml` 是 `protobuf>=7.0.0`，`master` 仍是 `protobuf>=5.27.0,<7.0.0`，`README.md` / `README.zh.md` 跟的是 master 的写法 —— 两分支在这一点上已经分叉，读者按 README 会得到与 develop 相反的结论。**已修（2026-10-09）**：声明与两份 README 统一为 `protobuf>=7.34.0`（PyPI 上不存在 `7.0.0`，Python 端最低的 7.x 是 7.34.0）；`master` 分支未动

---

## 3. 需要改动的生成器文件

### 3.1 `protobuf_pydantic_gen/ext.py`

职责：Python model ↔ protobuf message 的双向转换。

需要改动：

- `_to_field_proto()`（`:180`）：不再读 `fd.label`
- `model2protobuf()`（`:278`）：`fd.label == fd.LABEL_REPEATED` → `fd.is_repeated`
- `protobuf2model()`（`:448`）：同上
- `_convert_value()`（`:199`）：`None` 的语义见 §4.3（需先定语义再改）
- `:328` **要看调用点**，不能一句「合法」带过：从 `:276` 进来的 `fd` 是 `FieldDescriptorProto`（合法）；但从 `:200`（`_convert_value` 的 `None` 分支）进来的是**运行时 `FieldDescriptor`**，`:328` 的 `fd.label` 与 `:329/:332` 的 `is_map_field(fd, …)`（→ `utils.py:65-69` 读 `field_desc.type_name`）都会炸。只改 `:180/:278/:448` 的话，这条会在「repeated 元素为 `None`」时复发

### 3.2 `protobuf_pydantic_gen/type_mapper.py`

职责：protobuf 类型 → Python 类型字符串。

需要改动：

- `_get_map_field_types()`（`:120-150`）：改为使用 **proto 描述符**而不是运行时描述符 —— 要么对 `message_descriptor` 调 `CopyToProto()` 后取 `nested_type` 里的 `key` / `value` `FieldDescriptorProto`，要么在解析 message/enum 值类型时改用 `nested_field.message_type.full_name` / `nested_field.enum_type.full_name`
- `get_field_type()`（`:110` 的兜底）：对 `TYPE_MESSAGE` / `TYPE_ENUM` **不应静默返回 `Any`**。当类型名不可得时应当抛带诊断的异常（或记 `logger.error` 后返回可识别标记），否则类型信息丢失会被静默吞掉 —— 这正是 2.2 难被发现的原因
- **同时处理 `:106-107` 的 enum 分支与 `:148-150` 的 `except Exception`**：enum 值的失败现在被 `_get_map_field_types` 的宽 `except` 吞成 `(None, None)`，再被上游当成「Regular message type」处理，返回 map entry 的类型名（R2）。不修这里，`enum` 值的类型丢失仍然静默

### 3.3 `protobuf_pydantic_gen/constants.py`

职责：类型映射表与版本常量。

需要改动：

- `__version__`（`:8`）与包版本同步，或改为从包元数据读取，避免两处手工维护

### 3.4 `protobuf_pydantic_gen/message_processor.py`（仅当 oneof 纳入本 PR）

职责：从 descriptor 提取 message / field 结构。

需要改动（若做 §4.4）：

- 读取 `DescriptorProto.oneof_decl`，并用 `FieldDescriptorProto.oneof_index` 把字段归属到 oneof
- 注意 **proto3 `optional` 会产生 synthetic oneof**（`descriptor.proto` 的注释已说明：每个 proto3 optional 字段各自拥有一个 synthetic oneof，且在 descriptor 中排在所有真实 oneof 之后）—— 必须跳过 synthetic oneof，否则会把普通 `optional` 字段误判成 oneof 成员

---

## 4. 建议实现方式

### 4.1 `label` → `is_repeated` / `is_required`

```python
fd_proto.label = (
    descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED
    if fd.is_repeated
    else descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
)
```

`is_repeated` / `is_required` 在 protobuf 7.36.2 上实测存在（见 2.1）。若希望同时兼容 `<7.0.0`，可做一次能力探测后择一，但**既然 develop 已声明 `>=7.0.0`，直接改用新 API 更简单**。

### 4.2 map value 类型

统一走 proto 描述符：

```python
message_descriptor_proto = descriptor_pb2.DescriptorProto()
message_descriptor.CopyToProto(message_descriptor_proto)
for nested_field in message_descriptor_proto.nested_type[0].field:   # map entry
    ...
```

或保持运行时描述符、但把 message/enum 值类型单独解析：

```python
if nested_field.type == TYPE_MESSAGE:
    value_type = nested_field.message_type.name          # 运行时 API 提供 message_type
elif nested_field.type == TYPE_ENUM:
    value_type = nested_field.enum_type.name
```

### 4.3 `None` 的语义（**已定：方案 A，已实施**）

这不是补丁而是语义决策，两个方向：

| 方案 | 行为 | 代价 |
|---|---|---|
| **A. `optional` 字段的 `None` 表示「不设置」**（**已采纳并实施 2026-10-09**） | `_convert_value` 对 proto3 `optional` 字段遇 `None` 时**跳过赋值**，不写默认值 | 与非 `optional` 字段行为不同，需要按字段区分 |
| B. 保持现状（`None` → 默认值） | 无改动 | 生成模型永久无法表达缺省；`optional` 的存在意义被抹掉 |

若选 A，生成阶段也应让 `optional` 标量的默认值保持 `None`（当前是 `0.0` / `""` / `False`），否则模型侧第一步就已经丢了信息。

> **复核补注（R3）**：方案 A 的改动点**不是** §5 伪代码里 `_convert_value` 的 `_UNSET` 哨兵 —— 顶层 `optional` 字段的 `None` 根本不会进入 `_convert_value`（`ext.py:275-277` 已 `continue`）。正确落点是 `model2protobuf` 主循环 `:275-277`：遇 `None` 时**不要写进 `d`**（`d.pop(fd.name, None)` 后 `continue`）—— `model_dump()` 已经把这个键放进 `d`，`ParseDict(d, proto)` 会把显式默认值当成「已设置」。生成侧对应 `type_mapper.set_default_value`（`:152-183`）与 `message_processor`（目前**没有**任何 `proto3_optional` / `has_presence` 判定，生成侧 presence 缺失比 2.3 描述的更彻底）。

### 4.4 oneof 的模型侧表达（**已定：方案 A，已实施**）

两个候选：

| 方案 | 生成形状 | 说明 |
|---|---|---|
| **A. `Union` 成员**（**已采纳并实施 2026-10-09**） | `value: Optional[_Union[float, str, Inner]]` | 贴近 TS 生成器已有的 `oneof=unions` 语义；但丢失「哪一个成员」的名字，`0` 与 `""` 仍需靠类型区分。注解用 `_Union` 别名（`from typing import Union as _Union`）：名为 `Union` 的 proto message 会遮蔽 `typing.Union`（R14） |
| B. 显式选择器 | 各成员 + `which_value: str`（或 enum） | 信息完整、可逆；但字段数变多，与现有 `model_dump()` 全字段往返的写法需要配套修改 |

无论选哪个，`model2protobuf` 都必须改为**只设置被选中的那一个成员**，否则一次往返会把多个成员同时写进报文。

---

## 5. 伪代码

```python
# ── ext.py ──────────────────────────────────────────────────────────────────
def _to_field_proto(fd) -> descriptor_pb2.FieldDescriptorProto:
    fd_proto = descriptor_pb2.FieldDescriptorProto()
    fd_proto.name = fd.name
    fd_proto.number = fd.number
    fd_proto.label = (                                    # ← 不再读 fd.label
        descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED
        if fd.is_repeated
        else descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    )
    fd_proto.type_name = get_type_name(fd)
    fd_proto.type = fd.type
    return fd_proto


# ⚠ 复核 R3：下面这条分支**不是**顶层 optional 字段的落点（ext.py:275-277 已 continue）。
# 方案 A 的实际改动点在 model2protobuf 主循环 —— 不要把补丁打在 _convert_value 上。
def _convert_value(fd, value):
    if value is None:
        if _is_proto3_optional(fd):                       # ← 见 §4.3 方案 A
            return _UNSET                                  # 调用方跳过赋值
        return _get_default_value(fd, descriptor_proto)
    ...


# ── type_mapper.py ──────────────────────────────────────────────────────────
def _get_map_field_types(self, field, imports, type_mapping, file_name):
    message_descriptor = self.pool.FindMessageTypeByName(_strip_dot(field.type_name))
    entry_proto = descriptor_pb2.DescriptorProto()
    message_descriptor.CopyToProto(entry_proto)
    key_field, value_field = entry_proto.nested_type[0].field  # FieldDescriptorProto
    return (
        self.get_field_type(key_field, imports, type_mapping, file_name),
        self.get_field_type(value_field, imports, type_mapping, file_name),
    )
```

---

## 6. 测试清单

### 6.1 生成结果测试

- `map<string, Inner>` 生成 `dict[str, Inner]`（当前为 `dict[str, Any]`）
- `map<string, SomeEnum>` 生成 `dict[str, SomeEnum]`（当前既不是 `Any` 也不是枚举名，而是一个不存在的 entry 类型名，见 R2）
- `map<string, string>` / `map<string, int32>` 保持 `dict[str, str]` / `dict[str, int]`（正对照，防回归）
- `optional double` 的默认值为 `None`（若采纳 §4.3 方案 A）
- oneof 成员按选定表达生成（§4.4）

### 6.2 roundtrip 测试（在 **声明的下限版本** 上跑）

- `Model(...).to_protobuf()` 与 `Model.from_protobuf(...)` 在 `protobuf>=7.0.0` 上不抛异常
- oneof 往返后 `WhichOneof("value")` 与设置的那个成员一致，且**只有一个**成员被设置
- `optional` 字段不设置时往返后仍为「未设置」（`HasField` 为 False），而不是被写成默认值
- 标量 map、嵌套 message、repeated message、Timestamp、枚举（含 `enum_storage: name` / `value` 两种模式）的既有往返用例保持通过

### 6.3 版本矩阵测试

- 至少覆盖 `7.0.0`（声明下限）与当前最新 7.x
- CI 应固定在声明下限上跑一次，否则「声明支持 7.x 但只在 7.36 上验证过」这类不一致会再次出现

### 6.4 全量扫描测试

- 扫描 `example/protos/*.proto` 中所有 `map<...>` 字段，断言生成类型与 descriptor 中的 value 类型一致（`MISSING_COUNT == 0` 式的全量断言，而不是只测一个样例）
- **语料必须含 message 值 map 与 enum 值 map**：`example/protos` 里 map 只有 2 个、且都是 `map<string, google.protobuf.Any>`（`example/protos/example.proto:35,40`）→ 生成 `Optional[Dict[str, Any]]` 与正确答案**巧合一致**，所以只扫 example protos 的这套断言**修复前也会通过**，挡不住回归。请把 §附 的 `map<string, Inner>` 与一个 `map<string, SomeEnum>` 纳入扫描语料（R7）

---

## 7. 非目标

这份 PR 不处理：

- 下游业务仓库的兼容 shim，以及已落盘生成物的手工补丁
- `master` 与 `develop` 在 protobuf 声明上的分叉如何合并（需要单独决策：要么把 master 也提到 `>=7.0.0`，要么把 develop 的代码做成双版本兼容）
- `master` 与 `develop` 在 protobuf 声明上的分叉：本 PR 只把声明改成 **`protobuf>=7.34.0`**（PyPI 上不存在 `protobuf==7.0.0`；Python 端最低的 7.x 是 7.34.0）并同步 `README.md` / `README.zh.md` 的版本要求，**`master` 分叉未合并**，仍需单独决策
- `constants.py` 的 `__version__ = "0.1.8"` 与包版本 `0.1.9` 的漂移（§2.5，未在本 PR 范围内）
- oneof 之外的其他 proto3 语义（`proto3_optional` 之外的 presence 细节、`Any` / `Struct` 的既有兼容方案）

---

## 8. 建议 PR 标题

```text
Fix protobuf 7.x descriptor API usage and map value type resolution
```

---

## 9. 建议 PR 描述

```markdown
## Summary

This PR fixes generator-level and runtime-conversion issues in protobuf-pydantic-gen:

- `_to_field_proto()` no longer reads the removed runtime `FieldDescriptor.label`;
  repeated fields use `is_repeated` instead
- `map<string, Msg>` value types resolve to the message type instead of falling back to `Any`
- `get_field_type()` no longer silently returns `Any` for message/enum types whose name is unavailable

## Why

`develop` declares `protobuf>=7.0.0` (commit 7401a65 raised the floor from
`>=5.27.0,<7.0.0`), but the runtime conversion helpers still call
`fd.label`, which protobuf 7.x removed from the runtime `FieldDescriptor`
(neither the upb nor the pure-Python implementation provides it). As a result
`to_protobuf()` and `from_protobuf()` raise `AttributeError` on every generated
model in a 7.x environment.

Separately, `_get_map_field_types()` feeds runtime `FieldDescriptor` objects
into `get_field_type()`, whose branches test `hasattr(field, "type_name")` —
a `FieldDescriptorProto` attribute. Message- and enum-valued maps therefore
fall through to the `Any` fallback and silently lose their nested type.

## Validation

- round-trip tests pass on protobuf 7.0.0 (the declared floor) and on the current 7.x
- `map<string, Msg>` generates `dict[str, Msg]`; scalar maps are unchanged (positive control)
- full-scan test asserts every `map<...>` field's generated type matches its descriptor value type
```

---

## 附：最小复现步骤

```bash
mkdir -p /tmp/ppgen/pb /tmp/ppgen/models
cd /tmp/ppgen

cat > probe.proto <<'EOF'
syntax = "proto3";
package probe.v1;
import "protobuf_pydantic_gen/pydantic.proto";

message Inner {
  string outcome = 1 [(pydantic.field) = {description: "终态" label: "终态"}];
}

message Union {
  string metric = 1 [(pydantic.field) = {description: "指标" required: true label: "指标"}];
  oneof value {
    double numeric_value = 2 [(pydantic.field) = {description: "数值" label: "数值"}];
    string text_value = 3 [(pydantic.field) = {description: "文本" label: "文本"}];
  }
  map<string, Inner> unavailable = 4 [(pydantic.field) = {description: "不可用" label: "不可用"}];
}
EOF

# pydantic.proto 来自随包附带的那份（不要用手抄副本）
PKG_DIR=$(python3 -c "import protobuf_pydantic_gen, os; print(os.path.dirname(os.path.dirname(protobuf_pydantic_gen.__file__)))")

python3 -m grpc_tools.protoc \
  -I . -I "$PKG_DIR" \
  --python_out=pb --pydantic_out=models --pydantic_opt=package_name=probe \
  probe.proto

grep -n 'unavailable' models/probe_model.py     # → dict[str, Any]（应为 dict[str, Inner]）

python3 - <<'PY'
import sys; sys.path.insert(0, 'pb'); sys.path.insert(0, 'models')
from probe_model import Union
Union(metric='M', text_value='a').to_protobuf()   # → AttributeError: ... has no attribute 'label'
PY
```

---

## 附二：复核记录（2026-10-09）

对本文档做逐条源码级复核（宿主只读 git + 源码比对 + 上游官方文档交叉验证）。**结论：行号、机制、版本事实全部成立；4 处表述不成立或定位错位，已就地修正；另有 2 处测试/清单覆盖缺口。**

### 一、已核实成立

| 主张 | 证据 |
|---|---|
| 基线 `7401a65`，父提交 `e90259a`，仅一行 pyproject 差异 | `git log -1 --format='%H %ci %s' 7401a65` → `Update pyproject.toml` 2026-07-26；`git rev-parse 7401a65^` = `e90259aeb4791bae488c545a32b5050e6ea5adb6`；`git diff e90259a 7401a65 --stat` → `1 file changed, 1 insertion(+), 1 deletion(-)` |
| 下游声明与锁定 | `packages/zenmpai-protos/pyproject.toml:28` 与 `zenmpai/uv.lock:1358`（`rev=develop#7401a654…`，包版本 `0.1.9`）逐字一致；`uv.lock:1341-1342` `protobuf` = **7.36.2**，与 §0「复现环境」一致 |
| 2.1 行号与 traceback | `ext.py:180/:270/:278/:448` 与现码逐字一致；`label` 在 protobuf 7.x 被移除属上游事实（v34.0 release notes、commit `0a8ff55`、protobuf.dev Migration Guide：Replacement = `is_repeated()` / `is_required()`；两属性自 6.32.1 起可用） |
| 2.2 判据行号 | `type_mapper.py:76/:88/:110/:137` 逐字一致；`constants.py:11-28` 确实没有 `TYPE_MESSAGE`；生成物佐证 `example/models/example_model.py:79/108` |
| 2.4 oneof | 生成器 `.py` 与 `template.j2` 全仓 `oneof` **零命中**；命中仅在 vendored `descriptor.proto` / `http.proto` / `field_mask.proto` 注释与 `example/protos/Makefile:23 --ts_proto_opt=oneof=unions`；确无 `oneof_decl` / `oneof_index` 读取 |
| 2.5 版本漂移 | `constants.py:8 __version__ = "0.1.8"` vs `pyproject.toml version = "0.1.9"`；`git show master:pyproject.toml:18` = `protobuf>=5.27.0,<7.0.0`；`README.md:43` / `README.zh.md:43` = `protobuf >= 5.27.0, < 7.0.0` 而 develop 声明 `>=7.0.0` |

### 二、不成立 / 已修正

- **R1 §0 的 git 证据（三条全错，结论对）**：见 §0 的复核修正框。
- **R2 §2.2「message/enum 值必然落到兜底 `Any`」**：enum 部分不成立，见 §2.2 复核补注。**这是本次复核新发现的缺陷，原清单没有**，且 §3.2 原定修法拦不住。
- **R3 §2.3 根因定位 + §4.3/§5 补丁落点**：见 §2.3、§4.3、§5 的复核补注。顶层写回在 `:275-277`，不是 `_convert_value`。
- **R4 §0 的 `dist-info/direct_url.json` 证据**：本机**找不到** commit_id = `7401a65` 的安装副本，`zenmpai` 也没有 venv / dist-info（`packages/zenmpai-protos/src/zenmpai_protos/{models,pb}` 均为空目录）。本机实际存在的安装副本：`skill-forge` = `3d5145e`(develop)、`stew/proto/sdk/python` = `b49dc1d`(develop)、`stew/gateway_integration_demo/backend` = `905c57f`(feature/feat-auth, 0.1.8)、`srm-agent/core` = 0.1.5。⇒ §0 的 json 块应按「由 `uv.lock` 推导」表述，不应写成实测。
- **R5 §0「本方案的每一条都在该提交上复现」**：见 §0 的范围修正 —— 下游现网 proto 只能复现 2.1。
- **R6 §0 diff 的 hunk 头**：实际为 `@@ -11,7 +11,7 @@ license = "Apache-2.0"`，且首行上下文是 `dependencies = [`（初稿漏了这行、并把 hunk 头文字写成 `dependencies = [`）。改动行本身完全正确。

### 三、覆盖缺口（已就地补写）

- **R7 §6.4 全量扫描**：`example/protos` 里 map 只有 2 个且都是 `map<string, google.protobuf.Any>`（`example/protos/example.proto:35,40`）→ 生成 `Optional[Dict[str, Any]]` 与正确答案**巧合一致**，该断言修复前也通过，挡不住回归。语料必须补 message 值 map 与 enum 值 map。
- **R8 §3 文件清单**：漏了生成侧 —— `type_mapper.set_default_value`（`:152-183`，取 `DEFAULT_VALUES`）决定 `optional` 标量默认值；`message_processor.py` 完全没有 `proto3_optional` / `has_presence` 判定（grep 零命中），生成侧 presence 缺失比 2.3 描述的更彻底。
- **R9 §2.2 实测来源不同源**：`zenmpai.v1.Inner` 在 zenmpai 仓库中**不存在**（`zenmpai.proto` 仅 27 行 / 2 个 message，全仓 `grep 'message Inner'` 零命中）⇒ 2.2 的实测块来自合成 probe（借用了 `zenmpai.v1` 包名），与 §附 的 `probe.v1` 不同源，文档宜注明。
- **R10 若本 PR 覆盖 R2**，§9 的 Summary 需补一条（enum 值 map 不再生成不存在的 entry 类型名）。

### 四、本轮实测补充（2026-10-09，宿主侧）

复现工件与脚本已落盘：`tmp/probe-enum-map/`（`probe.proto` / `probe2.proto` / `probe3.proto`、`plugin.sh`、`run_checks.py`）。生成用**仓库源码**（`PYTHONPATH=<repo>`）驱动 `protoc`，protobuf 6.33.6（在声明范围内）。

**R2 实测成立，且比初稿描述更严重** —— 生成 `probe.proto` 时 stderr 出现：

```text
2026-10-09 10:37:52,030 - protobuf_pydantic_gen.type_mapper - ERROR - Error getting map field types:
'google._upb._message.FieldDescriptor' object has no attribute 'type_name'
```

即 enum 值确实在 `:106-107` 抛 `AttributeError`，被 `:148-150` 吞掉、生成**照常成功**，产物为：

```text
class Union(BaseModel):
    metric:        str | None            = _Field(default="")
    numeric_value: float | None          = _Field(default=0.0)     # oneof 成员
    text_value:    str | None            = _Field(default="")      # oneof 成员
    unavailable:   dict[str, Any] | None = _Field(default=None)    # 2.2：message 值 → Any
    levels:        LevelsEntry | None    = _Field(default=None)    # R2：LevelsEntry 全文件从未定义
    tags:          dict[str, str] | None = _Field(default=None)    # 正对照
    counts:        dict[str, int] | None = _Field(default=None)    # 正对照
    opt_score:     float | None          = _Field(default=0.0)     # 2.3
    plain_score:   float | None          = _Field(default=0.0)     # 2.3：与 optional 不可区分
```

`grep -n 'Entry\|Level' models/probe_model.py` 只命中 `class Level` 与该注解本身 —— 即 **`LevelsEntry` 在生成物里仅此一现**，生成模块会在 `model_rebuild()` 时因无法解析该注解而失败（import 级阻断，不只是「类型不精确」）。

**2.4 实测，推翻原「声明边界」的推断** —— `probe2`（message 值 map + oneof）的 `to_protobuf()` 不是「只保留最后设置的那个」，而是直接抛：

```text
google.protobuf.json_format.ParseError: Message type "probe2.v1.Union" should not have multiple "value" oneof fields at "Union".
```

**2.2 实测**：`unavailable: dict[str, Any]`（`map<string, Inner>`），正对照 `tags` / `counts` 正常。

### 五、仍未核实（需容器 / 带 protobuf 7.x 的解释器）

- **2.1 仍未见 7.x 实测**：宿主没有「`protobuf>=5.27` + `sqlmodel`」的 py3.11 解释器（现有 venv 只有 4.25.6 / 6.33.6，后者无 `sqlmodel`），而仓库源码的 `pydantic_pb2.py` 要求 `google.protobuf.runtime_version`（≥5.27），在 4.25.6 上直接 import 失败 —— `has label` / `fd.label` → `AttributeError` 这条链必须在容器（或装好 `protobuf==7.36.2` 的环境）里补测。
- **2.3 只测到生成侧**（`opt_score` / `plain_score` 同形），`HasField` 级别的「未设置被写成默认值」仍需容器实测。
- **2.4 的 `ParseError` 需在容器内复测**：那次运行时解析到的是 srm-agent venv 里的旧版 `protobuf_pydantic_gen`（0.1.5，遮蔽了仓库源码），不是仓库源码。
- 2.2 / R2 的**生成侧**已实测（见第四节），无需再补。

### 六、修复实施与验证（2026-10-09）

**实施范围**：2.1 + 2.2 + R2（用户指定）；2.3 / 2.4 待语义决策（见本节末）。

#### 6.1 改动点

| 文件 | 改动 |
|---|---|
| `utils.py` | 新增 `is_repeated_field()` / `is_required_field()`（两种描述符都吃：proto 读 `label`，运行时读 `is_repeated`/`is_required`）与 `field_descriptor_to_proto()`（运行时 `FieldDescriptor` → `FieldDescriptorProto` 的规范化；proto 入参原样返回） |
| `ext.py` | `_to_field_proto()` 改为走规范化（不再读 `fd.label`）；`model2protobuf` 的 repeated 判定（`:278`）与 `protobuf2model`（`:448`）改用 `is_repeated_field()`；`_get_default_value` 的调用点（`:200`）改传 `_to_field_proto(fd)`；`get_type_name()` 收敛为规范化后的 `type_name` |
| `ext.py`（map 运行时） | `model2protobuf` 的 map 分支重写：message 值从 **value 字段**取 `message_type`（原来取的是 map entry 类型）、`Any` 值走 `AnyTransformer`、enum 值转 name、标量直通 |
| `ext.py`（map 反序列化） | `protobuf2model` 的 `_convert_value()` 新增 `model_field_name` 参数，map 分支把 **map 字段名**（如 `inners`）传下去（原来传的是 value 字段名 `value`） |
| `type_mapper.py` | `get_field_type()` 入口规范化入参（根因修复：运行时描述符没有 `type_name`）；兜底不再静默 —— message/enum 走到 `Any` 时 `logger.error` 打出字段名/类型/type_name；`_is_map_field()` / `set_default_value()` 改用 `is_repeated_field()`；`_get_map_field_types()` 的 `except` 改为 `logger.exception`（保留生成不中断，但不再无痕） |
| `message_processor.py` | repeated 判定改用 `is_repeated_field()` |
| `example/tests/test_map_value_types.py` | 新增 14 项回归（map value 类型 × 4、规范化助手 × 4、生成产物 × 1、往返 × 5） |

#### 6.2 实测结果（protobuf 7.36.2 + 仓库源码）

| 项 | 修复前 | 修复后 |
|---|---|---|
| 2.1 `to_protobuf()` / `from_protobuf()` | `AttributeError: 'google._upb._message.FieldDescriptor' object has no attribute 'label'` | 正常往返 |
| 2.2 `map<string, Inner>` | `Optional[Dict[str, Any]]` | `Optional[Dict[str, Inner]]` |
| R2 `map<string, Level>` | `Optional[LevelsEntry]` → 模块 import 时 `PydanticUndefinedAnnotation: name 'LevelsEntry' is not defined` | `Optional[Dict[str, Level]]`，模块可 import |
| 正对照 `map<string, str>` / `int32` / `Any` | 正常 | 正常（不变） |
| 既有测试套件（`example/tests`，排除需 server 的 `test_performance.py`） | **3 failed / 36 passed**（`test_ext_forward_refs`、`test_models` ×2，全部是 `fd.label`） | **53 passed / 0 failed** |
| `example/protos/*.proto` 全量生成物 before/after diff | — | **无差异**（忽略 `@Time` 头） |

**声明下限本身是空区间（新发现）**：PyPI 上**不存在 `protobuf==7.0.0`** —— Python 端在 **7.34.0** 才跳到 7（最低 7.x = `7.34.0`），所以 develop 的 `protobuf>=7.0.0` 实际等价于 `>=7.34.0`，读代码的人会误以为 7.0–7.33 存在。§6.3 要求的「在声明下限上跑一次」已按 **7.34.0** 执行：修复后 **53 passed**（7.34.0），而未修复的基线在同一环境下 **3 failed / 36 passed**。建议把声明改写成 `>=7.34.0`。

#### 6.3 本次实施中新发现的缺陷（原清单没有，已一并修复或登记）

- **R11（已修）**：`model2protobuf` 的 map 分支用 `fd.message_type.full_name`（= **map entry** 类型，如 `Holder.InnersEntry`）当 value 类型 → `map<string, Msg>` 的 `to_protobuf()` 抛 `ParseError: Message type "…InnersEntry" has no field named "outcome"`；`map<string, int32>` 走同一分支 → `AttributeError: 'int' object has no attribute 'model_dump'`。即**只有 string 值与 `Any` 值的 map 曾经能往返**。
- **R12（已修）**：`protobuf2model` 的 map 分支把 value 字段名（`"value"`）当模型字段名传给 `_get_model_cls_by_field()` → `map<string, Msg>` 的 `from_protobuf()` 抛 `ValueError: Field value not found in <class …Holder>`。
- **R13（未修，登记为非目标）**：`bytes` 值的 map 两个方向都不正确（正向需要 base64，反向会把 base64 文本当 bytes）。标量直通后它不再崩溃，但值不保真 —— 需要单独处理，见 §7。
- 旁证：`generator.load_protos()` 把 pool 装载失败降级为 WARNING 后继续，配合原先静默的 `except`，会让「所有 map 类型解析失败」看起来像一次正常生成（本次 `logger.exception` 已让这条链可见）。

#### 6.4 2.3 / 2.4 的实测结论（**已实施：两项均采纳方案 A**）

**修复前**（protobuf 7.36.2）：

```text
# 2.3 ——「未设置」与「值就是 0」产生完全相同的字节
[unset]            HasField('opt_score')=True opt=0.0 bytes=b'\n\x01M\x11\x00\x00\x00\x00\x00\x00\x00\x00'
[opt_score=None]   HasField('opt_score')=True opt=0.0 bytes=b'\n\x01M\x11\x00\x00\x00\x00\x00\x00\x00\x00'
[opt_score=0.0]    HasField('opt_score')=True opt=0.0 bytes=b'\n\x01M\x11\x00\x00\x00\x00\x00\x00\x00\x00'
from_protobuf(<empty message>) -> metric='' opt_score=0.0 plain_score=0.0 inner=None

# 2.4 —— to_protobuf() 直接抛错
ParseError: Message type "probe2.v1.Union" should not have multiple "value" oneof fields at "Union".
```

**修复后**：见 §2.3 / §2.4 各自的「已修」框；回归落在 `test_presence_and_bytes.py` / `test_oneof.py`。

> **更正（R15）**：修复前那三个 `\x11` 字节是 **field 2 = `opt_score`**（被 `None` → 默认值写回），**不是** `plain_score`；`plain_score`（隐式 presence）从未被序列化 —— 隐式 presence 下零值不上线。本节初稿写成「`plain_score` 也被显式序列化」属误读，已更正。

#### 6.5 第二轮实施（2.3 / 2.4 / R13 + 声明下限，2026-10-09）

| 文件 | 改动 |
|---|---|
| `ext.py` | 新增 `_proto3_optional_field_names()`、`_real_oneof_names()`（跳过 synthetic oneof）、`_match_oneof_member()` 及两条匹配谓词、`_select_model_cls()`；`model2protobuf` 增加「proto3 optional 的 `None` → 不写」与「oneof 只设置被选中成员」；`protobuf2model` 增加「未设置的 optional → `None`」「oneof 走 `WhichOneof`」「Union 注解里按 message 名选类」；bytes 正向 base64 编码（标量 + map 值）、反向 base64 解码 |
| `type_mapper.py` | `set_default_value()` 增加 `proto3_optional` 分支（默认值 `None`） |
| `message_processor.py` | 新增 `_process_oneof_field()`；`_process_message()` 识别 synthetic oneof、跳过 oneof 成员、追加合并后的字段 |
| `pyproject.toml` / `README.md` / `README.zh.md` | 声明下限 → **`protobuf>=7.34.0`**（本地检出原为 `>=5.27.0,<7.0.0`，develop 为 `>=7.0.0`） |
| `example/tests/probe_schema.py` | 新增共享的进程内 probe 构造/加载工具（map+bytes+presence 与 oneof 两个 schema，不依赖 protoc） |
| `example/tests/test_presence_and_bytes.py` | 新增 8 项 |
| `example/tests/test_oneof.py` | 新增 7 项 |
| `example/tests/test_map_value_types.py` | 改为复用 `probe_schema`，并补 bytes map 的解析用例 |

**验证（protobuf 7.36.2 与 7.34.0 两个版本都跑过）**

| 项 | 结果 |
|---|---|
| `example/tests`（排除需 server 的 `test_performance.py`） | **69 passed / 0 failed**（修复前基线 3 failed / 36 passed） |
| `example/protos/*.proto` 全量生成物 before/after | **无差异**（忽略 `@Time`） |
| `tmp/probe-enum-map/` protoc 全链路（`run_checks.py`） | oneof 三态、message map、enum map、optional 三态全部 OK |

**本轮新发现并修复**

- **R13（已修）**：`bytes` 的 base64 处理缺失 —— 正向把 `bytes` 直接交给 `ParseDict`（它要 base64 文本）、反向把 `MessageToDict` 的 base64 文本直接当 `bytes`。**不止 map 值**：普通 `bytes` 标量字段同样不保真（`from_protobuf` 拿到的是 base64 文本的 utf-8 编码）。已在 `ext.py` 的两条转换路径统一处理。
- **R14（已修）**：名为 `Union` 的 proto message 会遮蔽生成模块里的 `typing.Union`，使 `Optional[Union[...]]` 在 pydantic 解析时报 `TypeError: cannot be parametrized`。生成的 oneof 注解改用 `_Union` 别名。**§附 的最小复现 proto 里 message 就叫 `Union`**，属真实触发路径。同类遮蔽风险对 `Dict` / `List` / `Any` / `Optional` 同样存在（既有行为，本次未处理）。
- **R15（文档更正）**：见 6.4 的更正框。

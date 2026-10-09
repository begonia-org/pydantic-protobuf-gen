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
- `develop` 的 `pyproject.toml` 是 `protobuf>=7.0.0`，`master` 仍是 `protobuf>=5.27.0,<7.0.0`，`README.md` / `README.zh.md` 跟的是 master 的写法 —— 两分支在这一点上已经分叉。**已修（2026-10-09）**：代码改成能力探测后不再需要 7.x 专属路径，声明与两份 README 统一为 **`protobuf>=5.29.0`**（真实下限由 committed vendored `*_pb2.py` 的 gencode 决定，见 6.6）—— 这同时**消解了分叉**：master 的 `>=5.27.0,<7.0.0` 与本声明方向一致，只差把 `<7.0.0` 上限去掉（`master` 分支本身未动）

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

### 4.1 `label` → `is_repeated` / `is_required`（**已实施：能力探测，不设版本分支**）

```python
fd_proto.label = (
    descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED
    if fd.is_repeated
    else descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
)
```

**已采纳的不是「硬切新 API」，而是能力探测（capability probe）** —— 这也是 protobuf 官方迁移文档给旧版本 runtime/生成物混用时推荐的写法（同型做法见 ray 的 `is_repeated` + `label` 回退）：

- `FieldDescriptor.is_repeated` / `is_required` 自 **protobuf 6.32.1** 起才有；**7.x 删掉了 `label`**；5.27–6.31 的运行时描述符**只有 `label`**。
- 所以判据必须是 `hasattr(field, "is_repeated")` —— 问对象，而不是问安装的版本（版本号比较在 patch 版本上会错，protobuf 自己也这么建议）。
- 实测确认这条分支真的会被走到：`protobuf 5.29.0` 上 `hasattr(FieldDescriptor, "is_repeated") == False`、`label` 存在；`7.36.2` 上相反。四版本矩阵（5.29.0 / 6.33.6 / 7.34.0 / 7.36.2）全绿，见附二·六 6.6。

```python
def is_repeated_field(field) -> bool:
    if isinstance(field, descriptor_pb2.FieldDescriptorProto):
        return field.label == descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED
    if hasattr(field, "is_repeated"):          # protobuf >= 6.32.1
        return field.is_repeated
    return field.label == descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED  # < 6.32.1
```

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
- `master` 分支与 `develop` 在 protobuf 声明上的分叉：本 PR 在 develop 侧把声明定为 **`protobuf>=5.29.0`** 并同步两份 `README`（真实下限 = committed vendored `*_pb2.py` 的 gencode 5.29.0）；**`master` 分支本身未动**，但它只需去掉 `<7.0.0` 上限即可两边一致
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

**声明下限与真实下限是两回事（新发现，最终结论见 6.6）**：PyPI 上**不存在 `protobuf==7.0.0`** —— Python 端在 **7.34.0** 才跳到 7（最低 7.x = `7.34.0`）。但把下限写成 `>=7.34.0` **也是错的**：包内**committed 的 vendored `*_pb2.py`**（`pydantic_pb2.py`、`example/pb/*_pb2.py`）gencode 是 **5.29.0**，protobuf 拒绝「runtime 比 gencode 旧」，所以真正的下限是 **5.29.0**（实测：5.29.0 上 71 passed；5.27.0 上连 `pydantic_pb2` 都 import 不了）。最终把声明改成 **`protobuf>=5.29.0`**。

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
| `pyproject.toml` / `README.md` / `README.zh.md` | 声明 → **`protobuf>=5.29.0`**（第二轮从 `>=7.34.0` 调整过来，理由见 6.6：真实下限由 committed vendored `*_pb2.py` 的 gencode 决定） |
| `example/tests/probe_schema.py` | 新增共享的进程内 probe 构造/加载工具（map+bytes+presence 与 oneof 两个 schema，不依赖 protoc） |
| `example/tests/test_presence_and_bytes.py` | 新增 8 项 |
| `example/tests/test_oneof.py` | 新增 7 项 |
| `example/tests/test_map_value_types.py` | 改为复用 `probe_schema`，并补 bytes map 的解析用例 |

**验证（四版本 protobuf 矩阵，见 6.6）**

| 项 | 结果 |
|---|---|
| `example/tests`（排除需 server 的 `test_performance.py`） | **71 passed / 0 failed**（修复前基线 3 failed / 36 passed） |
| 声明下限那一版（**5.29.0**，运行时描述符只有 `label`） | **71 passed** —— 能力探测的回退分支被真实走到 |
| 中间版（6.33.6，`label` 已废弃、`is_repeated` 已存在） | **71 passed**（走 `is_repeated`，不触发废弃警告） |
| 最低 7.x 与当前 7.x（7.34.0 / 7.36.2，`label` 已删除） | 各 **71 passed** |
| `example/protos/*.proto` 全量生成物 before/after | **无差异**（忽略 `@Time`） |
| `tmp/probe-enum-map/` protoc 全链路（`run_checks.py`） | oneof 三态、message map、enum map、optional 三态全部 OK |

**本轮新发现并修复**

- **R13（已修）**：`bytes` 的 base64 处理缺失 —— 正向把 `bytes` 直接交给 `ParseDict`（它要 base64 文本）、反向把 `MessageToDict` 的 base64 文本直接当 `bytes`。**不止 map 值**：普通 `bytes` 标量字段同样不保真（`from_protobuf` 拿到的是 base64 文本的 utf-8 编码）。已在 `ext.py` 的两条转换路径统一处理。
- **R14（已修）**：名为 `Union` 的 proto message 会遮蔽生成模块里的 `typing.Union`，使 `Optional[Union[...]]` 在 pydantic 解析时报 `TypeError: cannot be parametrized`。生成的 oneof 注解改用 `_Union` 别名。**§附 的最小复现 proto 里 message 就叫 `Union`**，属真实触发路径。同类遮蔽风险对 `Dict` / `List` / `Any` / `Optional` 同样存在（既有行为，本次未处理）。
- **R15（文档更正）**：见 6.4 的更正框。

#### 6.6 版本兼容性（第三轮，2026-10-09）

**为什么不能用「切到新 API + 抬高下限」了事**：那会把兼容性换成声明，而这次事故的起因恰恰是**声明与实现脱节**。`.proto` 生态里 runtime / gencode / 生成器三者版本各自漂移，唯一稳的判据是**能力探测**。

**三条独立的版本约束**（本次全部实测）：

1. **生成器 import**：`pydantic_pb2.py` 依赖 `google.protobuf.runtime_version` → 至少要 5.27；且 committed 的 `pydantic_pb2.py` gencode 是 **5.29.0**，protobuf 拒绝 runtime < gencode → **5.29.0 是真正能 import 的下限**（5.27.0 上直接 `VersionError`）。
2. **运行时描述符 API**：`is_repeated` / `is_required` 自 **6.32.1** 起存在，`label` 在 **7.x 被删除** → 代码必须两者都能走（`hasattr` 探测），否则任一侧区间都会炸。实测 5.29.0：`hasattr(FieldDescriptor, "is_repeated") == False`。
3. **生成物 pb2**：由 protoc 版本决定 gencode，消费方 runtime 不得更旧 —— 所以「在哪个环境生成」也决定了消费侧下限（`example/pb` 是 5.29.0，`tmp/probe-enum-map/pb` 由 5.29.4 生成，故 `run_checks.py` 只能在 ≥5.29.4 的解释器上跑）。

**结论：声明 `protobuf>=5.29.0`（无上限）**：下限由包内 committed gencode 决定（可验证、可复现），上限不设 —— 7.x 及以上靠能力探测与下面的矩阵保持一致。若仍想加保护，可写 `>=5.29.0,<8.0.0`，但那属于「用一个未经证明的假设替代另一个」。

**运行时矩阵（`tmp/probe-enum-map/matrix.sh`，一条命令五版本）** —— 默认走 `uv run --no-project --with protobuf==X` 的**临时环境**（跑完不往仓库落任何东西），`PROBE_VENVS=1` 才用 `tmp/probe*/venv` 的预建环境（更快，但每个 ~70–100MB）；预建 venv 已在清理中删除，需要时按 `tmp/probe-enum-map/README.md` 重建。这里**不装 protoc / grpcio-tools**，所以能覆盖「与声明集合无法共解」的版本（如 7.34.0）。

```text
protobuf 5.29.0            71 passed
protobuf 6.33.6            71 passed
protobuf 7.34.0            71 passed
protobuf 7.35.1            71 passed
protobuf 7.36.2            71 passed
```

（含 2 项新增的回退分支用例：用只带 `label` 的桩对象验证 `is_repeated`/`is_required` 缺失时的回退。）

#### 6.7 安装级约束：`protobuf==X` 能不能装，取决于整集合的可共解性（CI 首跑暴露）

第一版 CI 用的是「先 `pip install -e .`、再 `pip install protobuf==X`」两步 —— **在 GitHub 上红了三行**（5.29.0 / 6.33.6 / 7.34.0 失败，7.36.2 通过），而本地 `matrix.sh` 四行全绿。本地复现给出的原因很清楚：

```text
googleapis-common-protos 1.75.5 requires protobuf<8.0.0,>=6.33.5, but you have protobuf 5.29.0
grpcio-tools 1.84.0 requires protobuf<8.0.0,>=7.35.1, but you have protobuf 5.29.0
→ VersionError: Detected incompatible Protobuf Gencode/Runtime versions（8 个测试模块 import 失败）
```

即：**companion 包也有 gencode，也在抬高 runtime 下限**。把 protobuf 在第二次命令里降级，会让它们停在拒绝该 runtime 的版本上，它们的 pb2 gencode 比 runtime 新 → 连 import 都过不去。`grpcio-tools` 各版本对 protobuf 的要求（PyPI 元数据实测）：

| grpcio-tools | 要求 protobuf |
|---|---|
| 1.71.2 | `>=5.26.1,<6.0dev` |
| 1.81.1 | `>=6.33.5,<7.0.0` |
| 1.82.0 | `>=6.33.5,<8.0.0` |
| 1.83.1 / 1.84.0 | `>=7.35.1,<8.0.0` |

⇒ 可共解的点是 **5.29.x**（配 1.71.x）、**6.33.5+**（配 1.81/1.82）、**7.35.1+**（配 1.83+）；**7.34.0 落在空洞里**（pip 直接 `ResolutionImpossible`：`grpcio-tools 1.83.1/1.84.0 depends on protobuf>=7.35.1`，而更低的候选无法完成解析）。

于是维护两个矩阵，回答两个不同的问题：

| | 覆盖 | 装什么 | 判据 |
|---|---|---|---|
| **安装级** `.github/workflows/tests.yml` | 5.29.0 / 6.33.6 / **7.35.1** / 7.36.2 | `pip install -e . "protobuf==X"`（**单次解析**） | 消费者真能装上的点 |
| **运行时级** `tmp/probe-enum-map/matrix.sh` | 5.29.0 / 6.33.6 / **7.34.0** / 7.35.1 / 7.36.2 | `uv run --with`（**不装** protoc/grpcio-tools） | 生成器代码自身能跑的点 |

单次解析是关键（`pip install -e . "protobuf==X"` 会让解析器回退 companion 包：5.29.0 行自动选 grpcio-tools 1.71.2 + googleapis-common-protos 1.75.0，7.35.1/7.36.2 行选 1.84.0 + 1.75.5）。四条 CI 行的命令都在本地按 CI 的原样跑过：**各 71 passed**。

> 顺带确认了 `>=5.29.0` 这个声明是**可安装**的 —— 这一点此前只有「运行时能跑」的证据，没有「能装上」的证据。

#### 6.8 本轮的其他发现

- **上一提交 e90259a 的生成物没同步**：`example/models/example_model.py`（committed）与当前生成器输出不一致 —— 差异正是 e90259a 引入的 `nullable=`：

```text
-        sa_column=Column(JSON, doc="Emails of the example"),
+        sa_column=Column(JSON, nullable=True, doc="Emails of the example"),
```

  其余生成物（`constant_model.py` / `constraints_model.py` / `example2_model.py` / `example3_model.py` / `helloworld_model.py` / `tables.py`）与当前树一致。即 e90259a 改了生成逻辑但漏了刷新这份 checked-in 生成物（**不是本次改动造成的**；本文档早先「全量生成物 before/after 无差异」的对照是「旧码 vs 新码生成到临时目录」，结论仍然有效）。若要在 CI 里加「生成物最新」闸门，得先修这一处。
- **容器环境事实更正**：项目环境其实存在 —— `/opt/.uv.venv`（Dockerfile `uv sync` 的产物），依赖齐全（`google.api` / pgvector / zstandard / starlette / pytest 都在），protobuf **5.29.4**，跑整套 `example/tests` **71 passed**。问题只是 **PATH 没把 `/opt/.uv.venv/bin` 前置**（`VIRTUAL_ENV` 却指向它），于是 `python3` 解析到系统解释器 `/usr/local/bin/python3`（缺 `googleapis-common-protos`）。所以准确说法是「**系统** python3 跑不了生成器」，而不是「容器 env 跑不了」；要用仓库环境就直接指名 `/opt/.uv.venv/bin/python`。

#### 6.9 构建期上限：代码生成工具决定 vendored gencode（第二版 CI 红的根因）

**现象**：第二版 CI（改为单次解析后）仍红两行 —— 5.29.0 / 6.33.6 的 `Tests` 失败，7.35.1 / 7.36.2 通过；而同样命令在本地四行全绿。

**复现**（干净 checkout：`touch` 一下 `.proto` 触发构建钩子）：`setup.py` 的 `BuildProtoThenPy` 在「生成物缺失或比 `.proto` 旧」时，用**构建环境**里的 `grpc_tools.protoc` 重编译 `protobuf_pydantic_gen/pydantic_pb2.py`。而 `build-system.requires` 原来只写下界（`grpcio-tools>=1.50.0`），隔离构建环境于是装最新的 grpcio-tools（1.84，bundled protobuf 7.35/7.36）→ 生成物 gencode 从 committed 的 **5.29.0** 变成 **7.35.1** → 在这些 runtime 较旧的矩阵行上，9 个测试模块 collection 阶段就 `VersionError`（与 GH 现象一致）。

**这意味着**：包的**真实下限由构建它的环境决定**，而 `pyproject.toml` 声明的是 `protobuf>=5.29.0` —— 与本分支主题（声明与实现脱节）**同一类问题**，也顺带解释了历史上 5.27 → 5.29 的漂移从哪来（谁构建，谁移动下限）。

**修复**：钉住构建期的代码生成工具 —— `build-system.requires` 里 `grpcio-tools==1.71.0`。实测其 protoc 重新生成的 `pydantic_pb2.py` 与 committed 文件**逐字节相同**（gencode 5.29.0），于是构建可复现、声明为真；**升级 gencode 从此是一次显式动作**（必须同时改声明与生成物）。

**闸门**：CI 增加 `git diff --exit-code -- protobuf_pydantic_gen/` —— 构建若改写了 vendored 生成物就**响亮失败**，而不是静默抬高下限。

**验证**：在「强制重生成」场景下 gencode 保持 5.29.0、`git diff` 为空、5.29.0 行 71 passed；四条 CI 命令本地全绿；GitHub Actions 上 **4/4 success**（`bc62417`）。

#### 6.10 生成物的可复现性：依赖「谁生成」而不只是「生成什么」（第三版 CI 红，闸门首跑暴露）

「生成物最新」闸门第一版在 CI 上红（本地却绿），根因有两条，都是**生成环境**而非源码差异：

1. **格式化器是 dev-only 依赖**：模板渲染后由 `template_renderer.format_with_ruff()` 调用 `ruff check --fix --unsafe-fixes` + `ruff format` 收尾；`ruff` 只在 `[dependency-groups] dev`（uv.lock）里，`pip install -e .` 的环境里**没有**。找不到时该函数只 `logger.warning("ruff format failed")` 然后**静默返回未格式化代码** —— 表现就是生成物里留下未使用的 `from typing import Type`、空行位置不同，且**不报错**。
2. **pb2_grpc 带工具版本戳**：`example/pb/*_pb2_grpc.py` 里的 `GRPC_GENERATED_VERSION` 由 grpcio-tools 版本决定 —— lock 是 `1.71.0`，而 CI 的矩阵环境解析到 `1.71.2`，于是 6 个文件全部“过期”。

⇒ 结论：**committed 生成物只在 lock 环境（uv.lock：protobuf 5.29.4 / grpcio-tools 1.71.0 / ruff 0.11.13 / sqlmodel 0.0.24 / pydantic 2.11.4）下可复现**。实测：`uv sync --frozen` 出来的环境生成 → 与 committed **0 个文件差异**（忽略 `@Time`）；只在 lock 环境里补装 `ruff` 也同样 0 差异（说明除了 ruff 与 grpcio-tools 版本戳外无其他环境敏感项）。

**闸门最终形态**：该步骤改用 `python -m pip install -q uv` + `uv sync --frozen`，在 **lock 环境**里生成再逐文件 `diff -I '@Time'` 比对（`@Time` 是生成时间戳，无法稳定）。这样闸门既抓住「改了生成器忘了重生成」，也不因环境差异误报。

**遗留问题（产品侧）→ 已处理**：见 6.11（`ruff` 进运行依赖 + 缺格式化器响亮失败 + 把 ruff 规则集显式化）。

#### 6.11 生成器依赖 ruff：默认安装，且不再随 ruff 版本漂移（已实施）

**决策**：`ruff` 进运行依赖（默认安装）+ 缺格式化器时**响亮失败**；不改用 autopep8 路径。

**改动**

- `pyproject.toml`：`dependencies` 增加 `ruff>=0.11.13`（附注释说明为何是运行依赖：格式化器缺失曾导致静默产出劣化代码）。`uv.lock` 同步（仅 8 行：root 依赖表 + ruff 条目），`uv sync --frozen` 仍有效。**用范围而非精确钉**：输出确定性由下面的参数显式化保证（见实测），精确钉只会给下游（如自带 ruff 的项目）带来解析冲突。
- `template_renderer.format_with_ruff()`：`FileNotFoundError` / `CalledProcessError` 不再 `logger.warning` 后返回未格式化代码，改为抛 `RuntimeError`（带 `pip install ruff` 提示与 ruff 的 stderr）；调用参数显式化：`ruff check --fix --unsafe-fixes --select F401 --target-version py39`、`ruff format --target-version py39`。
- 新增 `example/tests/test_formatter_required.py`（6 项）：ruff 必须可用、格式化确实生效（未使用导入被删）、缺 ruff 响亮失败、ruff 执行失败响亮失败、**注解不被现代化**、**输出不随工作目录变化**。全套 `example/tests` 现为 **77 passed**。

**为什么必须显式化 ruff 规则集（实测，本轮最有价值的发现）**

生成物 = 模板 + protos + **ruff 的规则集**。原先只调 `ruff check --fix --unsafe-fixes`（**吃默认规则集**），而默认规则集在版本间会漂移：

| 调用 | ruff 0.11.13 | ruff 0.16.10 |
|---|---|---|
| 默认（改前） | 与 committed 生成物一致 | **改写注解**：`Optional[x]` → `x \| None`、`Type[...]` → `type[...]`、`-> "X"` → `-> X`，加 `from __future__ import annotations`，并删掉 `# -*- encoding: utf-8 -*-` 头（UP007 / UP009 / FA100 等被默认选上） |
| `--select F401 --target-version py39`（改后） | 与 committed 生成物**逐字节一致** | 与 0.11.13 输出**逐字节一致** |

改前的后果不小：用较新 ruff 生成的代码带 `x | None` 注解，在使用者 `requires-python = ">=3.9"` 的项目里是**运行期错误**（pydantic 会解析注解）—— 即"生成什么代码"取决于生成者装了哪个 ruff。

顺带否掉一个方案：`--select F401,I`（加 isort）**不可用** —— `I` 的第一/三方判定跟随项目根目录，同一份 proto 在 `CWD=/app` 与 `CWD=/app/example/protos` 下生成的 import 布局不同（实测 4 个文件差异），等于用"取决于从哪运行"替换"取决于装了什么版本"。最终只选 `F401`（未使用导入清理），实测三项全绿：0.11.13 == 0.16.10、`CWD=/app` == `CWD=/app/example/protos`、且与 committed 生成物**零差异** —— 所以本次**没有任何生成物改动**。


**遗留风险（钉住之后剩两处）**：`.github/workflows/tests.yml` 覆盖的是**安装级**四行；① 现在有**三条**生成 `pydantic_pb2.py` 的路径 —— 构建期（born by `build-system.requires` 的 pin）、`make -C protobuf_pydantic_gen` 与 pre-commit 钩子（用环境里的 protoc），它们必须在**同一 gencode** 上对齐（本机：requirements.txt 与容器 env 都已钉 1.71.0），偏移由 CI 的 `git diff --exit-code -- protobuf_pydantic_gen/` 闸门发现；② **运行时级**矩阵（含 7.34.0 这类与声明集合无法共解的版本）CI 覆盖不到，仍需人工跑 `tmp/probe-enum-map/matrix.sh`。

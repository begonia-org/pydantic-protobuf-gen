# Usage / 使用说明

## English

### Verified Entry Point

The verified release workflow uses `grpc_tools.protoc` together with the installed `protoc-gen-pydantic` plugin.

Repository-validated example:

```shell
python3 -m grpc_tools.protoc \
  --proto_path=./example/protos \
  --proto_path=./protos \
  --proto_path=. \
  --python_out=./example/pb \
  --pyi_out=./example/pb \
  --grpc_python_out=./example/pb \
  --pydantic_out=./example/models \
  ./example/protos/constant.proto \
  ./example/protos/example2.proto \
  ./example/protos/example.proto
```

### What The Generator Emits

For the files included in the request, the generator can emit:

- `*_model.py` for model code
- `messages.json`
- `fields.json`
- `services.json`
- `tables.py` when at least one generated message is a table model and table export generation is enabled

### Standard Protobuf Outputs

`--python_out`, `--pyi_out`, and `--grpc_python_out` are still provided by `grpc_tools.protoc` itself. The custom plugin only handles `--pydantic_out`.

### Include Path Rules

Make sure every imported proto file is reachable from one of the `--proto_path` directories. For repository examples, that means:

- `./example/protos` for example schemas
- `./protos` for shared extension schemas
- `.` when local imports resolve from the repository root

### Configuration Surface

The current release manual only documents configuration that is implemented in code today.

Environment variables:

| Variable | Meaning | Default |
| --- | --- | --- |
| `PROTOBUF_PYDANTIC_LOG_LEVEL` | Logging level | `INFO` |
| `PROTOBUF_PYDANTIC_MAX_LINE_LENGTH` | Formatting width for generated code | `120` |
| `PROTOBUF_PYDANTIC_SQLMODEL` | Optional SQLModel-related config hook | `false` |
| `PROTOBUF_PYDANTIC_SKIP_GOOGLE` | Skip selected Google protobuf types | `true` |
| `PROTOBUF_PYDANTIC_GENERATE_TABLES` | Emit `tables.py` | `true` |
| `PROTOBUF_PYDANTIC_TABLE_ALIAS_SUFFIX` | Alias suffix in `tables.py` | `Row` |

Proto annotations remain the primary way to control field and message behavior. See `PROTO_EXTENSIONS.md`.

### Notes On Historical Parameters

Older repository examples mentioned custom plugin options and companion client-generation switches. Those paths are not implemented in the verified GA workflow and have been removed from the maintained example commands.

## 中文

### 已验证入口

当前正式版本中已验证的工作流，是通过 `grpc_tools.protoc` 调用已安装的 `protoc-gen-pydantic` 插件。

仓库内已验证的示例命令：

```shell
python3 -m grpc_tools.protoc \
  --proto_path=./example/protos \
  --proto_path=./protos \
  --proto_path=. \
  --python_out=./example/pb \
  --pyi_out=./example/pb \
  --grpc_python_out=./example/pb \
  --pydantic_out=./example/models \
  ./example/protos/constant.proto \
  ./example/protos/example2.proto \
  ./example/protos/example.proto
```

### 生成器会输出什么

针对请求中包含的 proto 文件，生成器可以输出：

- `*_model.py`：模型代码
- `messages.json`
- `fields.json`
- `services.json`
- `tables.py`：当至少一个 message 被生成为表模型且允许导出表别名时生成

### 标准 protobuf 输出

`--python_out`、`--pyi_out` 和 `--grpc_python_out` 仍然由 `grpc_tools.protoc` 本身处理，自定义插件只负责 `--pydantic_out`。

### Include Path 规则

所有被 import 的 proto 文件，都必须能从某个 `--proto_path` 目录下找到。对于仓库示例，这通常意味着：

- `./example/protos`：示例 schema
- `./protos`：共享扩展 schema
- `.`：当本地 import 需要从仓库根目录解析时

### 配置面

本次正式手册只记录代码中当前已经实现的配置项。

环境变量如下：

| 变量 | 含义 | 默认值 |
| --- | --- | --- |
| `PROTOBUF_PYDANTIC_LOG_LEVEL` | 日志级别 | `INFO` |
| `PROTOBUF_PYDANTIC_MAX_LINE_LENGTH` | 生成代码格式化行宽 | `120` |
| `PROTOBUF_PYDANTIC_SQLMODEL` | SQLModel 相关配置钩子 | `false` |
| `PROTOBUF_PYDANTIC_SKIP_GOOGLE` | 跳过部分 Google protobuf 类型 | `true` |
| `PROTOBUF_PYDANTIC_GENERATE_TABLES` | 是否生成 `tables.py` | `true` |
| `PROTOBUF_PYDANTIC_TABLE_ALIAS_SUFFIX` | `tables.py` 中的别名后缀 | `Row` |

字段和消息的实际控制方式仍然以 proto 注解为主，详见 `PROTO_EXTENSIONS.md`。

### 关于历史参数示例

仓库中旧文档曾出现过自定义插件参数和配套客户端生成开关。这些路径不属于本次正式 GA 文档的已验证范围，也已经从维护中的示例命令中移除。
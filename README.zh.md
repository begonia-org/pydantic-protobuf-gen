[中文](README.zh.md) | [English](README.md)

# protobuf-pydantic-gen

protobuf-pydantic-gen 是一个面向 Python 的代码生成工具，用来把 Protocol Buffer schema 转成 Pydantic 和 SQLModel 模型。它把 protobuf 往返转换方法保留在生成类旁边，同时输出描述 message 和 service 的元数据文件，让一份 `.proto` 定义可以同时驱动校验模型、表模型和 Python 侧业务代码。

## 项目简介

这个项目适合已经把 Protocol Buffers 当作领域模型事实来源，但又希望在 Python 里获得更易用模型层的团队。

## 特性功能

- 从 `.proto` message 直接生成 Pydantic `BaseModel`。
- 当 message 声明 `(pydantic.database).as_table = true` 时生成 SQLModel 表模型。
- 在生成模型上保留 `to_protobuf()` 与 `from_protobuf()`，支持 protobuf 往返转换。
- 输出 `messages.json`、`fields.json`、`services.json`、`tables.py` 等配套元数据产物。
- 通过重建延后注解，保留同文件前向引用和嵌套消息关系。
- 通过 `(pydantic.field)`、`(pydantic.database)` 等 proto 注解控制字段和消息生成行为。
- 让 Python protobuf stub 和应用侧模型生成处于同一条工作流中。

## 为什么用它

- 让 protobuf schema、运行时数据校验和持久化模型保持一致。
- 避免在大规模 proto 上重复手写 Pydantic 或 SQLModel 定义。
- 通过 proto 注解控制生成行为，而不是把模型语义散落在 Python 代码里。
- 除了代码，还能产出机器可读的元数据，方便做检查、注册或自动化处理。

## 典型工作流

1. 在 `.proto` 文件中定义 message 和自定义注解。
2. 通过 `grpc_tools.protoc` 调用 `protoc-gen-pydantic` 插件。
3. 在 Python 应用中导入生成模型。
4. 用 `to_protobuf()` 和 `from_protobuf()` 在模型与 protobuf message 之间转换。

## 五分钟快速开始

下面这套仓库示例覆盖了项目的主路径：生成 Python protobuf stub、生成模型，并验证 protobuf 往返转换。

## 环境要求

- Python 3.9 及以上。
- 环境中可用 `protoc` 与 `grpcio-tools`。
- `protobuf >= 5.27.0, < 7.0.0`。
- `pydantic >= 2.4.1`。
- 如需生成表模型，安装 `sqlmodel >= 0.0.19`。

## 安装

安装包：

```shell
pip install protobuf-pydantic-gen
```

确保扩展 schema 能被 proto include path 找到。本仓库中的文件位置是 `protos/protobuf_pydantic_gen/pydantic.proto`；在你自己的项目里，建议把该文件 vendoring 到公共 proto 目录。

如果需要容器化开发，仓库提供了基于 Python 3.11 和 Debian Bookworm 的 [Dockerfile](Dockerfile)。

先生成 protobuf stub 与 Pydantic/SQLModel 输出：

```shell
mkdir -p example/pb example/models

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

再运行代表性的模型测试：

```shell
pytest example/tests/test_models.py -q
```

最后使用生成模型：

```python
from example.models.example_model import Example

model = Example(name="demo", age=1)
proto = model.to_protobuf()
roundtrip = Example.from_protobuf(proto)

assert roundtrip.name == "demo"
```

更完整的步骤与验证说明见 [QUICKSTART.md](QUICKSTART.md)。

## 生成产物

每个被处理的 proto 文件可以产出以下内容：

- `*_model.py`：生成的 Pydantic 与 SQLModel 类。
- `*_pb2.py`、`*_pb2.pyi`、`*_pb2_grpc.py`：`grpc_tools.protoc` 标准 Python 输出。
- `messages.json`：message 元数据。
- `fields.json`：field 元数据。
- `services.json`：从 descriptor 提取的 service 元数据。
- `tables.py`：对 SQLModel 表类做统一别名导出的反腐层。

## 配置摘要

当前项目中已经实现并公开的配置面位于 [protobuf_pydantic_gen/config.py](protobuf_pydantic_gen/config.py)：

| 环境变量 | 作用 | 默认值 |
| --- | --- | --- |
| `PROTOBUF_PYDANTIC_LOG_LEVEL` | 生成器日志级别 | `INFO` |
| `PROTOBUF_PYDANTIC_MAX_LINE_LENGTH` | 格式化行宽 | `120` |
| `PROTOBUF_PYDANTIC_SQLMODEL` | SQLModel 相关配置钩子 | `false` |
| `PROTOBUF_PYDANTIC_SKIP_GOOGLE` | 跳过部分 Google protobuf 类型 | `true` |
| `PROTOBUF_PYDANTIC_GENERATE_TABLES` | 存在表模型时输出 `tables.py` | `true` |
| `PROTOBUF_PYDANTIC_TABLE_ALIAS_SUFFIX` | `tables.py` 中的别名后缀 | `Row` |

生成类的实际形态主要由 proto 注解控制，尤其是 `(pydantic.field)` 与 `(pydantic.database)`。

## 文档导航

- [QUICKSTART.md](QUICKSTART.md)：从 proto 到生成模型的最短验证路径。
- [docs/INSTALLATION.md](docs/INSTALLATION.md)：环境安装与打包说明。
- [docs/USAGE.md](docs/USAGE.md)：protoc 入口、输出与工作流细节。
- [docs/PROTO_EXTENSIONS.md](docs/PROTO_EXTENSIONS.md)：模型生成注解参考。
- [docs/SQLMODEL_GUIDE.md](docs/SQLMODEL_GUIDE.md)：表模型行为、约束与 `tables.py`。
- [docs/RUNTIME_CONVERSION.md](docs/RUNTIME_CONVERSION.md)：运行时 protobuf 与模型转换 API。
- [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)：常见问题与排查说明。

## 仓库结构

- [example](example) 是本次快速开始所依赖的已验证模型生成示例。
- [protobuf_pydantic_gen](protobuf_pydantic_gen) 包含生成器主体、模板、运行时转换辅助代码和类型映射逻辑。
- [protos](protos) 包含共享 proto 定义以及生成器使用的扩展 schema。
- [tests](tests) 包含生成逻辑和运行时转换的回归测试。
- [example/frontend](example/frontend)、[example/web](example/web) 与 [protobuf-typescript-client-gen](protobuf-typescript-client-gen) 仍作为遗留或相邻资产保留在仓库中，但不是当前 Python 模型生成工作流的重点。

## 当前维护重点

本仓库当前持续维护并文档化的核心路径，是 Python 的 protoc 插件及其运行时辅助能力。历史上的网关相关流程和部分客户端资产仍保留在仓库中，但首页文档的重点放在 Python 模型生成与 protobuf 往返转换。

## 贡献

提交变更时应保证文档描述与可执行行为一致。凡是调整生成逻辑，都应同时更新相关文档和测试。

## 许可证

项目采用 Apache 2.0 License，见 [LICENSE](LICENSE)。




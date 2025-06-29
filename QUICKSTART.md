# Quickstart / 快速开始

This quickstart documents the shortest verified path in the current repository release scope: generate Python protobuf stubs and Pydantic/SQLModel models from the example protos, then validate round-trip conversion.

本快速开始只覆盖当前仓库已验证的正式发布范围：从示例 proto 生成 Python protobuf stub 与 Pydantic/SQLModel 模型，并验证往返转换。

## 1. Prerequisites / 前置条件

- Python 3.9+
- `protoc`
- `grpcio-tools`
- Installed package or editable workspace dependencies

```shell
pip install protobuf-pydantic-gen grpcio-tools
```

If you work inside this repository, `uv sync` is the preferred setup path.

如果你在本仓库内操作，推荐使用 `uv sync` 初始化环境。

## 2. Generate Models / 生成模型

From the repository root, run:

在仓库根目录执行：

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

This command validates three things at once:

这个命令同时验证三件事：

- `grpc_tools.protoc` can find the plugin entrypoint `protoc-gen-pydantic`.
- The custom annotation schema `protobuf_pydantic_gen/pydantic.proto` is on the include path.
- The generator can emit metadata files and `tables.py` alongside model files.

## 3. Inspect the Outputs / 查看输出

You should now have or refresh the following files:

此时你应当已经得到或刷新以下文件：

- `example/models/example_model.py`
- `example/models/example2_model.py`
- `example/pb/example_pb2.py`
- `messages.json`
- `fields.json`
- `services.json`
- `tables.py`

`example_model.py` demonstrates both model styles used by the project:

`example_model.py` 同时展示了本项目的两种生成模型：

- `Nested`, a regular Pydantic `BaseModel`
- `Example`, a SQLModel table because `(pydantic.database).as_table = true`

## 4. Validate Round-Trip Conversion / 验证往返转换

Run the representative test file:

执行代表性测试：

```shell
pytest example/tests/test_models.py -q
```

This test suite verifies model defaults, nested message handling, enums, and `to_protobuf()` / `from_protobuf()` round-trip behavior.

这组测试会验证默认值、嵌套消息、枚举，以及 `to_protobuf()` / `from_protobuf()` 的往返行为。

## 5. Use the Generated Model / 使用生成模型

```python
from example.models.example_model import Example

model = Example(name="demo", age=1)
proto = model.to_protobuf()
clone = Example.from_protobuf(proto)

assert clone.name == model.name
assert clone.age == model.age
```

## 6. What This Quickstart Covers / 本快速开始覆盖的范围

Included:

已覆盖：

- Python protoc plugin execution
- Pydantic model generation
- SQLModel table generation
- Metadata file generation
- Runtime protobuf round-trip conversion

Not included in the current verified release path:

不属于当前已验证正式发布路径：

- Deprecated gateway generation flow
- Generated HTTP clients
- TypeScript client generation
- Frontend demo applications

Continue with the detailed manual:

继续阅读正式手册：

- [docs/INSTALLATION.md](docs/INSTALLATION.md)
- [docs/USAGE.md](docs/USAGE.md)
- [docs/PROTO_EXTENSIONS.md](docs/PROTO_EXTENSIONS.md)
- [docs/SQLMODEL_GUIDE.md](docs/SQLMODEL_GUIDE.md)
- [docs/RUNTIME_CONVERSION.md](docs/RUNTIME_CONVERSION.md)
- [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)

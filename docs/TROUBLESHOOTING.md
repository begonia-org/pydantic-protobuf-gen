# Troubleshooting / 常见问题

## English

### `protoc-gen-pydantic: program not found or is not executable`

The package is either not installed or its script directory is not on your `PATH`.

Try:

```shell
pip install protobuf-pydantic-gen
protoc-gen-pydantic --version
```

### `protobuf_pydantic_gen/pydantic.proto: File not found`

Your `--proto_path` list does not include the directory that contains `protobuf_pydantic_gen/pydantic.proto`.

In this repository, add `--proto_path=./protos`.

### `tables.py` was not generated

Check both conditions:

- At least one message has `(pydantic.database).as_table = true`
- `PROTOBUF_PYDANTIC_GENERATE_TABLES` is not set to `false`

### Forward references fail in a handwritten model

If you call `protobuf2model()` with your own Pydantic model and use postponed or string annotations, call `model_rebuild()` after defining the class.

### Why are gateway, client, or TypeScript features missing from this manual?

Gateway-related functionality has been deprecated. Legacy client and TypeScript assets may still exist in the repository, but the current release manual only covers the Python generator and runtime conversion flow that was validated end to end.

## 中文

### `protoc-gen-pydantic: program not found or is not executable`

这通常说明包没有安装，或者脚本目录不在 `PATH` 中。

可执行：

```shell
pip install protobuf-pydantic-gen
protoc-gen-pydantic --version
```

### `protobuf_pydantic_gen/pydantic.proto: File not found`

你的 `--proto_path` 列表里没有包含 `protobuf_pydantic_gen/pydantic.proto` 所在目录。

在本仓库里，需要加入 `--proto_path=./protos`。

### 没有生成 `tables.py`

同时检查两个条件：

- 至少有一个 message 设置了 `(pydantic.database).as_table = true`
- `PROTOBUF_PYDANTIC_GENERATE_TABLES` 没有被设成 `false`

### 手写模型的前向引用失败

如果你用自定义 Pydantic 模型调用 `protobuf2model()`，并且使用了延后注解或字符串注解，请在类定义完成后调用 `model_rebuild()`。

### 为什么手册里没有网关、客户端或 TypeScript 能力？

网关相关功能已经废弃。遗留的客户端和 TypeScript 资产可能仍然存在于仓库中，但当前手册只描述已经端到端验证过的 Python 生成器与运行时转换流程。
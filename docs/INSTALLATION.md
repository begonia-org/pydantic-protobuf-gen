# Installation / 安装说明

## English

### Runtime Requirements

- Python 3.9 or newer
- `protoc`
- `grpcio-tools`
- `protobuf >= 5.27.0, < 7.0.0`
- `pydantic >= 2.4.1`

If you plan to generate table models, also install `sqlmodel` and the SQLAlchemy extras your own project needs.

### Install From PyPI

```shell
pip install protobuf-pydantic-gen
```

The package exposes the protoc plugin entrypoint `protoc-gen-pydantic`.

You can verify that the installed executable is on your `PATH` with:

```shell
protoc-gen-pydantic --version
```

### Development Install In This Repository

The repository is set up for `uv`-based development:

```shell
uv sync --all-packages
```

This is the preferred path if you want to regenerate the example outputs, run tests, or work on the generator itself.

### Make `pydantic.proto` Available

Your proto include paths must contain `protobuf_pydantic_gen/pydantic.proto`.

In this repository the file is already available at:

- `protos/protobuf_pydantic_gen/pydantic.proto`

In your own project, vendor that file into a shared include directory and add that directory to `--proto_path`.

### Container Setup

The repository ships a Docker image definition in `Dockerfile`.

Build it with:

```shell
docker build -t protobuf-pydantic-gen .
```

The current image uses Python 3.11 on Debian Bookworm and installs `protoc`, `uv`, and the project dependencies.

## 中文

### 运行环境要求

- Python 3.9 或更高版本
- `protoc`
- `grpcio-tools`
- `protobuf >= 5.27.0, < 7.0.0`
- `pydantic >= 2.4.1`

如果你需要生成表模型，还应安装 `sqlmodel` 以及项目自身需要的 SQLAlchemy 相关依赖。

### 从 PyPI 安装

```shell
pip install protobuf-pydantic-gen
```

安装后会暴露 protoc 插件入口 `protoc-gen-pydantic`。

可通过下面的命令确认可执行文件已经在 `PATH` 中：

```shell
protoc-gen-pydantic --version
```

### 在本仓库内进行开发安装

本仓库默认使用 `uv` 进行开发环境初始化：

```shell
uv sync --all-packages
```

如果你要重新生成示例输出、运行测试或修改生成器本身，这是推荐路径。

### 让 `pydantic.proto` 可被发现

你的 proto include path 中必须包含 `protobuf_pydantic_gen/pydantic.proto`。

在本仓库中，该文件位置为：

- `protos/protobuf_pydantic_gen/pydantic.proto`

在你自己的项目里，建议把它 vendoring 到公共 proto 目录，然后把该目录加入 `--proto_path`。

### 容器环境

仓库自带 `Dockerfile`。

构建命令：

```shell
docker build -t protobuf-pydantic-gen .
```

当前镜像基于 Debian Bookworm 的 Python 3.11，并预装了 `protoc`、`uv` 和项目依赖。
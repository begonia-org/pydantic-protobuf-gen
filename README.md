[English](README.md) | [中文](README.zh.md)

# protobuf-pydantic-gen

protobuf-pydantic-gen is a Python code generator that turns Protocol Buffer schemas into Pydantic and SQLModel models. It keeps protobuf conversion helpers close to the generated classes, preserves schema metadata as companion files, and lets a single `.proto` definition drive validation, storage-oriented models, and Python-side application code.

## Overview

This project is built for teams that already use Protocol Buffers as the source of truth but want a more ergonomic Python model layer.

## Features

- Generate Pydantic `BaseModel` classes directly from `.proto` messages.
- Generate SQLModel table classes when a message sets `(pydantic.database).as_table = true`.
- Keep `to_protobuf()` and `from_protobuf()` helpers on generated models for round-trip conversion.
- Emit metadata files such as `messages.json`, `fields.json`, `services.json`, and `tables.py` for downstream tooling.
- Preserve same-file forward references and nested message relationships in generated output.
- Control field and message behavior through proto annotations such as `(pydantic.field)` and `(pydantic.database)`.
- Keep generated Python protobuf stubs and application-facing models in the same workflow.

## Why Use It

- Keep protobuf schema, runtime validation, and persistence-facing models aligned.
- Avoid hand-writing repetitive Pydantic or SQLModel definitions for large proto surfaces.
- Use proto annotations to control model behavior instead of scattering Python-only model metadata.
- Generate machine-readable metadata alongside code for inspection, registries, or automation.

## Typical Workflow

1. Define messages and custom annotations in `.proto` files.
2. Run `grpc_tools.protoc` with the `protoc-gen-pydantic` plugin.
3. Import the generated models in your Python application.
4. Convert between generated models and protobuf messages with `to_protobuf()` and `from_protobuf()`.

## Five-Minute Quickstart

The following repository example covers the main project workflow: generate Python protobuf stubs, generate models, then validate protobuf round-trip behavior.

## Requirements

- Python 3.9 or newer.
- `protoc` and `grpcio-tools` available in your environment.
- `protobuf >= 5.27.0, < 7.0.0`.
- `pydantic >= 2.4.1`.
- `sqlmodel >= 0.0.19` when you generate table models.

## Installation

Install the package:

```shell
pip install protobuf-pydantic-gen
```

Make the extension schema available on your proto include path. In this repository it lives at `protos/protobuf_pydantic_gen/pydantic.proto`; in your own project you should vendor that file into a shared proto include directory.

For container-based development, the repository also ships a [Dockerfile](Dockerfile) based on Python 3.11 and Debian Bookworm.

Generate protobuf stubs and Pydantic/SQLModel outputs:

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

Run the representative model tests:

```shell
pytest example/tests/test_models.py -q
```

Use the generated model:

```python
from example.models.example_model import Example

model = Example(name="demo", age=1)
proto = model.to_protobuf()
roundtrip = Example.from_protobuf(proto)

assert roundtrip.name == "demo"
```

See [QUICKSTART.md](QUICKSTART.md) for a fuller walkthrough and validation notes.

## Generated Outputs

For each processed proto file, the plugin can emit:

- `*_model.py`: generated Pydantic and SQLModel classes.
- `*_pb2.py`, `*_pb2.pyi`, `*_pb2_grpc.py`: standard Python protobuf outputs from `grpc_tools.protoc`.
- `messages.json`: message-level metadata.
- `fields.json`: field-level metadata.
- `services.json`: service metadata extracted from the proto descriptors.
- `tables.py`: an anti-corruption layer that re-exports SQLModel table classes with a configurable alias suffix.

## Configuration Summary

The current project configuration surface is implemented in [protobuf_pydantic_gen/config.py](protobuf_pydantic_gen/config.py):

| Environment Variable | Purpose | Default |
| --- | --- | --- |
| `PROTOBUF_PYDANTIC_LOG_LEVEL` | Generator log level | `INFO` |
| `PROTOBUF_PYDANTIC_MAX_LINE_LENGTH` | Formatting width | `120` |
| `PROTOBUF_PYDANTIC_SQLMODEL` | Optional SQLModel-related configuration hook | `false` |
| `PROTOBUF_PYDANTIC_SKIP_GOOGLE` | Skip selected Google protobuf types | `true` |
| `PROTOBUF_PYDANTIC_GENERATE_TABLES` | Emit `tables.py` when table models exist | `true` |
| `PROTOBUF_PYDANTIC_TABLE_ALIAS_SUFFIX` | Alias suffix used in `tables.py` | `Row` |

Proto annotations remain the primary way to shape generated classes, especially `(pydantic.field)` and `(pydantic.database)`.

## Documentation

- [QUICKSTART.md](QUICKSTART.md): shortest validated path from proto to generated models.
- [docs/INSTALLATION.md](docs/INSTALLATION.md): environment setup and packaging notes.
- [docs/USAGE.md](docs/USAGE.md): protoc entrypoints, outputs, and workflow details.
- [docs/PROTO_EXTENSIONS.md](docs/PROTO_EXTENSIONS.md): model-generation annotations reference.
- [docs/SQLMODEL_GUIDE.md](docs/SQLMODEL_GUIDE.md): table-model behavior, constraints, and `tables.py`.
- [docs/RUNTIME_CONVERSION.md](docs/RUNTIME_CONVERSION.md): runtime protobuf and model conversion APIs.
- [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md): common problems and verified fixes.

## Repository Layout

- [example](example) contains the validated model-generation example used by the quickstart.
- [protobuf_pydantic_gen](protobuf_pydantic_gen) contains the generator, templates, runtime conversion helpers, and type mapping logic.
- [protos](protos) contains shared proto definitions and the extension schema used by the generator.
- [tests](tests) contains regression coverage for generation behavior and runtime conversion.
- [example/frontend](example/frontend), [example/web](example/web), and [protobuf-typescript-client-gen](protobuf-typescript-client-gen) remain in the repository as legacy or adjacent assets, but they are not the primary focus of the current Python model-generation workflow.

## Current Focus

The actively documented and verified path in this repository is the Python protoc plugin together with its runtime helpers. Historical gateway-related flows and some generated client assets still exist in the repository, but the maintained documentation focuses on Python model generation and protobuf round-trip support.

## Contributing

Pull requests should keep the documented behavior aligned with executable behavior. When updating generation behavior, update the relevant documentation and tests in the same change.

## License

This project is licensed under the Apache 2.0 License. See [LICENSE](LICENSE).
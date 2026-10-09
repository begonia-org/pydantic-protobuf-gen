# probe-enum-map — protobuf 7.x 兼容与 map value 类型修复的复现工件

配套文档：`docs/protobuf-pydantic-gen-protobuf7兼容与类型保真修复PR方案.md`（见「附二·四 / 附二·六」）。

## 工件

| 文件 | 作用 |
|---|---|
| `probe.proto` | `map<string, Inner>` + `map<string, Level>`（enum 值）+ `map<string, string>` + `map<string, int32>` + `oneof` + proto3 `optional` —— 覆盖 R2 / 2.2 / 2.3 / 2.4 |
| `probe2.proto` | 去掉 enum map，用于单独暴露 `oneof` 的 `ParseError`（2.4） |
| `probe3.proto` | 只有 `optional double` + `double`，用于 `HasField` 级别的 presence 观测（2.3） |
| `plugin.sh` | 以「仓库源码」作为 protoc 插件运行：`PROBE_REPO` 指定包根、`PROBE_PYTHON` 指定解释器 |
| `run_checks.py` | 导入三个 probe 的生成模型并做往返检查（打印字段注解、`to_protobuf`/`from_protobuf` 结果与异常） |
| `inproc_gen.py` | 不依赖 protoc，在进程内驱动 `CodeGenerator`（回归测试 `example/tests/test_map_value_types.py` 用的同一路径） |
| `pb/`、`models/` | 生成产物（可重新生成，不必保留） |

## 环境

两个隔离 venv（容器内、位于本仓库 `tmp/` 下，可随时删除后用下面命令重建）：

```bash
# 7.36.2（zenmpai 实际运行时版本）
uv venv /app/tmp/probe7/venv
uv pip install --python /app/tmp/probe7/venv/bin/python "protobuf==7.36.2" sqlmodel \
  googleapis-common-protos jinja2 grpcio pytest pytest-asyncio autopep8 inflection peewee pgvector
uv pip install --python /app/tmp/probe7/venv/bin/python --no-deps grpcio-tools==1.71.0

# 7.34.0（PyPI 上最低的 7.x —— 不存在 protobuf==7.0.0）
uv venv /app/tmp/probe-floor/venv
uv pip install --python /app/tmp/probe-floor/venv/bin/python "protobuf==7.34.0" sqlmodel \
  googleapis-common-protos jinja2 grpcio pytest pytest-asyncio autopep8 inflection peewee pgvector
```

## 跑法

```bash
cd /app/tmp/probe-enum-map

# 1) 生成（插件跑仓库源码；生成侧只需 5.27+ 的 protobuf）
for p in probe probe2 probe3; do
  PROBE_PYTHON=/app/tmp/probe7/venv/bin/python PROBE_REPO=/app \
  python3 -m grpc_tools.protoc -I . -I /app \
    --plugin=protoc-gen-pydantic=$PWD/plugin.sh \
    --python_out=pb --pydantic_out=models --pydantic_opt=package_name=$p $p.proto
done

# 2) 运行时检查（换解释器即可切换 protobuf 版本）
PYTHONPATH=/app /app/tmp/probe7/venv/bin/python run_checks.py
PYTHONPATH=/app /app/tmp/probe-floor/venv/bin/python run_checks.py

# 3) 进程内生成（无 protoc）
PYTHONPATH=/app /app/tmp/probe7/venv/bin/python inproc_gen.py
```

## 仓库测试套件 / 基线对照

```bash
# 当前代码
cd /app && PYTHONPATH=/app /app/tmp/probe7/venv/bin/python -m pytest example/tests \
  --ignore=example/tests/test_performance.py -q

# 未修复的基线（HEAD=e90259a 的纯副本，不触碰工作区）
mkdir -p /tmp/ppgen-baseline-e90259a && git -C /app archive HEAD | tar -x -C /tmp/ppgen-baseline-e90259a
cd /tmp/ppgen-baseline-e90259a && PYTHONPATH=/tmp/ppgen-baseline-e90259a \
  /app/tmp/probe7/venv/bin/python -m pytest example/tests \
  --ignore=example/tests/test_performance.py -q
```

`test_performance.py` 需要 `example.client`（仓库里不存在），两侧都排除。

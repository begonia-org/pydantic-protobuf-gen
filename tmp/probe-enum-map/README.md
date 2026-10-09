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

四个隔离 venv（**可选**：默认矩阵走 `uv run --with` 的临时环境，不落在仓库里；只有跑 `PROBE_VENVS=1` 时才用它们）。它们位于本仓库 `tmp/` 下，命中 `.gitignore` 的 `venv/` 规则，可随时删除后用下面命令重建：

```bash
# 5.29.0 —— 声明的下限（由 committed vendored *_pb2.py 的 gencode 决定）
uv venv /app/tmp/probe529/venv
uv pip install --python /app/tmp/probe529/venv/bin/python "protobuf==5.29.0" sqlmodel \
  googleapis-common-protos jinja2 grpcio pytest pytest-asyncio autopep8 inflection peewee pgvector

# 6.33.6 —— label 已废弃、is_repeated 已存在
uv venv /app/tmp/probe633/venv
uv pip install --python /app/tmp/probe633/venv/bin/python "protobuf==6.33.6" sqlmodel \
  googleapis-common-protos jinja2 grpcio pytest pytest-asyncio autopep8 inflection peewee pgvector

# 7.34.0 —— PyPI 上最低的 7.x（不存在 protobuf==7.0.0）
uv venv /app/tmp/probe-floor/venv
uv pip install --python /app/tmp/probe-floor/venv/bin/python "protobuf==7.34.0" sqlmodel \
  googleapis-common-protos jinja2 grpcio pytest pytest-asyncio autopep8 inflection peewee pgvector

# 7.36.2 —— 当前 7.x（zenmpai 实际运行时版本）
uv venv /app/tmp/probe7/venv
uv pip install --python /app/tmp/probe7/venv/bin/python "protobuf==7.36.2" sqlmodel \
  googleapis-common-protos jinja2 grpcio pytest pytest-asyncio autopep8 inflection peewee pgvector
uv pip install --python /app/tmp/probe7/venv/bin/python --no-deps grpcio-tools==1.71.0
```

一条命令跑完整矩阵：`sh /app/tmp/probe-enum-map/matrix.sh`（默认用 `uv run --no-project --with protobuf==X` 的临时环境；`PROBE_VENVS=1` 走上面这些 venv，快一些但占 ~300MB）。

> **为什么不直接用容器的 env**：protobuf 是「每解释器一个版本」，容器自带 5.29.4 只够矩阵一行（那一行确实直接用了容器 `python3`）；其余版本必须各自隔离，而矩阵本身就要四行。隔离载体优先选 uv 缓存（不在仓库内），其次才是仓库里的 venv。

> **两个版本坑**：① `tmp/` 下这几个 gencode 由生成时用的 protoc 决定，而 protobuf 拒绝 runtime < gencode —— 所以 `run_checks.py`（读 `pb/`）只能在 **≥ 生成该 pb 的 protoc 版本**（当前 5.29.4）的解释器上跑；`example/tests` 走**进程内** probe，不受此限，四版本都能跑。② `protobuf==5.27.0` 在 PyPI 上已被 yank，且 5.27/5.28 连 committed 的 `pydantic_pb2.py`（gencode 5.29.0）都 import 不了 —— 所以下限是 **5.29.0**，不是 5.27。

## 跑法

**所有入口都需要 `googleapis-common-protos`**（`protobuf_pydantic_gen/__init__.py` → `generator`
→ `service_processor` 会 `import google.api`），而容器自带的 `python3` 没有它 —— 所以下面统一走
`uv run --no-project --with …` 的临时环境（跑完不往仓库里落任何东西）：

```bash
cd /app/tmp/probe-enum-map
DEPS="--with sqlmodel --with googleapis-common-protos --with jinja2 --with grpcio --with peewee --with inflection --with autopep8 --with pgvector --with zstandard --with requests --with pydantic-settings"

# 1) 生成（插件跑仓库源码；uv run 会把 env 的 bin 放进 PATH，所以 plugin.sh 里的 `python3` 就是该 env 的解释器）
for p in probe probe2 probe3; do
  PYTHONPATH=/app uv run --no-project --python 3.11 --with "protobuf==7.36.2" $DEPS --with grpcio-tools \
    python -m grpc_tools.protoc -I . -I /app \
      --plugin=protoc-gen-pydantic=$PWD/plugin.sh \
      --python_out=pb --pydantic_out=models --pydantic_opt=package_name=$p $p.proto
done

# 2) 运行时检查（改 --with protobuf==X 即可换版本；受 pb 的 gencode 约束，见下）
PYTHONPATH=/app uv run --no-project --python 3.11 --with "protobuf==7.36.2" $DEPS run_checks.py

# 3) 进程内生成（无 protoc）
PYTHONPATH=/app uv run --no-project --python 3.11 --with "protobuf==7.36.2" $DEPS inproc_gen.py
```

（`$DEPS` 只为可读性拆出，等价于把每个 `--with` 逐个写全。）

## 仓库测试套件 / 基线对照

```bash
# 全部四版本（默认 uv 临时环境，仓库零新增）
cd /app && sh tmp/probe-enum-map/matrix.sh

# 单版本示例（容器自带 python3 只有 5.29.4，且缺 googleapis-common-protos，
# 直接用它跑整套会 import 失败 —— 所以套件统一走 uv）
cd /app && PYTHONPATH=/app uv run --no-project --python 3.11 \
  --with "protobuf==7.36.2" --with sqlmodel --with pytest --with pytest-asyncio \
  --with googleapis-common-protos --with jinja2 --with grpcio --with autopep8 \
  --with inflection --with peewee --with pgvector --with zstandard --with requests \
  --with pydantic-settings \
  python -m pytest example/tests --ignore=example/tests/test_performance.py -q

# 未修复的基线（e90259a 的纯副本，不触碰工作区；把上面那条的目录换掉即可）
mkdir -p /tmp/ppgen-baseline-e90259a && git -C /app archive e90259a | tar -x -C /tmp/ppgen-baseline-e90259a
cd /tmp/ppgen-baseline-e90259a && PYTHONPATH=$PWD uv run --no-project --python 3.11 \
  --with "protobuf==7.36.2" --with sqlmodel --with pytest --with pytest-asyncio \
  --with googleapis-common-protos --with jinja2 --with grpcio --with autopep8 \
  --with inflection --with peewee --with pgvector --with zstandard --with requests \
  --with pydantic-settings \
  python -m pytest example/tests --ignore=example/tests/test_performance.py -q
```

`test_performance.py` 需要 `example.client`（仓库里不存在），两侧都排除。

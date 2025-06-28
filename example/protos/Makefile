# Makefile

# 定义变量
PROTOC = protoc
PYTHON = python3
TS_PROTO_PLUGIN = $(shell which protoc-gen-ts_proto)
PY_PYDANTIC_PLUGIN = $(shell which grpc_python_plugin)
# TS_PROTO_PLUGIN = $(shell which protoc-gen-ts_proto)

# 目标文件夹
PROTO_DIR = .
OUTPUT_DIR = ..
PB_OUTPUT_DIR = $(OUTPUT_DIR)/pb
MODELS_DIR= $(OUTPUT_DIR)/models
PY_CLIENT_OUTPUT_DIR = $(OUTPUT_DIR)/client
# 生成的文件
TS_OUTPUT_DIR="../pb"
# 文件列表
PY_PROTO_FILES = $(wildcard $(PROTO_DIR)/*.proto)
TS_PROTO_FILES = $(wildcard $(PROTO_DIR)/*.proto)

PY_ARGS = --python_out=$(PB_OUTPUT_DIR) \
          --pyi_out=$(PB_OUTPUT_DIR) \
		  --grpc_python_out=$(PB_OUTPUT_DIR) --pydantic_out=$(MODELS_DIR) --pydantic_opt=package_name=example --pydantic_opt=client_out=../ --pydantic_opt=models_dir=$(MODELS_DIR) \
		  --proto_path=$(PROTO_DIR) --proto_path=./
TS_ARGS = --plugin="protoc-gen-ts=$(TS_PROTO_PLUGIN)" \
           --ts_proto_opt=esModuleInterop=true --ts_proto_opt=paths=source_relative \
           --ts_proto_opt=snakeToCamel=false --ts_proto_opt=oneof=unions \
           --ts_proto_out=$(TS_OUTPUT_DIR)


common:
	@mkdir -p $(OUTPUT_DIR)

models:
	@mkdir -p $(MODELS_DIR)
.PHONY: make_dir generate python,common, ts, py_cli
clean:
	@rm -rf $(COMMON_PROTO_FILES)
# 生成所有代码
generate: make_dir py.print,common,desc


py: $(PY_PROTO_FILES) | common
	@mkdir -p $(MODELS_DIR)
	@mkdir -p $(PB_OUTPUT_DIR)
	touch $(PB_OUTPUT_DIR)/__init__.py
	echo "#!/usr/bin/env python" > $(PB_OUTPUT_DIR)/__init__.py
	touch $(MODELS_DIR)/__init__.py
	echo "#!/usr/bin/env python" > $(MODELS_DIR)/__init__.py
	python3 -m grpc_tools.protoc --proto_path=$(PROTO_DIR) --proto_path=./ $(PY_ARGS) $?
	sed -i '/from/!s/import \(.*\) as/from . import \1 as/g' $(PB_OUTPUT_DIR)/*pb2*.py
py_cli:
	@mkdir -p $(PY_CLIENT_OUTPUT_DIR)
	python3 -m grpc_tools.protoc \
		--proto_path=$(PROTO_DIR) --proto_path=./ \
		--client_out=$(PY_CLIENT_OUTPUT_DIR) --client_opt=package_name=example \
		--client_opt=models_dir=$(MODELS_DIR) \
		--client_opt=class_name=ExampleClient \
		$(PY_PROTO_FILES)
ts: $(TS_PROTO_FILES) | common
	@mkdir -p $(TS_OUTPUT_DIR)
	$(PROTOC) --proto_path=$(PROTO_DIR) --proto_path=./ $(TS_ARGS) $?

print:
	@echo $(PY_PROTO_FILES)
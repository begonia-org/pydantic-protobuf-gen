# Makefile

PROTOC = protoc
TS_PROTO_PLUGIN = $(shell which protoc-gen-ts_proto)
TS_CLIENT_PLUGIN = $(shell which protoc-gen-ts_client)

PROTO_DIR = .
OUTPUT_DIR = ..
PB_OUTPUT_DIR = $(OUTPUT_DIR)/pb
MODELS_DIR = $(OUTPUT_DIR)/models
TS_OUTPUT_DIR = "../web/src/proto"
TS_CLIENT_OUTPUT_DIR = "../web/src/services"

PY_PROTO_FILES = $(wildcard $(PROTO_DIR)/*.proto)
TS_PROTO_FILES = $(wildcard $(PROTO_DIR)/*.proto)

PY_ARGS = --python_out=$(PB_OUTPUT_DIR) \
		--pyi_out=$(PB_OUTPUT_DIR) \
		--grpc_python_out=$(PB_OUTPUT_DIR) --pydantic_out=$(MODELS_DIR) \
		--proto_path=$(PROTO_DIR) --proto_path=./
TS_ARGS = --plugin="protoc-gen-ts=$(TS_PROTO_PLUGIN)" \
		--ts_proto_opt=esModuleInterop=true --ts_proto_opt=paths=source_relative \
		--ts_proto_opt=snakeToCamel=false --ts_proto_opt=oneof=unions \
		--ts_proto_out=$(TS_OUTPUT_DIR) \
		--plugin="protoc-gen-axios=${TS_CLIENT_PLUGIN}" \
		--axios_out=$(TS_CLIENT_OUTPUT_DIR) \
		--axios_opt=ts_out=$(TS_OUTPUT_DIR) \
		--axios_opt=axios_out=$(TS_CLIENT_OUTPUT_DIR) \


common:
	@mkdir -p $(OUTPUT_DIR)

models:
	@mkdir -p $(MODELS_DIR)

.PHONY: common models clean py ts ts-cli print

clean:
	@rm -rf $(PB_OUTPUT_DIR) $(MODELS_DIR)

py: $(PY_PROTO_FILES) | common
	@mkdir -p $(MODELS_DIR)
	@mkdir -p $(PB_OUTPUT_DIR)
	touch $(PB_OUTPUT_DIR)/__init__.py
	echo "#!/usr/bin/env python" > $(PB_OUTPUT_DIR)/__init__.py
	touch $(MODELS_DIR)/__init__.py
	echo "#!/usr/bin/env python" > $(MODELS_DIR)/__init__.py
	python3 -m grpc_tools.protoc --proto_path=$(PROTO_DIR) --proto_path=./ $(PY_ARGS) $?
	sed -i '/from/!s/import \(.*\) as/from . import \1 as/g' $(PB_OUTPUT_DIR)/*pb2*.py

ts: $(TS_PROTO_FILES) | common
	@mkdir -p $(TS_OUTPUT_DIR)
	$(PROTOC) --proto_path=$(PROTO_DIR) --proto_path=./ $(TS_ARGS) $?

ts-cli:
	@mkdir -p $(TS_CLIENT_OUTPUT_DIR)
	$(PROTOC) --proto_path=$(PROTO_DIR) --proto_path=./ \
		--plugin="protoc-gen-axios=$(TS_CLIENT_PLUGIN)" \
		--axios_out=$(TS_CLIENT_OUTPUT_DIR) \
		--axios_opt=ts_out=$(TS_OUTPUT_DIR),axios_out=$(TS_CLIENT_OUTPUT_DIR) \
		$(TS_PROTO_FILES)

print:
	@echo $(PY_PROTO_FILES)
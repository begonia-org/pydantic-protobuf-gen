# Makefile — compile pydantic.proto
# Run from the repo root:  make -C protobuf_pydantic_gen
# Or from this directory:  make

PROTOC       = python3 -m grpc_tools.protoc
PROTO_FILE   = protobuf_pydantic_gen/pydantic.proto
PROTO_SOURCE = ../protos/$(PROTO_FILE)
# proto_path must be the shared proto root so the source path recorded in the
# generated _pb2.py still matches "protobuf_pydantic_gen/pydantic.proto"
PROTO_PATH   = protos
REPO_ROOT    = ..
OUT_DIR      = .

.PHONY: all clean

# Sync the canonical pydantic.proto into the package as a distributable data
# file so consumers compile against the always-current schema (not a stale
# vendored copy). Constraint scalars use proto3 `optional` presence; a consumer
# compiling against an older non-optional copy silently drops bounds like
# `ge: 0`. Kept in sync by `make` (and the pre-commit hook).
all: $(OUT_DIR)/pydantic_pb2.py $(OUT_DIR)/pydantic_pb2.pyi $(OUT_DIR)/pydantic_pb2_grpc.py $(OUT_DIR)/pydantic.proto

$(OUT_DIR)/pydantic.proto: $(PROTO_SOURCE)
	cp $(PROTO_SOURCE) $(OUT_DIR)/pydantic.proto
	@echo "Synced pydantic.proto into package for distribution"

$(OUT_DIR)/pydantic_pb2.py $(OUT_DIR)/pydantic_pb2.pyi $(OUT_DIR)/pydantic_pb2_grpc.py: $(PROTO_SOURCE)
	cd $(REPO_ROOT) && $(PROTOC) \
		--proto_path=$(PROTO_PATH) \
		--python_out=. \
		--pyi_out=. \
		--grpc_python_out=. \
		$(PROTO_FILE)
	@echo "Generated pb2 files in $(OUT_DIR)/"

clean:
	rm -f $(OUT_DIR)/pydantic_pb2.py \
	      $(OUT_DIR)/pydantic_pb2.pyi \
	      $(OUT_DIR)/pydantic_pb2_grpc.py

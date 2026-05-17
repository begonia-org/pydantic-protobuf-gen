# Makefile — compile pydantic.proto
# Run from the repo root:  make -C protobuf_pydantic_gen
# Or from this directory:  make

PROTOC       = python3 -m grpc_tools.protoc
PROTO_FILE   = protobuf_pydantic_gen/pydantic.proto
# proto_path must be the repo root so the source path recorded in the
# generated _pb2.py matches "protobuf_pydantic_gen/pydantic.proto"
PROTO_PATH   = ..
OUT_DIR      = .

.PHONY: all clean

all: $(OUT_DIR)/pydantic_pb2.py $(OUT_DIR)/pydantic_pb2.pyi $(OUT_DIR)/pydantic_pb2_grpc.py

$(OUT_DIR)/pydantic_pb2.py $(OUT_DIR)/pydantic_pb2.pyi $(OUT_DIR)/pydantic_pb2_grpc.py: pydantic.proto
	cd $(PROTO_PATH) && $(PROTOC) \
		--proto_path=. \
		--python_out=. \
		--pyi_out=. \
		--grpc_python_out=. \
		$(PROTO_FILE)
	@echo "Generated pb2 files in $(OUT_DIR)/"

clean:
	rm -f $(OUT_DIR)/pydantic_pb2.py \
	      $(OUT_DIR)/pydantic_pb2.pyi \
	      $(OUT_DIR)/pydantic_pb2_grpc.py

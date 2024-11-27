python3 -m grpc_tools.protoc --proto_path=.  --proto_path=./ --python_out=./ --pyi_out=./ --grpc_python_out=./ ./protobuf_pydantic_gen/*.proto

protoc --plugin=protoc-gen-custom=pydantic_protobuf_gen/main.py --custom_out=./models   -I ./protos protos/example.proto protos/options.proto
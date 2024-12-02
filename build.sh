python3 -m grpc_tools.protoc --proto_path=.  --proto_path=./ --python_out=./ --pyi_out=./ --grpc_python_out=./ ./protobuf_pydantic_gen/*.proto

protoc --plugin=protoc-gen-custom=protobuf_pydantic_gen/main.py --custom_out=./models -I ./  -I ./protos protos/example.proto
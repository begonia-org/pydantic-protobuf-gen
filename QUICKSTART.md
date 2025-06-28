# Quick Start Guide

Get up and running with protobuf-pydantic-gen, grpc-fastapi-gateway, and grpc-fastapi-client-gen in 5 minutes.

## Installation

```bash
pip install protobuf-pydantic-gen
```

## 1. Define Your Service (hello.proto)

```protobuf
syntax = "proto3";
import "google/api/annotations.proto";

package hello;

service Greeter {
  rpc SayHello (HelloRequest) returns (HelloReply) {
    option (google.api.http) = {
      post: "/v1/hello"
      body: "*"
    };
  }
}

message HelloRequest {
  string name = 1;
}

message HelloReply {
  string message = 1;
}
```

## 2. Generate Everything

```bash
# Generate models, server routes, and client
python3 -m grpc_tools.protoc \
    --proto_path=. \
    --python_out=./pb \
    --grpc_python_out=./pb \
    --pydantic_out=./models \
    --client_out=./client \
    --pydantic_opt=package_name=hello \
    --client_opt=package_name=hello \
    --client_opt=models_dir=./models \
    hello.proto
```

## 3. Create Server (server.py)

```python
from fastapi import FastAPI
from grpc_fastapi_gateway import create_gateway
from hello.models.hello_model import HelloRequest, HelloReply

app = FastAPI()

# Implement your service
async def say_hello(request: HelloRequest) -> HelloReply:
    return HelloReply(message=f"Hello, {request.name}!")

# Auto-generate routes from protobuf
gateway = create_gateway("./models/services.json", "hello.models")
gateway.implement("Greeter.SayHello", say_hello)
app.include_router(gateway.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, port=8000)
```

## 4. Use Generated Client (client_example.py)

```python
import asyncio
from client.hello_client import HelloClient
from hello.models.hello_model import HelloRequest

async def main():
    client = HelloClient(base_url="http://localhost:8000")
    
    request = HelloRequest(name="World")
    response = await client.greeter_say_hello(request)
    print(response.message)  # "Hello, World!"

asyncio.run(main())
```

## 5. Run and Test

```bash
# Terminal 1: Start server
python server.py

# Terminal 2: Test client
python client_example.py
```

That's it! You now have:
- ✅ Type-safe Pydantic models from protobuf
- ✅ Auto-generated FastAPI routes with validation  
- ✅ Async HTTP client with proper typing
- ✅ Full test suite for the client

## Next Steps

- Check out the [complete example](./example/) for advanced features
- Read the [client usage guide](./CLIENT_USAGE_GUIDE.md) for detailed client usage
- Explore streaming support (SSE and WebSockets)
- Add authentication and custom headers
- Run the generated test suite

## Generated File Structure

```
./
├── hello.proto              # Your service definition
├── server.py               # Your FastAPI server
├── client_example.py       # Client usage example
├── models/                 # Generated Pydantic models
│   ├── hello_model.py
│   └── services.json
├── pb/                     # Generated protobuf files  
│   ├── hello_pb2.py
│   └── hello_pb2_grpc.py
└── client/                 # Generated HTTP client
    ├── hello_client.py
    └── tests/
        ├── test_client.py
        ├── test_performance.py
        └── run_tests.py
```

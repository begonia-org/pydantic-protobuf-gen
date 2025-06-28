[English](README.md) | [中文](README.zh.md)

# protobuf-pydantic-gen

This tool converts Protocol Buffer description language into pydantic `BaseModel` classes and supports converting pydantic models back to protobuf messages. It also enables the transformation of protobuf description language into `sqlmodel` ORM models.

# grpc_fastapi_gateway

This tool converts Protocol Buffer description language into gRPC se        async for response in client.greeter_say_hello_bidi_stream(input_generator()):
            print(f"Bidi response: {response.message}")
    except Exception as e:
        logger.error(f"Streaming error: {e}")
        # Implement retry logic here
```

## API Documentation

### Client Generator Plugin Parameters

| Parameter | Type | Description | Default | Required |
|-----------|------|-------------|---------|----------|
| `package_name` | string | Python package name for model imports | - | ✅ |
| `models_dir` | string | Directory containing Pydantic models | - | ✅ |
| `class_name` | string | Generated client class name | `Client` | ❌ |
| `services_json` | string | Path to services.json file | `{models_dir}/services.json` | ❌ |
| `template_dir` | string | Custom Jinja2 template directory | Built-in | ❌ |
| `template_name` | string | Jinja2 template filename | `client.j2` | ❌ |

### Generated Client API

#### Constructor
```python
def __init__(
    self,
    base_url: str,           # Server base URL
    api_key: str = "",       # Optional API key for auth
    timeout: float = 30.0    # Request timeout in seconds
)
```

#### Helper Methods
```python
def _build_headers(self, extra_headers: Optional[Dict[str, Any]] = None) -> Dict[str, str]
def _build_websocket_uri(self, path: str) -> str
```

#### Service Methods
For each gRPC service method, the client generates an async method with this signature:

**Unary Calls:**
```python
async def {service}_{method}(
    self,
    request: {InputType},
    headers: Optional[Dict[str, Any]] = None
) -> {OutputType}
```

**Server Streaming:**
```python
async def {service}_{method}(
    self,
    request: {InputType},
    headers: Optional[Dict[str, Any]] = None
) -> AsyncGenerator[{OutputType}, None]
```

**Bidirectional Streaming:**
```python
async def {service}_{method}(
    self,
    input_stream: AsyncGenerator[{InputType}, None],
    headers: Optional[Dict[str, Any]] = None
) -> AsyncGenerator[{OutputType}, None]
```

### Transport Protocols

| gRPC Type | Protocol | Description |
|-----------|----------|-------------|
| Unary | HTTP/JSON | Standard REST API calls |
| Server Streaming | Server-Sent Events (SSE) | HTTP streaming with `text/event-stream` |
| Client Streaming | WebSocket | Bidirectional WebSocket connection |
| Bidirectional Streaming | WebSocket | Bidirectional WebSocket connection |

### Error Handling

The client handles these error types:

- `httpx.HTTPStatusError` - HTTP 4xx/5xx responses
- `httpx.TimeoutException` - Request timeouts  
- `websockets.exceptions.ConnectionClosed` - WebSocket disconnections
- `json.JSONDecodeError` - Invalid JSON responses
- `pydantic.ValidationError` - Model validation failures

### Test Suite Structure

Generated test files:

```
tests/
├── __init__.py
├── conftest.py              # pytest configuration
├── test_client.py           # Main test suite
├── test_performance.py      # Performance benchmarks
└── run_tests.py            # Test runner script
```

### Environment Variables

The client supports these environment variables:

- `GRPC_FASTAPI_BASE_URL` - Default base URL
- `GRPC_FASTAPI_API_KEY` - Default API key
- `GRPC_FASTAPI_TIMEOUT` - Default timeout (seconds)
- `GRPC_FASTAPI_LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR)

Example usage:
```python
import os
from example.client.example_client import ExampleClient

client = ExampleClient(
    base_url=os.getenv("GRPC_FASTAPI_BASE_URL", "http://localhost:8000"),
    api_key=os.getenv("GRPC_FASTAPI_API_KEY", ""),
    timeout=float(os.getenv("GRPC_FASTAPI_TIMEOUT", "30.0"))
)
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run the test suite
6. Submit a pull request

## License

This project is licensed under the Apache 2.0 License - see the [LICENSE](LICENSE) file for details. and supports transforming gRPC services into FastAPI routes. It automates `FastAPI` route generation based on `gRPC service` definitions, eliminating the need for additional code.

# grpc_fastapi_client_gen

This tool automatically generates type-safe gRPC FastAPI clients from protobuf service definitions. It creates async HTTP clients that support unary calls, server streaming, and bidirectional streaming through WebSockets.

## 🚀 Quick Links

- **[Quick Start Guide](QUICKSTART.md)** - Get running in 5 minutes
- **[Complete Client Usage Guide](CLIENT_USAGE_GUIDE.md)** - Comprehensive examples and advanced usage  
- **[Example Project](./example/)** - Full working example with server and client
- **[API Documentation](#api-documentation)** - Detailed API reference

## Features

- **protobuf-pydantic-gen**: 
  - Supports conversion of protobuf primitive types to Python primitive types  
  - Converts protobuf description language into pydantic `BaseModel` classes  
  - Transforms protobuf description language into `sqlmodel` ORM models  
  - Implements `to_protobuf` and `from_protobuf` methods for `BaseModel` classes to enable bidirectional conversion between pydantic models and protobuf messages  
  - Provides `pydantic BaseModel Field` parameter options for protobuf description files  

- **grpc_fastapi_gateway**:
  - Converts protobuf description language into gRPC services and transforms them into FastAPI routes  
  - Generates `FastAPI` routes based on `gRPC service` definitions without requiring extra code  

- **grpc_fastapi_client_gen**:
  - Generates type-safe async HTTP clients from protobuf service definitions
  - Supports all gRPC call types: unary, server streaming, client streaming, and bidirectional streaming
  - Uses HTTP/REST for unary calls, Server-Sent Events (SSE) for server streaming, and WebSockets for bidirectional streaming
  - Includes comprehensive error handling and connection management
  - Provides built-in authentication support (API key/Bearer token)
  - Generates test suites with integration, unit, and performance tests

## Installation

```shell
pip install protobuf-pydantic-gen
```
# Example Usage of protobuf-pydantic-gen
```protobuf
syntax = "proto3";

import "google/protobuf/descriptor.proto";
import "protobuf_pydantic_gen/pydantic.proto";
import "google/protobuf/timestamp.proto";
import "google/protobuf/any.proto";
import "constant.proto";
import "example2.proto";
package pydantic_example;
message Nested {

  string name = 1[(pydantic.field) = {description: "Name of the example",example: "'ohn Doe",alias: "full_name",default: "John Doe",max_length:128,primary_key:true}];
}
message Example {
    option (pydantic.database) = { 
        as_table: true
        table_name: "users",
        compound_index:{
            indexs:["name","age"],
            index_type:"UNIQUE",
            name:"uni_name_age"
        },
        compound_index:{
            indexs:["name"],
            index_type:"PRIMARY",
            name:"index_name"
        }
    };

  string name = 1[(pydantic.field) = {description: "Name of the example",alias: "full_name",default: "John Doe",max_length:128,primary_key:true}];
  optional int32 age = 2 [(pydantic.field) = {description: "Age of the example",alias: "years",default: "30"}];
  // Note: The default value is a string-formatted JSON array using single quotes
  repeated string emails = 3 [(pydantic.field) = {description: "Emails of the example",default:'["example@example.com","example2@example.com"]'}];
  repeated Example2 examples = 9 [(pydantic.field) = {description: "Nested message",sa_column_type:"JSON"}];
  map<string, google.protobuf.Any> entry = 4 [(pydantic.field) = {description: "Properties of the example",default:"{}"}];
Nested nested=8[(pydantic.field) = {description: "Nested message",sa_column_type:"JSON"}];
  google.protobuf.Timestamp created_at = 5 [(pydantic.field) = {description: "Creation date of the example",default: "datetime.datetime.now()",required: true}];
  ExampleType type = 6 [(pydantic.field) = {description: "Type of the example",default: "ExampleType.TYPE1",sa_column_type:"Enum[ExampleType]"}];
  float score = 7 [(pydantic.field) = {description: "Score of the example",default: "0.0",gt: 0.0,le: 100.0,field_type: "Integer"}];
}
```

**Compile the protobuf file to generate pydantic models and SQLModel ORM models:**
    
```shell
python3 -m grpc_tools.protoc --proto_path=./protos -I=./protos -I=./ --python_out=./pb --pyi_out=./pb --grpc_python_out=./pb --pydantic_out=./models "./protos/example.proto"
```

```python
#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File    :   example.py
@Time    :
@Desc    :
'''

import datetime
from .constant_model import ExampleType
from .example2_model import Example2
from google.protobuf import message as _message, message_factory
from protobuf_pydantic_gen.ext import PySQLModel, PydanticModel, model2protobuf, pool, protobuf2model
from pydantic import BaseModel, ConfigDict, Field as _Field
from sqlmodel import Column, Enum, Field, Integer, JSON, PrimaryKeyConstraint, SQLModel, UniqueConstraint
from typing import Any, Dict, List, Optional, Type

class Nested(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    name: Optional[str] = _Field(
        description="Name of the example",
        example="'ohn Doe",
        default="John Doe",
        alias="full_name",
        primary_key=True,
        max_length=128)

    def to_protobuf(self) -> _message.Message:
        _proto = pool.FindMessageTypeByName("pydantic_example.Nested")
        _cls: Type[_message.Message] = message_factory.GetMessageClass(_proto)
        return model2protobuf(self, _cls())

    @classmethod
    def from_protobuf(cls: Type[PydanticModel], src: _message.Message) -> PydanticModel:
        return protobuf2model(cls, src)

class Example(SQLModel, table=True):
    model_config = ConfigDict(protected_namespaces=())
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint(
            "name", "age", name='uni_name_age'), PrimaryKeyConstraint(
            "name", name='index_name'),)
    name: Optional[str] = Field(
        description="Name of the example",
        default="John Doe",
        alias="full_name",
        primary_key=True,
        max_length=128,
        sa_column_kwargs={
            'comment': 'Name of the example'})
    age: Optional[int] = Field(
        description="Age of the example",
        default=30,
        alias="years",
        sa_column_kwargs={
            'comment': 'Age of the example'})
    emails: Optional[List[str]] = Field(description="Emails of the example", default=[
                                        'example@example.com', 'example2@example.com'], sa_column_kwargs={'comment': 'Emails of the example'})
    examples: Optional[List[Example2]] = Field(
        description="Nested message", default=None, sa_column=Column(JSON, doc="Nested message"))
    entry: Optional[Dict[str, Any]] = Field(description="Properties of the example", default={
    }, sa_column=Column(JSON, doc="Properties of the example"))
    nested: Optional[Nested] = Field(description="Nested message", sa_column=Column(JSON, doc="Nested message"))
    created_at: datetime.datetime = Field(
        description="Creation date of the example",
        default=datetime.datetime.now(),
        sa_column_kwargs={
            'comment': 'Creation date of the example'})
    type: Optional[ExampleType] = Field(
        description="Type of the example",
        default=ExampleType.TYPE1,
        sa_column=Column(
            Enum[ExampleType],
            doc="Type of the example"))
    score: Optional[float] = Field(
        description="Score of the example",
        default=0.0,
        le=100.0,
        sa_type=Integer,
        sa_column_kwargs={
            'comment': 'Score of the example'})

    def to_protobuf(self) -> _message.Message:
        _proto = pool.FindMessageTypeByName("pydantic_example.Example")
        _cls: Type[_message.Message] = message_factory.GetMessageClass(_proto)
        return model2protobuf(self, _cls())

    @classmethod
    def from_protobuf(cls: Type[PySQLModel], src: _message.Message) -> PySQLModel:
        return protobuf2model(cls, src)
```

### grpc_fastapi_gateway Usage Example

 - Reference [example](./example/) directory for a complete example of using `grpc_fastapi_gateway` with `protobuf-pydantic-gen`.

 - Compile the protobuf file into a pydantic model and output services.json

```shell
cd example/protos && make py
```

OR
```shell
python3 -m grpc_tools.protoc  --plugin=protoc-gen-custom=protobuf_pydantic_gen/main.py --custom_out=./example/models --python_out=./example/pb --grpc_python_out=./example/pb  -I ./example  -I ./example/protos helloworld.proto
```

## grpc_fastapi_client_gen Usage

### Quick Start

1. **Generate Client Code from Protobuf**

```shell
# Using the client generator plugin
python3 -m grpc_tools.protoc \
    --proto_path=./protos \
    --proto_path=./ \
    --client_out=./client \
    --client_opt=package_name=example \
    --client_opt=models_dir=./models \
    --client_opt=class_name=MyAPIClient \
    ./protos/helloworld.proto
```

2. **Or using Makefile (recommended)**

```shell
cd example/protos && make py_cli
```

### Generated Client Features

The generated client provides:

- **Type-safe async methods** for all gRPC service methods
- **Automatic serialization/deserialization** using Pydantic models
- **Multiple transport protocols**:
  - HTTP/JSON for unary calls
  - Server-Sent Events (SSE) for server streaming
  - WebSockets for bidirectional streaming
- **Built-in authentication** (API key/Bearer token support)
- **Connection management** and error handling

### Using the Generated Client

```python
import asyncio
from example.client.example_client import ExampleClient
from example.models.helloworld_model import HelloRequest, HelloReply

async def main():
    # Initialize client
    client = ExampleClient(
        base_url="http://localhost:8000",
        api_key="your-api-key",  # Optional
        timeout=30.0
    )
    
    # Unary call
    request = HelloRequest(name="Alice", language="en")
    response = await client.greeter_say_hello(request)
    print(f"Response: {response.message}")
    
    # Server streaming
    async for response in client.greeter_say_hello_stream_reply(request):
        print(f"Stream response: {response.message}")
        if some_condition:  # Control stream termination
            break
    
    # Bidirectional streaming
    async def input_generator():
        for name in ["Bob", "Charlie", "David"]:
            yield HelloRequest(name=name, language="en")
            await asyncio.sleep(1)  # Simulate delay
    
    async for response in client.greeter_say_hello_bidi_stream(input_generator()):
        print(f"Bidi response: {response.message}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Client Configuration Options

```python
client = ExampleClient(
    base_url="https://api.example.com",  # Server base URL
    api_key="sk-...",                    # Optional API key for authentication
    timeout=60.0                         # Request timeout in seconds
)

# Custom headers for individual requests
custom_headers = {"X-Custom-Header": "value"}
response = await client.greeter_say_hello(request, headers=custom_headers)
```

### Plugin Parameters

When using `protoc-gen-client`, you can customize generation with these parameters:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `package_name` | Python package name for imports | Required |
| `models_dir` | Directory containing Pydantic models | Required |
| `class_name` | Generated client class name | `Client` |
| `services_json` | Path to services.json file | `{models_dir}/services.json` |
| `template_dir` | Custom Jinja2 template directory | Built-in templates |

Example with custom parameters:
```shell
python3 -m grpc_tools.protoc \
    --client_out=./output \
    --client_opt=package_name=myapp \
    --client_opt=models_dir=./myapp/models \
    --client_opt=class_name=MyCustomClient \
    --client_opt=services_json=./custom/services.json \
    ./protos/*.proto
```
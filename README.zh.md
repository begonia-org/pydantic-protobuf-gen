# protobuf-pydantic-gen

该工具可以将protobuf描述语言转换为pydantic `BaseModel`类，并且支持将pydantic model转换为protobuf message。它还支持将protobuf描述语言转换为`sqlmodel` ORM模型。

# grpc_fastapi_gateway

该工具可以将protobuf描述语言转换为grpc服务，并且支持将grpc服务转换为FastAPI路由。支持基于`gRPC service`的`FastAPI`路由生成，无需编写额外的代码。

# grpc_fastapi_client_gen

该工具从protobuf服务定义自动生成类型安全的gRPC FastAPI客户端。它创建支持一元调用、服务器流式传输和通过WebSocket双向流式传输的异步HTTP客户端。

## 🚀 快速链接

- **[快速开始指南](QUICKSTART.md)** - 5分钟快速上手
- **[完整客户端使用指南](CLIENT_USAGE_GUIDE.md)** - 全面的示例和高级用法  
- **[示例项目](./example/)** - 包含服务器和客户端的完整工作示例
- **[API文档](#api文档)** - 详细的API参考

## 特性

- **protobuf-pydantic-gen**:
  - 支持protobuf基本类型转换为python基本类型
  - 支持protobuf描述语言转换为pydantic `BaseModel`类
  - 支持protobuf描述语言转换为`sqlmodel` ORM模型
  - 为`BaseModel`类实现`to_protobuf` 和 `from_protobuf`方法，实现pydantic model 和 protobuf message 互相转换
  - 为protobuf 描述文件提供`pydantic BaseModel Field` 字段的参数选项

- **grpc_fastapi_gateway**:
  - 支持将protobuf描述语言转换为grpc服务，并且支持将grpc服务转换为FastAPI路由
  - 支持基于`gRPC service`的`FastAPI`路由生成，无需编写额外的代码

- **grpc_fastapi_client_gen**:
  - 从protobuf服务定义生成类型安全的异步HTTP客户端
  - 支持所有gRPC调用类型：一元、服务器流式、客户端流式和双向流式
  - 对一元调用使用HTTP/REST，对服务器流式使用服务器发送事件(SSE)，对双向流式使用WebSocket
  - 包含全面的错误处理和连接管理
  - 提供内置身份验证支持(API密钥/Bearer令牌)

## 安装

```shell
pip install protobuf-pydantic-gen
```
## 示例
### protobuf-pydantic-gen 使用示例
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
  // 注意这里的default值是一个字符串格式，使用单引号，表示一个json数组
  repeated string emails = 3 [(pydantic.field) = {description: "Emails of the example",default:'["example@example.com","example2@example.com"]'}];
  repeated Example2 examples = 9 [(pydantic.field) = {description: "Nested message",sa_column_type:"JSON"}];
  map<string, google.protobuf.Any> entry = 4 [(pydantic.field) = {description: "Properties of the example",default:"{}"}];
Nested nested=8[(pydantic.field) = {description: "Nested message",sa_column_type:"JSON"}];
  google.protobuf.Timestamp created_at = 5 [(pydantic.field) = {description: "Creation date of the example",default: "datetime.datetime.now()",required: true}];
  ExampleType type = 6 [(pydantic.field) = {description: "Type of the example",default: "ExampleType.TYPE1",sa_column_type:"Enum[ExampleType]"}];
  float score = 7 [(pydantic.field) = {description: "Score of the example",default: "0.0",gt: 0.0,le: 100.0,field_type: "Integer"}];
}


```

**编译protobuf文件为pydantic model和sqlmodel ORM模型**
    
```shell
python3 -m grpc_tools.protoc --proto_path=./protos -I=./protos -I=./ --python_out=./pb --pyi_out=./pb --grpc_python_out=./pb --pydantic_out=./models "./protos/example.proto"
```

```python

# !/usr/bin/env python
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

### grpc_fastapi_gateway 使用示例

 - 参考 [example](./example) 目录下的代码。

 - 编译protobuf文件为文件为pydantic model并输出`services.json`

```shell
cd example/protos && make py
```

OR
```shell
python3 -m grpc_tools.protoc  --plugin=protoc-gen-custom=protobuf_pydantic_gen/main.py --custom_out=./example/models --python_out=./example/pb --grpc_python_out=./example/pb  -I ./example  -I ./example/protos helloworld.proto
```

## grpc_fastapi_client_gen 用法

### 快速开始

1. **从Protobuf生成客户端代码**

```shell
# 使用客户端生成器插件
python3 -m grpc_tools.protoc \
    --proto_path=./protos \
    --proto_path=./ \
    --client_out=./client \
    --client_opt=package_name=example \
    --client_opt=models_dir=./models \
    --client_opt=class_name=MyAPIClient \
    ./protos/helloworld.proto
```

2. **或使用Makefile（推荐）**

```shell
cd example/protos && make py_cli
```

### 生成的客户端特性

生成的客户端提供：

- **类型安全的异步方法** 适用于所有gRPC服务方法
- **自动序列化/反序列化** 使用Pydantic模型
- **多种传输协议**：
  - HTTP/JSON用于一元调用
  - 服务器发送事件(SSE)用于服务器流式传输
  - WebSocket用于双向流式传输
- **内置身份验证** (API密钥/Bearer令牌支持)
- **连接管理** 和错误处理
- **全面的测试套件**

### 使用生成的客户端

```python
import asyncio
from example.client.example_client import ExampleClient
from example.models.helloworld_model import HelloRequest, HelloReply

async def main():
    # 初始化客户端
    client = ExampleClient(
        base_url="http://localhost:8000",
        api_key="your-api-key",  # 可选
        timeout=30.0
    )
    
    # 一元调用
    request = HelloRequest(name="Alice", language="en")
    response = await client.greeter_say_hello(request)
    print(f"响应: {response.message}")
    
    # 服务器流式传输
    async for response in client.greeter_say_hello_stream_reply(request):
        print(f"流式响应: {response.message}")
        if some_condition:  # 控制流的终止
            break
    
    # 双向流式传输
    async def input_generator():
        for name in ["Bob", "Charlie", "David"]:
            yield HelloRequest(name=name, language="en")
            await asyncio.sleep(1)  # 模拟延迟
    
    async for response in client.greeter_say_hello_bidi_stream(input_generator()):
        print(f"双向响应: {response.message}")

if __name__ == "__main__":
    asyncio.run(main())
```

### 客户端配置选项

```python
client = ExampleClient(
    base_url="https://api.example.com",  # 服务器基础URL
    api_key="sk-...",                    # 可选的API密钥用于身份验证
    timeout=60.0                         # 请求超时时间（秒）
)

# 为单个请求自定义头部
custom_headers = {"X-Custom-Header": "value"}
response = await client.greeter_say_hello(request, headers=custom_headers)
```

### 插件参数

使用`protoc-gen-client`时，可以使用这些参数自定义生成：

| 参数 | 描述 | 默认值 |
|------|------|---------|
| `package_name` | 导入的Python包名 | 必需 |
| `models_dir` | 包含Pydantic模型的目录 | 必需 |
| `class_name` | 生成的客户端类名 | `Client` |
| `services_json` | services.json文件路径 | `{models_dir}/services.json` |
| `template_dir` | 自定义Jinja2模板目录 | 内置模板 |

带自定义参数的示例：
```shell
python3 -m grpc_tools.protoc \
    --client_out=./output \
    --client_opt=package_name=myapp \
    --client_opt=models_dir=./myapp/models \
    --client_opt=class_name=MyCustomClient \
    --client_opt=services_json=./custom/services.json \
    ./protos/*.proto
```




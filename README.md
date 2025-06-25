[English](README.md) | [中文](README.zh.md)

# protobuf-pydantic-gen

This tool converts Protocol Buffer description language into pydantic `BaseModel` classes and supports converting pydantic models back to protobuf messages. It also enables the transformation of protobuf description language into `sqlmodel` ORM models.

# grpc_fastapi_gateway

This tool converts Protocol Buffer description language into gRPC services and supports transforming gRPC services into FastAPI routes. It automates `FastAPI` route generation based on `gRPC service` definitions, eliminating the need for additional code.

## Features

- Supports conversion of protobuf primitive types to Python primitive types  
- Converts protobuf description language into pydantic `BaseModel` classes  
- Transforms protobuf description language into `sqlmodel` ORM models  
- Implements `to_protobuf` and `from_protobuf` methods for `BaseModel` classes to enable bidirectional conversion between pydantic models and protobuf messages  
- Provides `pydantic BaseModel Field` parameter options for protobuf description files  
- Converts protobuf description language into gRPC services and transforms them into FastAPI routes  
- Generates `FastAPI` routes based on `gRPC service` definitions without requiring extra code  

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



[English](README.md)|[简体中文](README_ZH.md)  

# protobuf-pydantic-gen

A tool for converting between Pydantic models and Protobuf messages, enabling the generation of Pydantic `BaseModel` classes from `.proto` files.

## Features

- Supports conversion of Protobuf basic types to Python basic types.
- Converts Protobuf definition language to Pydantic `BaseModel` classes.
- Converts Protobuf definition language to `sqlmodel` ORM models.
- Implements `to_protobuf` and `from_protobuf` methods for `BaseModel` classes, facilitating bidirectional conversion between Pydantic models and Protobuf messages.
- Allows specifying `Pydantic BaseModel Field` parameters in Protobuf descriptor files.

## Installation

```shell
pip install protobuf-pydantic-gen
```
## Example
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
  repeated string emails = 3 [(pydantic.field) = {description: "Emails of the example",default:"[]"}];
  repeated Example2 examples = 9 [(pydantic.field) = {description: "Nested message",sa_column_type:"JSON"}];
  map<string, google.protobuf.Any> entry = 4 [(pydantic.field) = {description: "Properties of the example",default:"{}"}];
Nested nested=8[(pydantic.field) = {description: "Nested message",sa_column_type:"JSON"}];
  google.protobuf.Timestamp created_at = 5 [(pydantic.field) = {description: "Creation date of the example",default: "datetime.datetime.now()",required: true}];
  ExampleType type = 6 [(pydantic.field) = {description: "Type of the example",default: "ExampleType.TYPE1",sa_column_type:"Enum[ExampleType]"}];
  float score = 7 [(pydantic.field) = {description: "Score of the example",default: "0.0",gt: 0.0,le: 100.0,field_type: "Integer"}];
}

```
## Usage

```shell
python3 -m grpc_tools.protoc --proto_path=./protos -I=./protos -I=./ \
--python_out=./pb --pyi_out=./pb --grpc_python_out=./pb --pydantic_out=./models \
"./protos/example.proto"

```
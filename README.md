# protobuf-pydantic-gen

pydantic model 和 protobuf message 互相转换工具，实现`.proto`文件生成pydantic `BaseModel`类。

## 特性

- 支持protobuf基本类型转换为python基本类型

- 支持protobuf描述语言转换为pydantic `BaseModel`类

- 支持protobuf描述语言转换为`sqlmodel` ORM模型

- 为`BaseModel`类实现`to_protobuf` 和 `from_protobuf`方法，实现pydantic model 和 protobuf message 互相转换

- 为protobuf 描述文件提供`pydantic BaseModel` 字段的参数选项

## 安装

```shell
pip install protobuf-pydantic-gen
```

## 使用
    
```shell
python3 -m grpc_tools.protoc --proto_path=./protos -I=./protos -I=./ --python_out=./pb --pyi_out=./pb --grpc_python_out=./pb --pydantic_out=./models "./protos/example.proto"
```



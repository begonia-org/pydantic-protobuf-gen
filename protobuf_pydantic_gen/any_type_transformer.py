from typing import Any, Union, List, Dict
from google.protobuf import any_pb2
from google.protobuf import wrappers_pb2
from google.protobuf import struct_pb2
from pydantic import BaseModel


class AnyTransformer:
    @classmethod
    def any_type_to_protobuf(cls, value: Any) -> any_pb2.Any:
        """
        Convert a Python value to a protobuf Any message
        Args:
            value (Any): The Python value to convert
        Returns:
            any_pb2.Any: The protobuf Any message containing the value
        Raises:
            ValueError: If the value type is not supported
        """
        any_value = any_pb2.Any()
        wrapper = cls._convert_to_protobuf_message(value)
        any_value.Pack(wrapper)
        return any_value

    @classmethod
    def _convert_to_protobuf_message(
        cls,
        value: Any,
    ) -> Union[
        wrappers_pb2.StringValue,
        wrappers_pb2.Int64Value,
        wrappers_pb2.DoubleValue,
        wrappers_pb2.BoolValue,
        wrappers_pb2.BytesValue,
        struct_pb2.Struct,
        struct_pb2.ListValue,
        struct_pb2.Value,
    ]:
        """
        Convert a Python value to a protobuf message
        Args:
            value (Any): The Python value to convert
        Returns:
            Union[wrappers_pb2.StringValue, wrappers_pb2.Int64Value, wrappers_pb2.DoubleValue,
            wrappers_pb2.BoolValue, wrappers_pb2.BytesValue, struct_pb2.Struct,
            struct_pb2.ListValue, struct_pb2.Value]: The protobuf message containing the value
        Raises:
            ValueError: If the value type is not supported
        """
        if value is None:
            return struct_pb2.Value(null_value=struct_pb2.NullValue.NULL_VALUE)
        elif isinstance(value, bool):
            return wrappers_pb2.BoolValue(value=value)
        elif isinstance(value, int):
            return wrappers_pb2.Int64Value(value=value)
        elif isinstance(value, float):
            return wrappers_pb2.DoubleValue(value=value)
        elif isinstance(value, str):
            return wrappers_pb2.StringValue(value=value)
        elif isinstance(value, bytes):
            return wrappers_pb2.BytesValue(value=value)
        elif isinstance(value, dict):
            return cls._dict_to_struct(value)
        elif isinstance(value, BaseModel):
            return cls._pydantic_model_to_protobuf(value)
        elif isinstance(value, (list, tuple)):
            return cls._list_to_listvalue(value)
        else:
            return wrappers_pb2.StringValue(value=str(value))

    @classmethod
    def _pydantic_model_to_protobuf(cls, model: BaseModel) -> any_pb2.Any:
        """
        Convert a Pydantic model to a protobuf Any message
        """
        data = model.model_dump(mode="json")
        struct = cls._dict_to_struct(data)
        any_value = any_pb2.Any()
        any_value.Pack(struct)
        return any_value

    @classmethod
    def _dict_to_struct(cls, data: Dict[str, Any]) -> struct_pb2.Struct:
        """
        Convert a Python dictionary to protobuf Struct
        Args:
            data (Dict[str, Any]): Python Dictionary
        Returns:
            struct_pb2.Struct: protobuf Struct message
        """
        struct = struct_pb2.Struct()
        for key, value in data.items():
            struct.fields[key].CopyFrom(cls._python_to_struct_value(value))
        return struct

    @classmethod
    def _list_to_listvalue(cls, data: List[Any]) -> struct_pb2.ListValue:
        """
        Convert a Python list to protobuf ListValue
        Args:
            data (List[Any]): Python List
        Returns:
            struct_pb2.ListValue: protobuf ListValue message
        """
        list_value = struct_pb2.ListValue()
        for item in data:
            list_value.values.add().CopyFrom(cls._python_to_struct_value(item))
        return list_value

    @classmethod
    def _python_to_struct_value(cls, value: Any) -> struct_pb2.Value:
        """
        Convert a Python value to a protobuf Value
        Args:
            value (Any): The Python value to convert
        Returns:
            struct_pb2.Value: The protobuf Value message containing the value
        Raises:
            ValueError: If the value type is not supported
        """
        if value is None:
            return struct_pb2.Value(null_value=struct_pb2.NullValue.NULL_VALUE)
        elif isinstance(value, bool):
            return struct_pb2.Value(bool_value=value)
        elif isinstance(value, int):
            return struct_pb2.Value(number_value=float(value))
        elif isinstance(value, float):
            return struct_pb2.Value(number_value=value)
        elif isinstance(value, str):
            return struct_pb2.Value(string_value=value)
        elif isinstance(value, dict):
            struct_val = struct_pb2.Struct()
            for k, v in value.items():
                struct_val.fields[k].CopyFrom(cls._python_to_struct_value(v))
            return struct_pb2.Value(struct_value=struct_val)
        elif isinstance(value, (list, tuple)):
            list_val = struct_pb2.ListValue()
            for item in value:
                list_val.values.add().CopyFrom(cls._python_to_struct_value(item))
            return struct_pb2.Value(list_value=list_val)
        else:
            # 其他类型转换为字符串
            return struct_pb2.Value(string_value=str(value))

    @classmethod
    def protobuf_any_to_python(cls, any_proto: any_pb2.Any) -> Any:
        """
        Convert a protobuf Any message to a Python value
        Args:
            any_proto (any_pb2.Any): The protobuf Any message to convert
        Returns:
            Any: The Python value contained in the Any message
        Raises:
            ValueError: If the type of the Any message is not supported
        """
        if any_proto.Is(wrappers_pb2.StringValue.DESCRIPTOR):
            string_value = wrappers_pb2.StringValue()
            any_proto.Unpack(string_value)
            return string_value.value
        elif any_proto.Is(wrappers_pb2.Int64Value.DESCRIPTOR):
            int_value = wrappers_pb2.Int64Value()
            any_proto.Unpack(int_value)
            return int_value.value
        elif any_proto.Is(wrappers_pb2.DoubleValue.DESCRIPTOR):
            double_value = wrappers_pb2.DoubleValue()
            any_proto.Unpack(double_value)
            return double_value.value
        elif any_proto.Is(wrappers_pb2.BoolValue.DESCRIPTOR):
            bool_value = wrappers_pb2.BoolValue()
            any_proto.Unpack(bool_value)
            return bool_value.value
        elif any_proto.Is(wrappers_pb2.BytesValue.DESCRIPTOR):
            bytes_value = wrappers_pb2.BytesValue()
            any_proto.Unpack(bytes_value)
            return bytes_value.value
        elif any_proto.Is(struct_pb2.Struct.DESCRIPTOR):
            struct_value = struct_pb2.Struct()
            any_proto.Unpack(struct_value)
            return cls._struct_to_dict(struct_value)
        elif any_proto.Is(struct_pb2.ListValue.DESCRIPTOR):
            list_value = struct_pb2.ListValue()
            any_proto.Unpack(list_value)
            return cls._listvalue_to_list(list_value)
        elif any_proto.Is(struct_pb2.Value.DESCRIPTOR):
            value = struct_pb2.Value()
            any_proto.Unpack(value)
            return cls._struct_value_to_python(value)
        else:
            raise ValueError(f"Unsupported type: {any_proto.type_url}")

    @classmethod
    def _struct_to_dict(cls, struct: struct_pb2.Struct) -> Dict[str, Any]:
        """
        Convert a protobuf Struct to a Python dictionary
        Args:
            struct (struct_pb2.Struct): The protobuf Struct to convert
        Returns:
            Dict[str, Any]: The Python dictionary representation of the Struct
        """
        result = {}
        for key, value in struct.fields.items():
            result[key] = cls._struct_value_to_python(value)
        return result

    @classmethod
    def _listvalue_to_list(cls, list_value: struct_pb2.ListValue) -> List[Any]:
        """
        Convert a protobuf ListValue to a Python list
        Args:
            list_value (struct_pb2.ListValue): The protobuf ListValue to convert
        Returns:
            List[Any]: The Python list representation of the ListValue
        """
        return [cls._struct_value_to_python(value) for value in list_value.values]

    @classmethod
    def _struct_value_to_python(cls, value: struct_pb2.Value) -> Any:
        """
        Convert a protobuf Value to a Python value
        Args:
            value (struct_pb2.Value): The protobuf Value to convert
        Returns:
            Any: The Python value contained in the Value message
        Raises:
            ValueError: If the type of the Value message is not supported
        """
        kind = value.WhichOneof("kind")
        if kind == "null_value":
            return None
        elif kind == "number_value":
            if value.number_value.is_integer():
                return int(value.number_value)
            return value.number_value
        elif kind == "string_value":
            return value.string_value
        elif kind == "bool_value":
            return value.bool_value
        elif kind == "struct_value":
            return cls._struct_to_dict(value.struct_value)
        elif kind == "list_value":
            return cls._listvalue_to_list(value.list_value)
        else:
            return None


if __name__ == "__main__":
    from models.example_model import Example, Nested
    from pb.example_pb2 import Example as ExampleProto  # noqa: F401
    from pb.example_pb2 import Nested as NestedProto  # noqa: F401
    from pb.constant_pb2 import ExampleType  # noqa: F401

    e = Example(
        name="John Doe",
        age=30,
        emails=["example@example.com"],
        entry={"key1": "value1", "key2": 42},
        nested=Nested(name="Nested Example"),
    )
    print(Example.from_protobuf(e.to_protobuf()).entry)

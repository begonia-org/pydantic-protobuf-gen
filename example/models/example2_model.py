# !/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@File    :   example2_model.py
@Time    :   2025-06-29 08:39:04
@Desc    :   Generated Pydantic models from protobuf definitions
"""

from .constant_model import ExampleType
from google.protobuf import message as _message, message_factory
from protobuf_pydantic_gen.ext import model2protobuf, pool, protobuf2model
from pydantic import BaseModel, ConfigDict, Field as _Field
from typing import Optional, Type


class Example2(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    type: Optional[ExampleType] = _Field(
        description="Type of the example", default=ExampleType.TYPE1
    )

    def to_protobuf(self) -> _message.Message:
        """Convert Pydantic model to protobuf message"""
        _proto = pool.FindMessageTypeByName("pydantic_example.Example2")
        _cls: Type[_message.Message] = message_factory.GetMessageClass(_proto)
        return model2protobuf(self, _cls())

    @classmethod
    def from_protobuf(cls, src: _message.Message) -> "Example2":
        """Convert protobuf message to Pydantic model"""
        return protobuf2model(cls, src)

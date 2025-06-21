
# !/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File    :   helloworld.py
@Time    :
@Desc    :
'''


from google.protobuf import message as _message, message_factory

from protobuf_pydantic_gen.ext import PydanticModel, model2protobuf, pool, protobuf2model

from pydantic import BaseModel, ConfigDict, Field as _Field

from typing import Optional, Type


class HelloRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    name: str = _Field(description="The name of the person to greet", example="'John Doe'", default='John Doe')
    language: Optional[str] = _Field(description="The language of the greeting", example="'en'", default="'en'")

    def to_protobuf(self) -> _message.Message:
        _proto = pool.FindMessageTypeByName("helloworld.HelloRequest")
        _cls: Type[_message.Message] = message_factory.GetMessageClass(_proto)
        return model2protobuf(self, _cls())

    @classmethod
    def from_protobuf(cls: Type[PydanticModel], src: _message.Message) -> PydanticModel:
        return protobuf2model(cls, src)


class HelloReply(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    message: str = _Field(description="The greeting message", example="'Hello, John Doe!'", default='Hello, John Doe!')
    language: Optional[str] = _Field(description="The language of the greeting", example="'en'", default="'en'")

    def to_protobuf(self) -> _message.Message:
        _proto = pool.FindMessageTypeByName("helloworld.HelloReply")
        _cls: Type[_message.Message] = message_factory.GetMessageClass(_proto)
        return model2protobuf(self, _cls())

    @classmethod
    def from_protobuf(cls: Type[PydanticModel], src: _message.Message) -> PydanticModel:
        return protobuf2model(cls, src)

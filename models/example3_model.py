
# !/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File    :   example3.py
@Time    :
@Desc    :
'''


from google.protobuf import message as _message, message_factory

from protobuf_pydantic_gen.ext import PydanticModel, model2protobuf, pool, protobuf2model

from pydantic import BaseModel, ConfigDict, Field as _Field

from typing import Optional, Type


class Example3(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    name: Optional[str] = _Field()

    def to_protobuf(self) -> _message.Message:
        _proto = pool.FindMessageTypeByName("pydantic_example.Example3")
        _cls: Type[_message.Message] = message_factory.GetMessageClass(_proto)
        return model2protobuf(self, _cls())

    @classmethod
    def from_protobuf(cls: Type[PydanticModel], src: _message.Message) -> PydanticModel:
        return protobuf2model(cls, src)

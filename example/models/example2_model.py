
#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File    :   example2.py
@Time    :
@Desc    :
'''


from pydantic_protobuf.ext import model2protobuf, PydanticModel, protobuf2model, pool

from .constant_model import ExampleType

from google.protobuf import message_factory

from google.protobuf import message as _message

from pydantic import Field as _Field

from pydantic import BaseModel

from typing import Optional, Type


class Example2(BaseModel):

    type: Optional[ExampleType] = _Field(description="Type of the example", default=ExampleType.TYPE1)

    def to_protobuf(self) -> _message.Message:
        _proto = pool.FindMessageTypeByName("pydantic_example.Example2")
        _cls: Type[_message.Message] = message_factory.GetMessageClass(_proto)
        return model2protobuf(self, _cls())

    @classmethod
    def from_protobuf(cls: Type[PydanticModel], src: _message.Message) -> PydanticModel:
        return cls(**protobuf2model(cls, src))

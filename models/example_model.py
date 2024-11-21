
#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File    :   example.py
@Time    :
@Desc    :
'''


from typing import Optional, List, Any, Type, Dict

from protobuf_pydantic_gen.ext import model2protobuf, PydanticModel, pool, protobuf2model, PySQLModel

from sqlmodel import Enum, Integer, UniqueConstraint, JSON, Column, PrimaryKeyConstraint

from .constant_model import ExampleType

from pydantic import BaseModel, ConfigDict

from google.protobuf import message as _message

from sqlmodel import SQLModel, Field

from .example2_model import Example2

import datetime

from google.protobuf import message_factory

from pydantic import Field as _Field


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
        max_length=128)
    age: Optional[int] = Field(description="Age of the example", default=30, alias="years")
    emails: Optional[List[str]] = Field(description="Emails of the example", default=[])
    examples: Optional[List[Example2]] = Field(description="Nested message", default=[], sa_column=Column(JSON))
    entry: Optional[Dict[str, Any]] = Field(description="Properties of the example", default={}, sa_column=Column(JSON))
    nested: Optional[Nested] = Field(description="Nested message", sa_column=Column(JSON))
    created_at: datetime.datetime = Field(
        description="Creation date of the example",
        default=datetime.datetime.now(),
        schema_extra={
            'required': True})
    type: Optional[ExampleType] = Field(
        description="Type of the example",
        default=ExampleType.TYPE1,
        sa_column=Column(
            Enum[ExampleType]))
    score: Optional[float] = Field(description="Score of the example", default=0.0, le=100.0, sa_type=Integer)

    def to_protobuf(self) -> _message.Message:
        _proto = pool.FindMessageTypeByName("pydantic_example.Example")
        _cls: Type[_message.Message] = message_factory.GetMessageClass(_proto)
        return model2protobuf(self, _cls())

    @classmethod
    def from_protobuf(cls: Type[PySQLModel], src: _message.Message) -> PySQLModel:
        return protobuf2model(cls, src)

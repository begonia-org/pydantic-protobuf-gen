
#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File    :   example.py
@Time    :
@Desc    :
'''


from google.protobuf import message_factory

from pydantic_protobuf.ext import PySQLModel, model2protobuf, protobuf2model, pool, PydanticModel

from sqlmodel import Enum, Integer, Column, UniqueConstraint, PrimaryKeyConstraint, JSON

from pydantic import BaseModel

import datetime

from typing import Type, Any, List, Dict, Optional

from .constant_model import ExampleType

from sqlmodel import SQLModel, Field

from google.protobuf import message as _message

from typing import Type, Optional


class Nested(BaseModel):

    name: Optional[str] = Field(
        description="Name of the example",
        example="'ohn Doe",
        default="John Doe",
        alias="full_name",
        primary_key=True,
        max_length=128)

    def to_protobuf(self) -> _message.Message:
        _proto = pool.FindMessageTypeByName("example.Nested")
        _cls: Type[_message.Message] = message_factory.GetMessageClass(_proto)
        return model2protobuf(self, _cls())

    @classmethod
    def from_protobuf(cls: Type[PydanticModel], src: _message.Message) -> PydanticModel:
        return protobuf2model(src, cls)


class Example(SQLModel, table=True):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint(
            "name", "age", name='uni_name_age'), PrimaryKeyConstraint(
            "name", name='index_name'),)
    name: Optional[str] = Field(
        description="Name of the example",
        example="'ohn Doe",
        default="John Doe",
        alias="full_name",
        primary_key=True,
        max_length=128)
    age: Optional[int] = Field(description="Age of the example", example=30, default=30, alias="years")
    emails: Optional[List[str]] = Field(description="Emails of the example")
    entry: Optional[Dict[str, Any]] = Field(description="Properties of the example", sa_column=Column(JSON))
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
        _proto = pool.FindMessageTypeByName("example.Example")
        _cls: Type[_message.Message] = message_factory.GetMessageClass(_proto)
        return model2protobuf(self, _cls())

    @classmethod
    def from_protobuf(cls: Type[PySQLModel], src: _message.Message) -> PySQLModel:
        return protobuf2model(src, cls)

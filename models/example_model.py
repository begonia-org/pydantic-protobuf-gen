
# !/usr/bin/env python
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
    emails: Optional[List[str]] = Field(description="Emails of the example", default=[],
                                        sa_column_kwargs={'comment': 'Emails of the example'})
    examples: Optional[List[Example2]] = Field(description="Nested message", default=[], sa_column=Column(
        JSON), sa_column_kwargs={'comment': 'Nested message'})
    entry: Optional[Dict[str, Any]] = Field(description="Properties of the example", default={}, sa_column=Column(
        JSON), sa_column_kwargs={'comment': 'Properties of the example'})
    nested: Optional[Nested] = Field(
        description="Nested message",
        sa_column=Column(JSON),
        sa_column_kwargs={
            'comment': 'Nested message'})
    created_at: datetime.datetime = Field(
        description="Creation date of the example", default=datetime.datetime.now(), schema_extra={
            'required': True}, sa_column_kwargs={
            'comment': 'Creation date of the example'})
    type: Optional[ExampleType] = Field(
        description="Type of the example",
        default=ExampleType.TYPE1,
        sa_column=Column(
            Enum[ExampleType]),
        sa_column_kwargs={
            'comment': 'Type of the example'})
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

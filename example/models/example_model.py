# !/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@File    :   example_model.py
@Time    :   2025-07-01 16:17:31
@Desc    :   Generated Pydantic models from protobuf definitions
"""

import datetime
from .constant_model import ExampleType
from .example2_model import Example2
from google.protobuf import message as _message, message_factory
from protobuf_pydantic_gen.ext import model2protobuf, pool, protobuf2model
from pydantic import BaseModel, ConfigDict, Field as _Field
from sqlmodel import (
    Column,
    Enum,
    Field,
    Integer,
    JSON,
    PrimaryKeyConstraint,
    SQLModel,
    UniqueConstraint,
)
from typing import Any, Dict, List, Optional, Type


class Nested(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    name: Optional[str] = _Field(
        description="Name of the example",
        default="John Doe",
        alias="full_name",
        max_length=128,
        json_schema_extra={"example": "ohn Doe"},
    )

    def to_protobuf(self) -> _message.Message:
        """Convert Pydantic model to protobuf message"""
        _proto = pool.FindMessageTypeByName("pydantic_example.Nested")
        _cls: Type[_message.Message] = message_factory.GetMessageClass(_proto)
        return model2protobuf(self, _cls())

    @classmethod
    def from_protobuf(cls, src: _message.Message) -> "Nested":
        """Convert protobuf message to Pydantic model"""
        return protobuf2model(cls, src)


class Example(SQLModel, table=True):
    model_config = ConfigDict(protected_namespaces=())
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("name", "age", name="uni_name_age"),
        PrimaryKeyConstraint("name", name="index_name"),
    )
    name: Optional[str] = Field(
        description="Name of the example",
        default="John Doe",
        alias="full_name",
        primary_key=True,
        max_length=128,
        sa_column_kwargs={"comment": "Name of the example"},
    )
    age: Optional[int] = Field(
        description="Age of the example",
        default=30,
        alias="years",
        sa_column_kwargs={"comment": "Age of the example"},
    )
    emails: Optional[List[str]] = Field(
        description="Emails of the example",
        default=["example@example.com", "example2@example.com"],
        sa_column=Column(JSON, doc="Emails of the example"),
    )
    examples: Optional[List[Example2]] = Field(
        description="Nested message",
        default=None,
        sa_column=Column(JSON, doc="Nested message"),
    )
    entry: Optional[Dict[str, Any]] = Field(
        description="Properties of the example",
        default={},
        sa_column=Column(JSON, doc="Properties of the example"),
    )
    nested: Optional[Nested] = Field(
        description="Nested message",
        default=None,
        sa_column=Column(JSON, doc="Nested message"),
    )
    created_at: datetime.datetime = Field(
        description="Creation date of the example",
        default=datetime.datetime.now(),
        sa_column_kwargs={"comment": "Creation date of the example"},
    )
    type: Optional[ExampleType] = Field(
        description="Type of the example",
        default=ExampleType.TYPE1,
        sa_column=Column(Enum[ExampleType], doc="Type of the example"),
    )
    score: Optional[float] = Field(
        description="Score of the example",
        default=0.0,
        le=100.0,
        sa_column=Column(Integer, doc="Score of the example"),
    )
    metadatas: Optional[Dict[str, Any]] = Field(
        description="Metadata attributes and their values for the document",
        default=None,
        sa_column=Column(
            JSON, doc="Metadata attributes and their values for the document"
        ),
    )

    def to_protobuf(self) -> _message.Message:
        """Convert Pydantic model to protobuf message"""
        _proto = pool.FindMessageTypeByName("pydantic_example.Example")
        _cls: Type[_message.Message] = message_factory.GetMessageClass(_proto)
        return model2protobuf(self, _cls())

    @classmethod
    def from_protobuf(cls, src: _message.Message) -> "Example":
        """Convert protobuf message to Pydantic model"""
        return protobuf2model(cls, src)

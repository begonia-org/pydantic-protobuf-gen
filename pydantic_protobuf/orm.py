#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File    :   orm.py
@Time    :   2024/06/30 13:51:33
@Desc    :   
'''


from peewee import (
    BigIntegerField, BooleanField, CharField,
    CompositeKey, IntegerField, TextField, FloatField, DateTimeField,
    Field, Model, Metadata
)
from sqlmodel import Field, SQLModel,JSON,Column,Integer,Text


class PydanticModel:
    pass
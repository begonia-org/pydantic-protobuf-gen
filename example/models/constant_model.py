
#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File    :   constant.py
@Time    :   
@Desc    :   
'''


from sqlmodel import Field
from pydantic_protobuf.ext import model2protobuf, protobuf2model, pool, PydanticModel, PySQLModel
from google.protobuf import message_factory
from typing import Type
from google.protobuf import message as _message
from pydantic import BaseModel


from enum import Enum as _Enum


class ExampleType(_Enum):
    UNKNOWN = 0
    TYPE1 = 1
    TYPE2 = 2
    TYPE3 = 3

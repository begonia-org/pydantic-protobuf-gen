
#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File    :   constant.py
@Time    :   
@Desc    :   
'''



from sqlmodel import SQLModel, Field
from pydantic_protobuf.ext import model2protobuf,pool
from google.protobuf import message_factory
from typing import Type
from google.protobuf import message as _message

from enum import Enum as _Enum



class ExampleType(_Enum):
    UNKNOWN = 0
    TYPE1 = 1
    TYPE2 = 2
    TYPE3 = 3





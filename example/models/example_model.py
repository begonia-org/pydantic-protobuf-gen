
#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File    :   example.py
@Time    :   
@Desc    :   
'''



from pydantic import BaseModel, Field

from .example_model import ExampleType

from enum import Enum

from typing import Any, List, Dict, Optional

import datetime



class ExampleType(Enum):
    UNKNOWN = 0
    TYPE1 = 1
    TYPE2 = 2
    TYPE3 = 3




class Example(BaseModel):
    name: Optional[str] = Field(description="Name of the example",example="'ohn Doe",default="John Doe",alias="full_name")
    age: Optional[int] = Field(description="Age of the example",example=30,default=30,alias="years")
    emails: Optional[List[str]] = Field(description="Emails of the example")
    entry: Optional[Dict[str,Any]] = Field(description="Properties of the example")
    created_at: datetime.datetime = Field(description="Creation date of the example",default=datetime.datetime.now(),required=True)
    type: Optional[ExampleType] = Field(description="Type of the example",default=ExampleType.TYPE1)



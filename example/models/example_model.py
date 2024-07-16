
#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File    :   example.py
@Time    :   
@Desc    :   
'''



from sqlmodel import SQLModel, Field



from typing import List, Optional, Dict, Any

from .constant_model import ExampleType

from sqlmodel import JSON, Integer, PrimaryKeyConstraint, Enum, Column, UniqueConstraint

import datetime

from enum import Enum

from pydantic import BaseModel

from typing import Optional





class Nested(BaseModel):
    
    
    name: Optional[str] = Field(description="Name of the example",example="'ohn Doe",default="John Doe",alias="full_name",primary_key=True,max_length=128)

class Example(SQLModel ,table=True):
    __tablename__="users"
    __table_args__=(UniqueConstraint("name","age",name='uni_name_age'),PrimaryKeyConstraint("name",name='index_name'),)
    name: Optional[str] = Field(description="Name of the example",example="'ohn Doe",default="John Doe",alias="full_name",primary_key=True,max_length=128)
    age: Optional[int] = Field(description="Age of the example",example=30,default=30,alias="years")
    emails: Optional[List[str]] = Field(description="Emails of the example")
    entry: Optional[Dict[str,Any]] = Field(description="Properties of the example",sa_column=Column(JSON))
    nested: Optional[Nested] = Field(description="Nested message",sa_column=Column(JSON))
    created_at: datetime.datetime = Field(description="Creation date of the example",default=datetime.datetime.now(),schema_extra={'required': True})
    type: Optional[ExampleType] = Field(description="Type of the example",default=ExampleType.TYPE1,sa_column=Column(Enum[ExampleType]))
    score: Optional[float] = Field(description="Score of the example",default=0.0,le=100.0,sa_type=Integer)


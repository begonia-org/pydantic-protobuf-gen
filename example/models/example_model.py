
#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File    :   example.py
@Time    :   
@Desc    :   
'''



from pydantic import BaseModel, Field

import datetime

from typing import List, Optional, Dict




class Example(BaseModel):
    name: Optional[str] = Field(description='Name of the example',example='John Doe',default='John Doe',alias='full_name')
    age: Optional[int] = Field(description='Age of the example',example=30,default=30,alias='years')
    emails: Optional[List[str]] = Field(description='Emails of the example')
    entry: Optional[List[Dict[str,str]]] = Field(description='Properties of the example')
    created_at: datetime.datetime = Field(description='Creation date of the example',default=datetime.datetime.now(),required=True)


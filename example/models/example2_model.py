
#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File    :   example2.py
@Time    :   
@Desc    :   
'''



from pydantic import BaseModel, Field

from enum import Enum

from .example_model import ExampleType

from typing import Optional





class Example2(BaseModel):
    type: Optional[ExampleType] = Field(description="Type of the example",default=ExampleType.TYPE1)




#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File    :   constant.py
@Time    :   
@Desc    :   
'''



from sqlmodel import SQLModel, Field

from enum import Enum as _Enum



class ExampleType(_Enum):
    UNKNOWN = 0
    TYPE1 = 1
    TYPE2 = 2
    TYPE3 = 3





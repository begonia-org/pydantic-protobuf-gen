#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File    :   test.py
@Time    :   2024/07/25 16:37:06
@Desc    :   
'''


import os
import sys
import grpc
from typing import _UnionGenericAlias
from example.models.example_model import Example
from typing import List
from typing import get_args, get_origin, Optional

if __name__=="__main__":
    for name,typ in Example.model_fields.items():
        if get_args(typ.annotation):
            print(name,get_args(typ.annotation)[0].__module__)
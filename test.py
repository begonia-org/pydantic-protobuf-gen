from typing import List, Optional, Union, get_args, get_origin
from example.models.constant_model import ExampleType
class MyClass:
    my_list: Optional[List[int]]

# 获取类属性的类型注释
annotations = MyClass.__annotations__
list_type = annotations.get('my_list')

# 处理 Optional 类型
if get_origin(list_type) is Union:
    # 提取 Optional 中的实际类型（去掉 None 类型）
    actual_type = next(arg for arg in get_args(list_type) if arg is not type(None))
else:
    actual_type = list_type

# 提取 List 的元素类型
if get_origin(actual_type) is list:
    element_type = get_args(actual_type)[0]
else:
    element_type = None

print(f'The element type of my_list is {element_type}')
ExampleType(1)
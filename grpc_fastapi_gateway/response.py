from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T", bound=BaseModel)


class BaseHttpResponse(BaseModel, Generic[T]):
    code: int = Field(0, description="Status code, 0 for success, non-zero for error")
    message: str = "success"
    data: T = Field(None, description="Response data, can be any type")
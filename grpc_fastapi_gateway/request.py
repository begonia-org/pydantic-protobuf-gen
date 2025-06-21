from typing import TypeVar

from pydantic import BaseModel


InputT = TypeVar("InputT", bound=BaseModel)



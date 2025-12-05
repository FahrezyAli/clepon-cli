from typing import List
from pydantic import BaseModel

from . import Function


class Project(BaseModel):
    project_token: str
    functions: List[Function]

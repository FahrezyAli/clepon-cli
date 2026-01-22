from typing import List

from pydantic import BaseModel

from .function import Function


class Project(BaseModel):
    project_token: str
    functions: List[Function]

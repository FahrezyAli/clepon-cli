from typing import Optional

from pydantic import BaseModel


class FunctionArgument(BaseModel):
    id: str
    argument_name: str
    argument_type: Optional[str] = None

from typing import List, Optional

from pydantic import BaseModel

from .function_argument import FunctionArgument


class Function(BaseModel):
    id: str
    source_code: str
    input: List[FunctionArgument]
    output_type: Optional[str] = None
    file: str

from pydantic import BaseModel, StringConstraints, ConfigDict
from typing import Annotated, Literal


class Events(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=64)]
    severity: Literal["info", "warning", "critical"]
    message: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]

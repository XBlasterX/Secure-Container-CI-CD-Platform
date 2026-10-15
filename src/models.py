from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints


class Events(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=64)]
    severity: Literal["info", "warning", "critical"]
    message: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]

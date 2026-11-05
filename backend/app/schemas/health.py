from typing import Literal
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: Literal["study-materials-backend"] = "study-materials-backend"

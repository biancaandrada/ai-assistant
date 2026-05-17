from pydantic import BaseModel
from typing import Any


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = {}


class ErrorResponse(BaseModel):
    error: ErrorBody

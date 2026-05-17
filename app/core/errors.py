"""Application exception hierarchy. Convert to HTTP responses in middleware."""
from typing import Any


class AppError(Exception):
    """Base class for all domain errors. Maps to HTTP via middleware."""

    status_code: int = 500
    code: str = "internal_error"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {"error": {"code": self.code, "message": self.message, "details": self.details}}


class ValidationError(AppError):
    status_code = 400
    code = "validation_error"


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class ExternalServiceError(AppError):
    """OpenAI, ChromaDB, etc. failed."""
    status_code = 502
    code = "external_service_error"


class RateLimitError(AppError):
    status_code = 429
    code = "rate_limited"


class AgentError(AppError):
    """Agent loop failed (bad JSON, max steps exceeded, etc.)."""
    status_code = 500
    code = "agent_error"

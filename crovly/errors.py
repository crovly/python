"""Crovly SDK error classes."""

from __future__ import annotations

from typing import Any, List, Optional


class CrovlyError(Exception):
    """Base error for all Crovly API errors."""

    def __init__(
        self,
        message: str,
        code: str,
        status_code: Optional[int] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"message={self.message!r}, "
            f"code={self.code!r}, "
            f"status_code={self.status_code})"
        )


class AuthenticationError(CrovlyError):
    """Raised when the secret key is invalid or missing (HTTP 401)."""

    def __init__(self, message: str = "Invalid or missing secret key") -> None:
        super().__init__(message, "authentication_error", 401)


class ValidationError(CrovlyError):
    """Raised when request parameters are invalid (HTTP 400)."""

    def __init__(
        self,
        message: str = "Invalid request parameters",
        details: Optional[List[dict[str, Any]]] = None,
    ) -> None:
        super().__init__(message, "validation_error", 400)
        self.details = details


class RateLimitError(CrovlyError):
    """Raised when rate limit is exceeded (HTTP 429)."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
    ) -> None:
        super().__init__(message, "rate_limit_error", 429)
        self.retry_after = retry_after


class ApiError(CrovlyError):
    """Raised for unexpected server errors (HTTP 5xx)."""

    def __init__(
        self,
        message: str = "Internal server error",
        status_code: int = 500,
    ) -> None:
        super().__init__(message, "api_error", status_code)

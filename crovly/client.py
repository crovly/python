"""Crovly HTTP clients for captcha token verification."""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

import httpx

from .errors import (
    ApiError,
    AuthenticationError,
    CrovlyError,
    RateLimitError,
    ValidationError,
)
from .types import VerifyResponse

DEFAULT_API_URL = "https://api.crovly.com"
DEFAULT_TIMEOUT = 10.0
DEFAULT_MAX_RETRIES = 2
RETRY_BASE_S = 0.2
SDK_VERSION = "1.0.0"


def _build_verify_body(
    token: str,
    expected_ip: Optional[str] = None,
) -> Dict[str, Any]:
    """Build the JSON body for a verify-token request."""
    body: Dict[str, Any] = {"token": token}
    if expected_ip is not None:
        body["expectedIp"] = expected_ip
    return body


def _parse_verify_response(data: Dict[str, Any]) -> VerifyResponse:
    """Parse the API response into a VerifyResponse dataclass."""
    return VerifyResponse(
        success=data.get("success", False),
        score=float(data.get("score", 0.0)),
        ip=data.get("ip", ""),
        solved_at=int(data.get("solvedAt", 0)),
    )


def _raise_for_status(response: httpx.Response) -> None:
    """Raise a typed error based on HTTP status code."""
    try:
        body = response.json()
    except Exception:
        body = {}

    message = body.get("error", response.reason_phrase or "Unknown error")
    status = response.status_code

    if status == 400:
        raise ValidationError(message, body.get("details"))
    if status == 401:
        raise AuthenticationError(message)
    if status == 429:
        retry_after_header = response.headers.get("Retry-After")
        retry_after = int(retry_after_header) if retry_after_header else None
        raise RateLimitError(message, retry_after)
    if status >= 500:
        raise ApiError(message, status)

    raise CrovlyError(message, "api_error", status)


class Crovly:
    """Synchronous Crovly client for verifying captcha tokens.

    Usage::

        from crovly import Crovly

        client = Crovly("crvl_secret_xxx")
        result = client.verify(token, expected_ip="1.2.3.4")

        if result.is_human():
            # allow the request
            pass

    Args:
        secret_key: Your Crovly secret key (crvl_secret_xxx).
        api_url: API base URL. Default: https://api.crovly.com
        timeout: Request timeout in seconds. Default: 10.0
        max_retries: Max retries on 5xx/network errors. Default: 2
    """

    def __init__(
        self,
        secret_key: str,
        *,
        api_url: str = DEFAULT_API_URL,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        if not secret_key:
            raise ValueError(
                "Crovly secret key is required. "
                "Get yours at https://app.crovly.com/dashboard/sites"
            )

        self._secret_key = secret_key
        self._api_url = api_url.rstrip("/")
        self._timeout = timeout
        self._max_retries = max_retries
        self._client = httpx.Client(timeout=self._timeout)

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._secret_key}",
            "Content-Type": "application/json",
            "User-Agent": f"crovly-python/{SDK_VERSION}",
        }

    def verify(
        self,
        token: str,
        *,
        expected_ip: Optional[str] = None,
    ) -> VerifyResponse:
        """Verify a captcha token.

        Args:
            token: The captcha token from the client widget.
            expected_ip: Expected client IP for IP binding validation.

        Returns:
            VerifyResponse with success, score, ip, and solved_at.

        Raises:
            AuthenticationError: Invalid or missing secret key (401).
            ValidationError: Invalid request parameters (400).
            RateLimitError: Rate limit exceeded (429).
            ApiError: Server error (5xx).
            CrovlyError: Any other API error.
        """
        url = f"{self._api_url}/verify-token"
        body = _build_verify_body(token, expected_ip)
        last_error: Optional[Exception] = None

        for attempt in range(self._max_retries + 1):
            if attempt > 0:
                time.sleep(RETRY_BASE_S * (2 ** (attempt - 1)))

            try:
                response = self._client.request(
                    "POST",
                    url,
                    headers=self._headers(),
                    json=body,
                )

                if response.is_success:
                    return _parse_verify_response(response.json())

                # Non-retryable errors
                if response.status_code < 500:
                    _raise_for_status(response)

                # 5xx - retry if attempts remain
                last_error = ApiError(
                    response.reason_phrase or "Server error",
                    response.status_code,
                )

            except (CrovlyError, AuthenticationError, ValidationError, RateLimitError):
                raise
            except Exception as exc:
                last_error = exc

        if last_error is not None:
            raise last_error
        raise ApiError("Request failed after retries")

    def close(self) -> None:
        """Close the underlying HTTP client and release connections."""
        self._client.close()

    def __enter__(self) -> "Crovly":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def __del__(self) -> None:
        try:
            self._client.close()
        except Exception:
            pass


class AsyncCrovly:
    """Async Crovly client for verifying captcha tokens.

    For use with FastAPI, async Django, Starlette, and other async frameworks.

    Usage::

        from crovly import AsyncCrovly

        async with AsyncCrovly("crvl_secret_xxx") as client:
            result = await client.verify(token, expected_ip="1.2.3.4")
            if result.is_human():
                # allow the request
                pass

    Args:
        secret_key: Your Crovly secret key (crvl_secret_xxx).
        api_url: API base URL. Default: https://api.crovly.com
        timeout: Request timeout in seconds. Default: 10.0
        max_retries: Max retries on 5xx/network errors. Default: 2
    """

    def __init__(
        self,
        secret_key: str,
        *,
        api_url: str = DEFAULT_API_URL,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        if not secret_key:
            raise ValueError(
                "Crovly secret key is required. "
                "Get yours at https://app.crovly.com/dashboard/sites"
            )

        self._secret_key = secret_key
        self._api_url = api_url.rstrip("/")
        self._timeout = timeout
        self._max_retries = max_retries
        self._client = httpx.AsyncClient(timeout=self._timeout)

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._secret_key}",
            "Content-Type": "application/json",
            "User-Agent": f"crovly-python/{SDK_VERSION}",
        }

    async def verify(
        self,
        token: str,
        *,
        expected_ip: Optional[str] = None,
    ) -> VerifyResponse:
        """Verify a captcha token asynchronously.

        Args:
            token: The captcha token from the client widget.
            expected_ip: Expected client IP for IP binding validation.

        Returns:
            VerifyResponse with success, score, ip, and solved_at.

        Raises:
            AuthenticationError: Invalid or missing secret key (401).
            ValidationError: Invalid request parameters (400).
            RateLimitError: Rate limit exceeded (429).
            ApiError: Server error (5xx).
            CrovlyError: Any other API error.
        """
        import asyncio

        url = f"{self._api_url}/verify-token"
        body = _build_verify_body(token, expected_ip)
        last_error: Optional[Exception] = None

        for attempt in range(self._max_retries + 1):
            if attempt > 0:
                await asyncio.sleep(RETRY_BASE_S * (2 ** (attempt - 1)))

            try:
                response = await self._client.request(
                    "POST",
                    url,
                    headers=self._headers(),
                    json=body,
                )

                if response.is_success:
                    return _parse_verify_response(response.json())

                # Non-retryable errors
                if response.status_code < 500:
                    _raise_for_status(response)

                # 5xx - retry if attempts remain
                last_error = ApiError(
                    response.reason_phrase or "Server error",
                    response.status_code,
                )

            except (CrovlyError, AuthenticationError, ValidationError, RateLimitError):
                raise
            except Exception as exc:
                last_error = exc

        if last_error is not None:
            raise last_error
        raise ApiError("Request failed after retries")

    async def close(self) -> None:
        """Close the underlying async HTTP client and release connections."""
        await self._client.aclose()

    async def __aenter__(self) -> "AsyncCrovly":
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()

    def __del__(self) -> None:
        try:
            if not self._client.is_closed:
                import warnings
                warnings.warn(
                    "AsyncCrovly client was not closed. Use 'async with AsyncCrovly(...)' or call 'await client.close()'.",
                    ResourceWarning,
                    stacklevel=2,
                )
        except Exception:
            pass

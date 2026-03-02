# Crovly Python SDK

Official Python SDK for [Crovly](https://crovly.com) — privacy-first, Proof of Work captcha verification.

## Installation

```bash
pip install crovly
```

## Quick Start

```python
from crovly import Crovly

client = Crovly("crvl_secret_xxx")

# Verify a captcha token from the widget
result = client.verify(token, expected_ip=request_ip)

if result.is_human():
    # Allow the request
    print(f"Human verified (score: {result.score})")
else:
    # Block the request
    print("Verification failed")
```

## Async Usage (FastAPI)

```python
from fastapi import FastAPI, Request, HTTPException
from crovly import AsyncCrovly

app = FastAPI()
crovly = AsyncCrovly("crvl_secret_xxx")

@app.post("/submit")
async def submit_form(request: Request):
    data = await request.json()
    token = data.get("crovly_token")

    if not token:
        raise HTTPException(400, "Missing captcha token")

    result = await crovly.verify(token, expected_ip=request.client.host)

    if not result.is_human():
        raise HTTPException(403, "Captcha verification failed")

    return {"message": "Form submitted successfully"}

@app.on_event("shutdown")
async def shutdown():
    await crovly.close()
```

Or use the async context manager:

```python
async with AsyncCrovly("crvl_secret_xxx") as client:
    result = await client.verify(token)
```

## Django Middleware

```python
# middleware.py
from crovly import Crovly, CrovlyError

crovly_client = Crovly("crvl_secret_xxx")

PROTECTED_PATHS = ["/contact", "/register", "/login"]

class CrovlyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == "POST" and request.path in PROTECTED_PATHS:
            token = request.POST.get("crovly_token")
            if not token:
                from django.http import JsonResponse
                return JsonResponse({"error": "Missing captcha token"}, status=400)

            try:
                result = crovly_client.verify(
                    token,
                    expected_ip=self._get_client_ip(request),
                )
                if not result.is_human():
                    from django.http import JsonResponse
                    return JsonResponse({"error": "Captcha failed"}, status=403)
            except CrovlyError:
                from django.http import JsonResponse
                return JsonResponse({"error": "Verification error"}, status=500)

        return self.get_response(request)

    def _get_client_ip(self, request):
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            return xff.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")
```

Add to `settings.py`:

```python
MIDDLEWARE = [
    # ...
    "yourapp.middleware.CrovlyMiddleware",
]
```

## Flask

```python
from flask import Flask, request, jsonify
from crovly import Crovly

app = Flask(__name__)
client = Crovly("crvl_secret_xxx")

@app.route("/submit", methods=["POST"])
def submit():
    token = request.form.get("crovly_token")
    if not token:
        return jsonify(error="Missing captcha token"), 400

    result = client.verify(token, expected_ip=request.remote_addr)

    if not result.is_human():
        return jsonify(error="Captcha verification failed"), 403

    return jsonify(message="Success")
```

## Custom Threshold

The default threshold for `is_human()` is `0.5`. You can adjust it:

```python
# Stricter — require higher confidence
if result.is_human(threshold=0.7):
    allow()

# Lenient — allow lower scores
if result.is_human(threshold=0.3):
    allow()

# Manual score check
if result.success and result.score >= 0.8:
    allow()
```

## Configuration

```python
client = Crovly(
    "crvl_secret_xxx",
    api_url="https://api.crovly.com",  # API base URL
    timeout=10.0,                       # Request timeout (seconds)
    max_retries=2,                      # Retries on 5xx/network errors
)
```

## Error Handling

```python
from crovly import (
    Crovly,
    CrovlyError,
    AuthenticationError,
    ValidationError,
    RateLimitError,
    ApiError,
)

client = Crovly("crvl_secret_xxx")

try:
    result = client.verify(token)
except AuthenticationError:
    # Invalid or missing secret key (401)
    print("Check your secret key")
except ValidationError as e:
    # Invalid request parameters (400)
    print(f"Bad request: {e.message}")
except RateLimitError as e:
    # Rate limit exceeded (429)
    print(f"Rate limited, retry after: {e.retry_after}")
except ApiError as e:
    # Server error (5xx)
    print(f"Server error: {e.status_code}")
except CrovlyError as e:
    # Any other API error
    print(f"Error: {e.message} (code: {e.code})")
```

### Error Classes

| Class | Status | When |
|-------|--------|------|
| `AuthenticationError` | 401 | Invalid or missing secret key |
| `ValidationError` | 400 | Invalid token or request body |
| `RateLimitError` | 429 | Too many requests |
| `ApiError` | 5xx | Server error (retried automatically) |
| `CrovlyError` | - | Base class for all errors |

## VerifyResponse

| Field | Type | Description |
|-------|------|-------------|
| `success` | `bool` | Whether the token is valid |
| `score` | `float` | Risk score: 0.0 (bot) to 1.0 (human) |
| `ip` | `str` | IP address that solved the challenge |
| `solved_at` | `str` | ISO 8601 timestamp |

## Requirements

- Python 3.9+
- httpx

## Documentation

Full documentation at [docs.crovly.com](https://docs.crovly.com).

## License

MIT

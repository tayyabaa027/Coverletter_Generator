"""
Thin wrapper around the Groq API.
Handles validation, error handling, and logging.
"""
import os
import sys
import logging
import httpx

logger = logging.getLogger("coverletter.llm")
logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s")

# ---------------------------------------------------------------------------
# API key validation
# ---------------------------------------------------------------------------
_api_key = os.environ.get("GROQ_API_KEY", "").strip().strip('"').strip("'")

if not _api_key:
    logger.critical(
        "GROQ_API_KEY is not set. "
        "Add it to your .env file or export it as an environment variable. "
        "Get a free key at https://console.groq.com/keys"
    )
    sys.exit(1)

logger.info("GROQ_API_KEY loaded (starts with %s…, length %d)", _api_key[:6], len(_api_key))

# ---------------------------------------------------------------------------
# Model configuration
# ---------------------------------------------------------------------------
MODEL = "llama-3.3-70b-versatile"  # Fast, free-tier Groq model
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

class GroqError(Exception):
    """Raised when the Groq API returns an error."""

    def __init__(self, message: str, status_code: int = 502, suggestion: str = ""):
        super().__init__(message)
        self.status_code = status_code
        self.suggestion = suggestion


def _call_groq(messages: list[dict], max_tokens: int = 1024) -> str:
    """Make a synchronous call to the Groq chat completions API."""
    headers = {
        "Authorization": f"Bearer {_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.7,
    }
    try:
        response = httpx.post(GROQ_API_URL, json=payload, headers=headers, timeout=60)
    except httpx.RequestError as exc:
        raise GroqError(
            message=f"Network error connecting to Groq API: {exc}",
            status_code=503,
            suggestion="Check your internet connection and try again.",
        ) from exc

    if response.status_code == 401:
        raise GroqError(
            message="Groq API key is invalid or expired.",
            status_code=401,
            suggestion="Generate a new key at https://console.groq.com/keys and update your .env file.",
        )
    if response.status_code == 429:
        raise GroqError(
            message="Groq rate limit exceeded.",
            status_code=429,
            suggestion="Wait a moment and try again. Groq free tier has generous limits — this should resolve quickly.",
        )
    if response.status_code == 400:
        detail = response.json().get("error", {}).get("message", str(response.text))
        raise GroqError(
            message=f"Bad request to Groq API: {detail}",
            status_code=400,
        )
    if not response.is_success:
        raise GroqError(
            message=f"Groq API returned HTTP {response.status_code}: {response.text[:200]}",
            status_code=502,
        )

    data = response.json()
    content = data["choices"][0]["message"]["content"]
    if not content:
        raise GroqError(message="Groq returned an empty response. Please try again.", status_code=502)
    return content


def verify_api_key() -> dict:
    """Lightweight connectivity + auth test. Returns status dict or raises GroqError."""
    result = _call_groq(
        messages=[{"role": "user", "content": "Respond with exactly: OK"}],
        max_tokens=10,
    )
    return {
        "status": "ok",
        "model": MODEL,
        "api_key_prefix": _api_key[:8] + "…",
        "test_response": result[:100],
    }


def generate_cover_letter(system_prompt: str, user_prompt: str) -> str:
    """
    Generates a complete cover letter and returns the full text.
    Raises GroqError with an appropriate HTTP status on failure.
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    logger.info("Calling Groq model=%s, prompt_length=%d chars", MODEL, len(system_prompt) + len(user_prompt))
    result = _call_groq(messages, max_tokens=1200)
    logger.info("Cover letter generated — %d words", len(result.split()))
    return result

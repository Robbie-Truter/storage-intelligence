"""Agent execution and model error types."""


class AgentError(Exception):
    """Base class for agent execution errors."""


class AgentModelError(AgentError):
    """The agent model failed during construction or execution."""

    def __init__(self, message: str, status_code: int = 503) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def format_model_error(exc: Exception) -> tuple[int, str]:
    """Extract an HTTP status code and user-facing error message from a model error."""
    raw_msg = str(exc)
    raw_lower = raw_msg.lower()
    exc_type_name = type(exc).__name__.lower()

    # Detect HTTP status code on the exception if present
    code = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    status_code: int | None = code if isinstance(code, int) else None

    # 1. Model Overloaded / Capacity issues (e.g. Gemini "The model is overloaded")
    is_overloaded = (
        "overloaded" in raw_lower
        or "capacity" in raw_lower
        or "overloadederror" in exc_type_name
    )
    if is_overloaded:
        return 503, "The AI model is currently overloaded. Please try again in a few moments."

    # 2. Rate limit / Quota exhausted (429 or ResourceExhausted)
    is_rate_limited = (
        status_code == 429
        or "resource_exhausted" in raw_lower
        or "resourceexhausted" in exc_type_name
        or "quota" in raw_lower
        or "rate limit" in raw_lower
        or "ratelimit" in exc_type_name
        or "too many requests" in raw_lower
    )
    if is_rate_limited:
        return (
            429,
            (
                "The AI model rate limit or quota has been exceeded. "
                "Please check your provider quota or try again later."
            ),
        )

    # 3. Authentication / Invalid API key (401 / 403)
    if (
        status_code in (401, 403)
        or "invalid api key" in raw_lower
        or "api_key_invalid" in raw_lower
        or "authentication" in raw_lower
        or "unauthorized" in raw_lower
        or "authenticationerror" in exc_type_name
    ):
        return 401, "Invalid API key provided for the model provider."

    # 4. Context length / prompt size exceeded (400)
    if (
        status_code == 400
        or "context length" in raw_lower
        or "maximum context" in raw_lower
        or "token limit" in raw_lower
    ):
        return 400, "The request exceeds the model's maximum context length."

    # 5. Upstream Service Unavailable (502 / 503 / 504)
    if (
        status_code in (502, 503, 504)
        or "service unavailable" in raw_lower
        or "bad gateway" in raw_lower
    ):
        return 503, "The AI model provider is temporarily unavailable. Please try again later."

    # 6. Fallback
    fallback_status = status_code if status_code and 400 <= status_code < 600 else 503
    return fallback_status, f"Agent model run failed: {raw_msg}"

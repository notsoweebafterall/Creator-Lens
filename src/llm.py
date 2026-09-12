import os
import re
import time
from typing import Any, Callable

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types
from openai import OpenAI

from src.logging_utils import log_llm_event

load_dotenv()

gemini_client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

groq_client = OpenAI(
    api_key=GROQ_API_KEY or "dummy",
    base_url="https://api.groq.com/openai/v1"
) if GROQ_API_KEY else None


def call_llm_with_fallback(
    gemini_fn: Callable[[], Any],
    groq_fn: Callable[[], Any] | None = None,
    *,
    purpose: str,
    model: str | None = None,
    max_retries: int = 5,
) -> tuple[Any, str]:
    """
    Executes a Gemini SDK call `gemini_fn()` with exponential backoff retry.
    If all Gemini retries are exhausted and `groq_fn` is provided, transparently falls back to Groq.
    Returns a tuple of (response, model_used).
    Logs the ACTUAL model_used to log_llm_event.
    """
    model_name = model or DEFAULT_MODEL
    start_time = time.time()

    last_exc = None
    for attempt in range(max_retries):
        try:
            response = gemini_fn()
            latency = time.time() - start_time
            usage = getattr(response, "usage_metadata", None)
            log_llm_event(
                purpose=purpose,
                model=model_name,
                status="success" if attempt == 0 else "retry_success",
                latency_seconds=latency,
                input_tokens=getattr(usage, "prompt_token_count", None),
                output_tokens=getattr(usage, "candidates_token_count", None),
                total_tokens=getattr(usage, "total_token_count", None),
            )
            return response, model_name
        except (errors.ServerError, errors.ClientError, errors.APIError, Exception) as exc:
            last_exc = exc
            exc_str = str(exc)
            if attempt < max_retries - 1:
                m = re.search(r'retry in (\d+\.?\d*)s', exc_str)
                if m:
                    delay = min(float(m.group(1)) + 1.0, 65.0)
                elif any(token in exc_str for token in ["429", "RESOURCE_EXHAUSTED", "503", "UNAVAILABLE"]):
                    delay = (attempt + 1) * 2.0
                else:
                    delay = (attempt + 1) * 1.5
                time.sleep(delay)

    # Gemini retries exhausted -> attempt Groq fallback
    if groq_fn is not None:
        groq_model_name = f"groq/{GROQ_MODEL}"
        groq_start = time.time()
        try:
            response = groq_fn()
            latency = time.time() - groq_start
            usage = getattr(response, "usage", None)
            log_llm_event(
                purpose=purpose,
                model=groq_model_name,
                status="fallback_groq_success",
                latency_seconds=latency,
                input_tokens=getattr(usage, "prompt_tokens", None),
                output_tokens=getattr(usage, "completion_tokens", None),
                total_tokens=getattr(usage, "total_tokens", None),
            )
            return response, groq_model_name
        except Exception as groq_exc:
            log_llm_event(
                purpose=purpose,
                model=groq_model_name,
                status="fallback_groq_error",
                latency_seconds=time.time() - groq_start,
            )
            raise groq_exc

    latency = time.time() - start_time
    log_llm_event(
        purpose=purpose,
        model=model_name,
        status="error",
        latency_seconds=latency,
    )
    raise last_exc


def call_gemini_with_retry(
    fn: Callable[[], Any],
    groq_fn: Callable[[], Any] | None = None,
    *,
    purpose: str,
    model: str | None = None,
    max_retries: int = 5,
) -> tuple[Any, str]:
    """
    Wrapper alias for call_llm_with_fallback for backwards compatibility.
    Returns (response, model_used).
    """
    return call_llm_with_fallback(
        fn,
        groq_fn=groq_fn,
        purpose=purpose,
        model=model,
        max_retries=max_retries,
    )
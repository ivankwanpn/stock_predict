import logging
import time
from typing import Optional

from openai import OpenAI

from app.config import settings

logger = logging.getLogger(__name__)


def get_client(timeout: float = 300.0) -> OpenAI:
    return OpenAI(
        api_key=settings.DEEPSEEK_API_KEY,
        base_url=settings.DEEPSEEK_BASE_URL,
        timeout=timeout,
    )


def analyze(
    system_prompt: str,
    user_prompt: str,
    model: Optional[str] = None,
    max_retries: int = 3,
    timeout: float = 300.0,
) -> str:
    client = get_client(timeout=timeout)
    model = model or settings.DEEPSEEK_MODEL

    last_error = None
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,
            )
            return response.choices[0].message.content or ""

        except Exception as e:
            last_error = e
            logger.warning("DeepSeek API attempt %d/%d failed: %s", attempt + 1, max_retries, e)
            if attempt < max_retries - 1:
                wait = 2 ** attempt
                time.sleep(wait)

    raise RuntimeError(f"DeepSeek API call failed after {max_retries} retries: {last_error}")

import logging
import os

import anthropic

from src.domain.query_ask.repository import LLMClient as LLMClientABC

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "claude-haiku-4-5-20251001"
_DEFAULT_MAX_TOKENS = 1024


class LLMClient(LLMClientABC):
    """Anthropic Claude LLM adapter.

    Model and token cap are configurable via environment variables:
      LLM_MODEL      — Claude model ID (default: claude-haiku-4-5-20251001)
      LLM_MAX_TOKENS — Hard cap on response tokens; bounds cost and latency (default: 1024)
    """

    def __init__(self, api_key: str) -> None:
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = os.getenv("LLM_MODEL", _DEFAULT_MODEL)
        self._max_tokens = int(os.getenv("LLM_MAX_TOKENS", str(_DEFAULT_MAX_TOKENS)))

    def llm_complete(self, system: str, messages: list[dict]) -> str:
        """Generate a response using Claude.

        Args:
            system: System prompt string.
            messages: Conversation messages with 'role' and 'content' keys.

        Returns:
            The model's text response.
        """
        logger.debug("Calling Claude model=%s max_tokens=%d", self._model, self._max_tokens)
        response = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system=system,
            messages=messages,
        )
        return response.content[0].text

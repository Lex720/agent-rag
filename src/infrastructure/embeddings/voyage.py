import logging
import os

import voyageai

from src.domain.query_ask.repository import EmbeddingClient as EmbeddingClientABC

logger = logging.getLogger(__name__)


class EmbeddingClient(EmbeddingClientABC):
    """Voyage AI embedding adapter."""

    _MODEL = os.getenv("EMBED_MODEL", "voyage-4-lite")

    def __init__(self, api_key: str) -> None:
        self._client = voyageai.Client(api_key=api_key)

    def embedding_create(self, text: str) -> list[float]:
        """Create an embedding vector using Voyage AI.

        Args:
            text: Input text to embed.

        Returns:
            1024-dimensional embedding vector.
        """
        logger.debug("Creating embedding for text of length %d", len(text))
        result = self._client.embed([text], model=self._MODEL, input_type="query")
        return result.embeddings[0]

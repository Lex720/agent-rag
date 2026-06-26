from abc import ABC, abstractmethod

from src.domain.query_ask.entity import Chunk


class ChunkRepository(ABC):
    @abstractmethod
    def chunk_search(self, embedding: list[float], top_k: int = 5) -> list[Chunk]:
        """Search for the most similar chunks by cosine distance.

        Args:
            embedding: Query embedding vector.
            top_k: Number of results to return.

        Returns:
            List of Chunk objects ordered by similarity descending.
        """
        ...


class EmbeddingClient(ABC):
    @abstractmethod
    def embedding_create(self, text: str) -> list[float]:
        """Create an embedding vector for the given text.

        Args:
            text: Input text to embed.

        Returns:
            Embedding vector as a list of floats.
        """
        ...


class LLMClient(ABC):
    @abstractmethod
    def llm_complete(self, system: str, messages: list[dict]) -> str:
        """Generate a completion from the language model.

        Args:
            system: System prompt string.
            messages: List of message dicts with 'role' and 'content' keys.

        Returns:
            The model's text response.
        """
        ...


class RagClient(ABC):
    @abstractmethod
    def rag_chat(self, text: str, history: list[dict]) -> tuple[str, list[str]]:
        """Retrieve context and generate a response.

        Args:
            text: User query text.
            history: Conversation history as list of role/content dicts.

        Returns:
            Tuple of (answer, sources) where sources are 'METHOD /path' strings.
        """
        ...

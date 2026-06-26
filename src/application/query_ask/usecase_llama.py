import logging

from src.domain.query_ask.entity import Query as QueryEntity
from src.domain.query_ask.entity import QueryResult
from src.domain.query_ask.repository import RagClient as RagClientABC
from src.domain.query_ask.usecase import QueryAsk as QueryAskUsecase

logger = logging.getLogger(__name__)


class QueryAsk(QueryAskUsecase):
    """LlamaIndex RAG implementation. Delegates retrieval and generation to RagClient."""

    def __init__(self, rag_client: RagClientABC) -> None:
        self._rag_client = rag_client

    def query_ask(self, query: QueryEntity) -> QueryResult:
        """Execute a RAG query via the LlamaIndex adapter.

        Args:
            query: Query entity with text and conversation history.

        Returns:
            QueryResult with answer, updated history, and source chunk references.
        """
        answer, sources = self._rag_client.rag_chat(query.text, query.history)
        updated_history = list(query.history) + [
            {"role": "user", "content": query.text},
            {"role": "assistant", "content": answer},
        ]
        return QueryResult(answer=answer, history=updated_history, sources=sources)

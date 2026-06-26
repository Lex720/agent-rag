from abc import ABC, abstractmethod

from src.domain.query_ask.entity import Query as QueryEntity
from src.domain.query_ask.entity import QueryResult


class QueryAsk(ABC):
    @abstractmethod
    def query_ask(self, query: QueryEntity) -> QueryResult:
        """Execute a RAG query and return the answer with updated history.

        Args:
            query: The user query entity containing text and conversation history.

        Returns:
            QueryResult with answer, updated history, and source references.
        """
        ...

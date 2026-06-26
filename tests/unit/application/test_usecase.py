from unittest.mock import MagicMock

import pytest

from src.application.query_ask.usecase_manual import QueryAsk
from src.domain.query_ask.entity import Chunk, Query as QueryEntity, QueryResult


@pytest.fixture
def chunk() -> Chunk:
    return Chunk(
        id="uuid-1",
        path="/auth/login",
        method="POST",
        content="POST /auth/login\nSummary: Authenticate user\nResponses: 200 - JWT token",
        metadata={"tags": ["auth"]},
    )


@pytest.fixture
def usecase(chunk: Chunk) -> QueryAsk:
    embedding_client = MagicMock()
    embedding_client.embedding_create.return_value = [0.1] * 1024

    chunk_repo = MagicMock()
    chunk_repo.chunk_search.return_value = [chunk]

    llm_client = MagicMock()
    llm_client.llm_complete.return_value = (
        "The POST /auth/login endpoint authenticates users and returns a JWT token."
    )

    return QueryAsk(
        chunk_repo=chunk_repo,
        embedding_client=embedding_client,
        llm_client=llm_client,
    )


class TestQueryAsk:
    def test_returns_query_result(self, usecase: QueryAsk) -> None:
        query = QueryEntity(text="How does login work?")
        result = usecase.query_ask(query)
        assert isinstance(result, QueryResult)

    def test_answer_matches_llm_response(self, usecase: QueryAsk) -> None:
        query = QueryEntity(text="How does login work?")
        result = usecase.query_ask(query)
        assert "POST /auth/login" in result.answer

    def test_sources_contain_method_and_path(self, usecase: QueryAsk) -> None:
        query = QueryEntity(text="How does login work?")
        result = usecase.query_ask(query)
        assert "POST /auth/login" in result.sources

    def test_history_appended_with_user_and_assistant_turn(self, usecase: QueryAsk) -> None:
        query = QueryEntity(text="How does login work?")
        result = usecase.query_ask(query)
        assert len(result.history) == 2
        assert result.history[0]["role"] == "user"
        assert result.history[0]["content"] == "How does login work?"
        assert result.history[1]["role"] == "assistant"

    def test_existing_history_preserved(self, usecase: QueryAsk) -> None:
        existing = [
            {"role": "user", "content": "What APIs are available?"},
            {"role": "assistant", "content": "There are several endpoints..."},
        ]
        query = QueryEntity(text="Tell me about auth.", history=existing)
        result = usecase.query_ask(query)
        assert len(result.history) == 4

    def test_embedding_called_with_query_text(self, usecase: QueryAsk) -> None:
        query = QueryEntity(text="How does login work?")
        usecase.query_ask(query)
        usecase._embedding_client.embedding_create.assert_called_once_with("How does login work?")

    def test_chunk_search_called_with_embedding(self, usecase: QueryAsk) -> None:
        query = QueryEntity(text="How does login work?")
        usecase.query_ask(query)
        usecase._chunk_repo.chunk_search.assert_called_once_with([0.1] * 1024, top_k=5)

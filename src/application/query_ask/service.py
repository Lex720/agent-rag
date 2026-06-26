from functools import lru_cache

from src.application.query_ask.usecase_manual import SYSTEM_PROMPT
from src.application.query_ask.usecase_manual import QueryAsk as ManualQueryAsk
from src.domain.query_ask.usecase import QueryAsk as QueryAskUsecase
from src.infrastructure.config import config_get
from src.infrastructure.embeddings.voyage import EmbeddingClient as VoyageEmbeddingClient
from src.infrastructure.guardrails.guardrails import Guardrails
from src.infrastructure.llm.claude import LLMClient as ClaudeLLMClient
from src.infrastructure.vector_store.postgres import ChunkRepository as PostgresChunkRepository


@lru_cache
def _embedding_client() -> VoyageEmbeddingClient:
    return VoyageEmbeddingClient(api_key=config_get("VOYAGE_API_KEY"))


@lru_cache
def _chunk_repository() -> PostgresChunkRepository:
    return PostgresChunkRepository(db_url=config_get("DB_URL"))


@lru_cache
def _llm_client() -> ClaudeLLMClient:
    return ClaudeLLMClient(api_key=config_get("ANTHROPIC_API_KEY"))


@lru_cache
def guardrails() -> Guardrails:
    return Guardrails(system_prompt=SYSTEM_PROMPT)


@lru_cache
def query_ask_v1() -> QueryAskUsecase:
    return ManualQueryAsk(
        chunk_repo=_chunk_repository(),
        embedding_client=_embedding_client(),
        llm_client=_llm_client(),
    )


@lru_cache
def query_ask_v2() -> QueryAskUsecase:
    # Lazy imports to avoid LlamaIndex overhead when only v1 is used.
    from src.application.query_ask.usecase_llama import QueryAsk as LlamaQueryAsk
    from src.infrastructure.llamaindex.rag_client import RagClient as LlamaIndexRagClient

    rag_client = LlamaIndexRagClient(
        db_url=config_get("DB_URL"),
        voyage_api_key=config_get("VOYAGE_API_KEY"),
        anthropic_api_key=config_get("ANTHROPIC_API_KEY"),
        system_prompt=SYSTEM_PROMPT,
    )
    return LlamaQueryAsk(rag_client=rag_client)

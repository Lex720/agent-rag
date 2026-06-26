import logging
import os
import time

from llama_index.core import Document, Settings, StorageContext, VectorStoreIndex
from llama_index.core.llms import ChatMessage, MessageRole
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.voyageai import VoyageEmbedding
from llama_index.llms.anthropic import Anthropic as AnthropicLLM
from llama_index.vector_stores.postgres import PGVectorStore
from pydantic import PrivateAttr

from src.domain.query_ask.repository import RagClient as RagClientABC

logger = logging.getLogger(__name__)

_LLM_MODEL = os.getenv("LLM_MODEL", "claude-haiku-4-5-20251001")
_LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "1024"))
_EMBED_MODEL = os.getenv("EMBED_MODEL", "voyage-4-lite")
_EMBED_DIM = int(os.getenv("EMBED_DIM", "1024"))
_TABLE_NAME = "chunks_llama"
_TOP_K = 5
# Free tier: 3 RPM / 10K TPM. Batch size keeps each call under 10K tokens;
# sleep between calls keeps request rate under 3 RPM.
_EMBED_BATCH_SIZE = 20
_EMBED_BATCH_SLEEP = 21


class _RateLimitedVoyageEmbedding(VoyageEmbedding):
    """VoyageEmbedding with inter-batch sleep to respect free-tier rate limits."""

    _batch_call_count: int = PrivateAttr(default=0)

    def _get_text_embeddings(self, texts: list[str]) -> list[list[float]]:
        if self._batch_call_count > 0:
            logger.info("Rate limit pause: %ds before embedding batch %d", _EMBED_BATCH_SLEEP, self._batch_call_count + 1)
            time.sleep(_EMBED_BATCH_SLEEP)
        self._batch_call_count += 1
        return super()._get_text_embeddings(texts)


class RagClient(RagClientABC):
    """LlamaIndex RAG adapter: Voyage AI embeddings + PGVectorStore + Claude via ContextChatEngine."""

    def __init__(
        self,
        db_url: str,
        voyage_api_key: str,
        system_prompt: str,
        anthropic_api_key: str | None = None,
    ) -> None:
        Settings.embed_model = _RateLimitedVoyageEmbedding(
            model_name=_EMBED_MODEL,
            voyage_api_key=voyage_api_key,
            embed_batch_size=_EMBED_BATCH_SIZE,
        )
        # One document = one node. chunk_size larger than any OpenAPI operation; overlap irrelevant.
        Settings.transformations = [SentenceSplitter(chunk_size=4096, chunk_overlap=0)]
        if anthropic_api_key:
            Settings.llm = AnthropicLLM(
                model=_LLM_MODEL,
                api_key=anthropic_api_key,
                max_tokens=_LLM_MAX_TOKENS,
            )

        async_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        self._db_url = db_url
        self._vector_store = PGVectorStore(
            connection_string=db_url,
            async_connection_string=async_url,
            table_name=_TABLE_NAME,
            embed_dim=_EMBED_DIM,
        )
        self._system_prompt = system_prompt

    def initialize(self) -> None:
        """Create the vector store table if it does not exist."""
        self._vector_store._initialize()

    def clear(self) -> None:
        """Delete all rows from the vector store table before re-ingestion."""
        from sqlalchemy import create_engine, text as sa_text

        engine = create_engine(self._db_url)
        with engine.begin() as conn:
            conn.execute(sa_text(f"DELETE FROM data_{_TABLE_NAME}"))
        logger.info("Cleared existing rows from table 'data_%s'", _TABLE_NAME)

    def load(self, chunks: list[dict]) -> None:
        """Embed and store chunks via LlamaIndex ingestion pipeline."""
        docs = [
            Document(
                text=c["content"],
                metadata={"path": c["path"], "method": c["method"], **c.get("metadata", {})},
            )
            for c in chunks
        ]
        storage_context = StorageContext.from_defaults(vector_store=self._vector_store)
        logger.info("Loading %d documents into LlamaIndex vector store", len(docs))
        VectorStoreIndex.from_documents(docs, storage_context=storage_context, show_progress=True)
        logger.info("LlamaIndex load complete")

    def rag_chat(self, text: str, history: list[dict]) -> tuple[str, list[str]]:
        """Retrieve context chunks and generate a response via ContextChatEngine."""
        history_messages = [
            ChatMessage(
                role=MessageRole.USER if msg["role"] == "user" else MessageRole.ASSISTANT,
                content=msg["content"],
            )
            for msg in history
        ]

        index = VectorStoreIndex.from_vector_store(self._vector_store)
        chat_engine = index.as_chat_engine(
            chat_mode="context",
            system_prompt=self._system_prompt,
            similarity_top_k=_TOP_K,
            verbose=False,
        )
        logger.debug("Calling LlamaIndex ContextChatEngine")
        response = chat_engine.chat(text, chat_history=history_messages)

        answer = str(response)
        sources = [
            f"{node.metadata.get('method', '').upper()} {node.metadata.get('path', '')}".strip()
            for node in response.source_nodes
        ]
        return answer, sources

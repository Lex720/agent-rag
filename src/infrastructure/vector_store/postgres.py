import logging

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from src.domain.query_ask.entity import Chunk
from src.domain.query_ask.repository import ChunkRepository as ChunkRepositoryABC

logger = logging.getLogger(__name__)


class ChunkRepository(ChunkRepositoryABC):
    """PostgreSQL pgvector repository using SQLAlchemy. Compatible with Supabase direct connections."""

    def __init__(self, db_url: str) -> None:
        self._engine: Engine = create_engine(db_url)

    def chunk_search(self, embedding: list[float], top_k: int = 5) -> list[Chunk]:
        """Search for similar chunks using cosine distance via pgvector.

        Args:
            embedding: Query embedding vector (1024 dims).
            top_k: Number of results to return.

        Returns:
            List of Chunk objects ordered by similarity descending.
        """
        vector_literal = "[" + ",".join(str(v) for v in embedding) + "]"
        logger.debug("Searching top-%d chunks", top_k)

        with self._engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT id, path, method, content, metadata
                    FROM data_chunks
                    ORDER BY embedding <=> CAST(:emb AS vector)
                    LIMIT :k
                """),
                {"emb": vector_literal, "k": top_k},
            )
            return [
                Chunk(
                    id=str(row.id),
                    path=row.path,
                    method=row.method,
                    content=row.content,
                    metadata=row.metadata or {},
                )
                for row in result
            ]

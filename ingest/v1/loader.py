"""Load embedded chunks into PostgreSQL pgvector (v1 manual table: data_chunks)."""

import json
import logging

from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)

_TABLE = "data_chunks"
_BATCH_SIZE = 100


def load(chunks: list[dict], db_url: str) -> None:
    """Insert chunks with embeddings into the 'chunks' table via SQLAlchemy.

    Args:
        chunks: List of chunk dicts with 'embedding' key from embedder.py.
        db_url: PostgreSQL connection string (postgresql://...).
    """
    engine = create_engine(db_url)

    with engine.begin() as conn:
        conn.execute(text(f"DELETE FROM {_TABLE}"))
        logger.info("Cleared existing rows from table '%s'", _TABLE)

        for i in range(0, len(chunks), _BATCH_SIZE):
            batch = chunks[i : i + _BATCH_SIZE]
            rows = [
                {
                    "path": c["path"],
                    "method": c["method"],
                    "content": c["content"],
                    "embedding": "[" + ",".join(str(v) for v in c["embedding"]) + "]",
                    "metadata": json.dumps(c.get("metadata", {})),
                }
                for c in batch
            ]
            conn.execute(
                text("""
                    INSERT INTO data_chunks (path, method, content, embedding, metadata)
                    VALUES (:path, :method, :content, CAST(:embedding AS vector), CAST(:metadata AS jsonb))
                """),
                rows,
            )
            logger.info(
                "Inserted batch %d/%d", i // _BATCH_SIZE + 1, -(-len(chunks) // _BATCH_SIZE)
            )

    logger.info("Loaded %d chunks into table '%s'", len(chunks), _TABLE)


if __name__ == "__main__":
    import argparse
    import os

    from dotenv import load_dotenv

    load_dotenv()

    arg_parser = argparse.ArgumentParser(description="Load embedded chunks into PostgreSQL.")
    arg_parser.add_argument("--input", default="/tmp/chunks_embedded.json")
    args = arg_parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    with open(args.input) as f:
        import json

        chunks = json.load(f)

    load(chunks, os.environ["DB_URL"])

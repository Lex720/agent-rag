"""Build the LlamaIndex vector index from parsed chunks (v2 table: data_chunks_llama)."""

import logging

from src.infrastructure.llamaindex.rag_client import RagClient

logger = logging.getLogger(__name__)


def load(chunks: list[dict], db_url: str, voyage_api_key: str) -> None:
    """Embed and store chunks using the LlamaIndex RAG adapter.

    Args:
        chunks: List of chunk dicts from parser.py.
        db_url: Postgres connection string (postgresql://...).
        voyage_api_key: Voyage AI API key.
    """
    client = RagClient(db_url=db_url, voyage_api_key=voyage_api_key, system_prompt="")
    client.initialize()
    client.clear()
    try:
        client.load(chunks)
    except Exception:
        logger.error(
            "v2 ingestion failed after index was cleared — "
            "re-run ingestion to restore the index before querying /v2/query"
        )
        raise
    logger.info("v2 ingestion complete: %d chunks loaded", len(chunks))


if __name__ == "__main__":
    import argparse
    import json
    import os

    from dotenv import load_dotenv

    load_dotenv()

    arg_parser = argparse.ArgumentParser(description="Build LlamaIndex index from chunks.")
    arg_parser.add_argument("--input", default="/tmp/chunks.json")
    args = arg_parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    with open(args.input) as f:
        chunks = json.load(f)

    load(chunks, os.environ["DB_URL"], os.environ["VOYAGE_API_KEY"])

"""Embed parsed OpenAPI chunks using Voyage AI."""

import logging
import os
import time
from typing import Iterator

import voyageai

logger = logging.getLogger(__name__)

_MODEL = os.getenv("EMBED_MODEL", "voyage-4-lite")
# Free tier: 3 RPM / 10K TPM. Keep batches small and sleep between them.
_BATCH_SIZE = 30
_BATCH_SLEEP_SECONDS = 21


def embed(chunks: list[dict], api_key: str) -> Iterator[dict]:
    """Embed a list of chunks in batches and yield each chunk with its embedding.

    Args:
        chunks: List of chunk dicts from parser.py.
        api_key: Voyage AI API key.

    Yields:
        Chunk dict with an added 'embedding' key (list[float], 1024 dims).
    """
    client = voyageai.Client(api_key=api_key)
    total_batches = -(-len(chunks) // _BATCH_SIZE)

    for i in range(0, len(chunks), _BATCH_SIZE):
        batch = chunks[i : i + _BATCH_SIZE]
        texts = [c["content"] for c in batch]
        batch_num = i // _BATCH_SIZE + 1

        result = client.embed(texts, model=_MODEL, input_type="document")
        logger.info("Embedded batch %d/%d", batch_num, total_batches)

        for chunk, embedding in zip(batch, result.embeddings):
            yield {**chunk, "embedding": embedding}

        if batch_num < total_batches:
            logger.info("Rate limit pause: %ds before next batch", _BATCH_SLEEP_SECONDS)
            time.sleep(_BATCH_SLEEP_SECONDS)


if __name__ == "__main__":
    import argparse
    import json
    import os

    from dotenv import load_dotenv

    load_dotenv()

    arg_parser = argparse.ArgumentParser(description="Embed chunks with Voyage AI.")
    arg_parser.add_argument("--input", default="/tmp/chunks.json")
    arg_parser.add_argument("--output", default="/tmp/chunks_embedded.json")
    args = arg_parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    api_key = os.environ["VOYAGE_API_KEY"]
    with open(args.input) as f:
        chunks = json.load(f)

    embedded = list(embed(chunks, api_key))
    with open(args.output, "w") as f:
        json.dump(embedded, f)
    print(f"Embedded {len(embedded)} chunks → {args.output}")

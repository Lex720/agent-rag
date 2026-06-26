"""Orchestrate the full ingestion pipeline: parse → embed → load (v1 and v2)."""

import argparse
import logging
import os

from dotenv import load_dotenv

load_dotenv()

from ingest.parser import parse  # noqa: E402
from ingest.v1.embedder import embed  # noqa: E402
from ingest.v1.loader import load  # noqa: E402
from ingest.v2.loader_llama import load as load_llama  # noqa: E402
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_v1(spec_path: str) -> None:
    """Run the manual ingestion pipeline (Voyage AI + SQLAlchemy direct insert)."""
    logger.info("=== v1 ingestion pipeline ===")
    chunks = parse(spec_path)
    embedded = list(embed(chunks, os.environ["VOYAGE_API_KEY"]))
    load(embedded, os.environ["DB_URL"])
    logger.info("v1 ingestion complete: %d chunks loaded", len(embedded))


def run_v2(spec_path: str) -> None:
    """Run the LlamaIndex ingestion pipeline (embeddings handled by LlamaIndex)."""
    logger.info("=== v2 ingestion pipeline ===")
    chunks = parse(spec_path)
    load_llama(chunks, os.environ["DB_URL"], os.environ["VOYAGE_API_KEY"])
    logger.info("v2 ingestion complete: %d documents indexed", len(chunks))


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(description="Run ingestion pipeline.")
    arg_parser.add_argument("--input", default="data/openapi.json")
    arg_parser.add_argument(
        "--pipeline",
        choices=["v1", "v2", "both"],
        default="both",
        help="Which ingestion pipeline to run.",
    )
    args = arg_parser.parse_args()

    if args.pipeline in ("v1", "both"):
        run_v1(args.input)
    if args.pipeline in ("v2", "both"):
        run_v2(args.input)

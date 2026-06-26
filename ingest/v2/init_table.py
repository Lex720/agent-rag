"""Initialize the LlamaIndex vector table (data_chunks_llama) via RagClient."""

import logging
import os

from dotenv import load_dotenv

from src.infrastructure.llamaindex.rag_client import RagClient

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init(db_url: str, voyage_api_key: str) -> None:
    client = RagClient(db_url=db_url, voyage_api_key=voyage_api_key, system_prompt="")
    client.initialize()
    logger.info("LlamaIndex table initialized")


if __name__ == "__main__":
    init(os.environ["DB_URL"], os.environ["VOYAGE_API_KEY"])

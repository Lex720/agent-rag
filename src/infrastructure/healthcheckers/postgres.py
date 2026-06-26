import logging

import asyncpg

from src.application.healthcheckers.interface import CheckRepository
from src.infrastructure.config import config_get

logger = logging.getLogger(__name__)


class Check(CheckRepository):
    async def __call__(self) -> None:
        db_url = config_get("DB_URL").replace("postgresql://", "postgresql://", 1)
        connection = await asyncpg.connect(dsn=db_url, timeout=5.0)
        try:
            await connection.fetchval("SELECT 1")
        finally:
            await connection.close()

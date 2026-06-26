import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.infrastructure.guardrails.guardrails import GuardrailError
from src.presentation.api.resources.healthcheckers.routes import healthcheckers_router
from src.presentation.api.resources.query_ask import v1 as query_v1_router
from src.presentation.api.resources.query_ask import v2 as query_v2_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting agent-rag API")
    yield
    logger.info("Shutting down agent-rag API")


api = FastAPI(
    title="agent-rag",
    description=(
        "RAG agent for API integration documentation. "
        "v1: manual pipeline. v2: LlamaIndex pipeline."
    ),
    version="0.1.0",
    lifespan=lifespan,
)


@api.exception_handler(GuardrailError)
async def guardrail_exception_handler(request: Request, exc: GuardrailError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": exc.message})


api.include_router(healthcheckers_router)
api.include_router(query_v1_router.router)
api.include_router(query_v2_router.router)

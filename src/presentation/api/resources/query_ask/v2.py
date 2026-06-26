import logging
from typing import Annotated

from fastapi import APIRouter, Depends

from src.application.query_ask import service as query_service
from src.domain.query_ask.entity import Query as QueryEntity
from src.domain.query_ask.usecase import QueryAsk as QueryAskUsecase
from src.infrastructure.guardrails.guardrails import Guardrails
from src.presentation.api.resources.query_ask.dtos import MessageDTO, QueryRequest, QueryResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v2", tags=["v2 — LlamaIndex"])


@router.post("/query", response_model=QueryResponse)
def query_ask(
    body: QueryRequest,
    usecase: Annotated[QueryAskUsecase, Depends(query_service.query_ask_v2)],
    guardrails: Annotated[Guardrails, Depends(query_service.guardrails)],
) -> QueryResponse:
    """Ask a question about the API integrations documentation.

    This endpoint uses a LlamaIndex RAG pipeline:
    VoyageEmbedding → PGVectorStore → ContextChatEngine → Anthropic LLM.

    Args:
        body: Request with query text and optional conversation history.
        usecase: Injected v2 use case.
        guardrails: Injected guardrails instance.

    Returns:
        QueryResponse with answer, updated history, and source endpoints.
    """
    guardrails.validate_input(body.query)
    for msg in body.history:
        guardrails.validate_history_message(msg.content)

    query = QueryEntity(
        text=body.query,
        history=[msg.model_dump() for msg in body.history],
    )
    result = usecase.query_ask(query)
    answer = guardrails.validate_output(result.answer)

    logger.info("v2 query answered — sources: %s", result.sources)
    return QueryResponse(
        answer=answer,
        history=[MessageDTO(**msg) for msg in result.history],
        sources=result.sources,
    )

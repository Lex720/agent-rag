from typing import Literal

from pydantic import BaseModel, Field, field_validator


class MessageDTO(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=4000)


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    history: list[MessageDTO] = Field(default_factory=list)

    @field_validator("history")
    @classmethod
    def validate_history_length(cls, v: list) -> list:
        """Cap history at 20 messages (10 conversation turns) to bound token usage."""
        if len(v) > 20:
            raise ValueError("El historial no puede superar 20 mensajes (10 turnos).")
        return v


class QueryResponse(BaseModel):
    answer: str
    history: list[MessageDTO]
    sources: list[str]

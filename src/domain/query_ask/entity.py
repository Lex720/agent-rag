from dataclasses import dataclass, field


@dataclass(frozen=True)
class Chunk:
    """A single OpenAPI operation stored as a retrievable text chunk."""

    id: str
    path: str
    method: str
    content: str
    metadata: dict = field(default_factory=dict)


@dataclass
class Query:
    """A user query with optional conversation history."""

    text: str
    history: list[dict] = field(default_factory=list)


@dataclass
class QueryResult:
    """The agent's answer with updated history and source references."""

    answer: str
    history: list[dict]
    sources: list[str]

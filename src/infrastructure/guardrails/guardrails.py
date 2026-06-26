import logging
import re

logger = logging.getLogger(__name__)

_INJECTION_PATTERNS: list[re.Pattern] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"ignore\s+(previous|above|all)\s+instructions",
        r"forget\s+(everything|all|your)",
        r"you\s+are\s+now\s+",
        r"new\s+instructions?:",
        r"act\s+as\s+if\s+you",
        r"disregard\s+(all|your|previous)",
        r"system\s*:",
        r"<\|im_start\|>",
        r"\[INST\]",
        r"</s>",
        r"###\s*(system|instruction)",
    ]
]

# Phrases that, if present in the output, indicate a system prompt leak
_SECRET_PATTERNS: list[re.Pattern] = [
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),
    re.compile(r"sk-ant-[a-zA-Z0-9\-]{20,}"),
    re.compile(r"AIza[0-9A-Za-z\-_]{35}"),
    re.compile(r"pa-[a-zA-Z0-9]{40,}"),
]

_DOMAIN_KEYWORDS: frozenset[str] = frozenset(
    [
        "endpoint", "endpoints", "api", "apis", "route", "routes", "url", "urls",
        "http", "rest", "openapi", "swagger",
        "request", "requests", "response", "responses", "payload", "payloads",
        "body", "header", "headers", "parameter", "parameters", "param", "params",
        "auth", "token", "tokens", "oauth", "bearer", "jwt", "credential", "credentials",
        "apikey", "apikeys",
        "schema", "schemas", "json", "field", "fields", "format", "formats",
        "integration", "integrations", "webhook", "webhooks", "callback", "callbacks",
        "call", "calls", "invoke", "send", "fetch", "query", "queries",
    ]
)

_MAX_LENGTH = 500


class GuardrailError(Exception):
    """Raised when a guardrail check fails. Message is safe to return to the client."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class Guardrails:
    """Input and output validation for the RAG query pipeline."""

    def __init__(self, system_prompt: str = "") -> None:
        # Extract 4-gram phrases from system prompt for leak detection
        self._leak_phrases = self._ngrams(system_prompt.lower(), n=4)

    def validate_input(self, query: str) -> None:
        """Validate a user query before it reaches the retrieval pipeline.

        Args:
            query: Raw user query string.

        Raises:
            GuardrailError: If the query fails any validation check.
        """
        if len(query) > _MAX_LENGTH:
            raise GuardrailError(
                f"La consulta excede el límite de {_MAX_LENGTH} caracteres."
            )

        query_lower = query.lower()

        for pattern in _INJECTION_PATTERNS:
            if pattern.search(query_lower):
                logger.warning("Prompt injection attempt detected: %r", query[:80])
                raise GuardrailError("Consulta no permitida.")

        words = set(re.findall(r"\b\w+\b", query_lower))
        if not words.intersection(_DOMAIN_KEYWORDS):
            raise GuardrailError("Consulta fuera del dominio de integraciones.")

    def validate_history_message(self, content: str) -> None:
        """Validate a single history message content for injection attempts.

        Args:
            content: Message content from the conversation history.

        Raises:
            GuardrailError: If injection patterns are detected.
        """
        content_lower = content.lower()
        for pattern in _INJECTION_PATTERNS:
            if pattern.search(content_lower):
                logger.warning("Prompt injection attempt detected in history: %r", content[:80])
                raise GuardrailError("Consulta no permitida.")

    def validate_output(self, response: str) -> str:
        """Validate and sanitize the LLM response before returning it to the client.

        Args:
            response: Raw LLM response string.

        Returns:
            Sanitized response string.

        Raises:
            GuardrailError: If a system prompt leak is detected.
        """
        response_lower = response.lower()

        for phrase in self._leak_phrases:
            if phrase in response_lower:
                logger.warning("System prompt leak detected in response")
                raise GuardrailError("Respuesta no permitida.")

        for pattern in _SECRET_PATTERNS:
            response = pattern.sub("[REDACTED]", response)

        return response

    @staticmethod
    def _ngrams(text: str, n: int) -> list[str]:
        words = re.findall(r"\b\w+\b", text)
        if len(words) < n:
            return [" ".join(words)] if words else []
        return [" ".join(words[i : i + n]) for i in range(len(words) - n + 1)]

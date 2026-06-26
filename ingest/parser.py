"""Parse an input JSON file into text chunks.

Supports two formats:
- OpenAPI spec (dict with 'paths' key): one chunk per HTTP operation.
- Flat doc list (list of {id, title, content}): one chunk per document.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options"}


def parse(spec_path: str | Path) -> list[dict]:
    """Parse a JSON file into a list of chunks.

    Args:
        spec_path: Path to the JSON file. Accepts OpenAPI spec or flat doc list.

    Returns:
        List of dicts with keys: path, method, content, metadata.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the format is not recognised.
    """
    with open(spec_path) as f:
        data = json.load(f)

    if isinstance(data, list):
        chunks = _parse_docs(data)
        logger.info("Parsed %d doc chunks from %s", len(chunks), spec_path)
    elif isinstance(data, dict) and "paths" in data:
        chunks = _parse_openapi(data)
        logger.info("Parsed %d operation chunks from %s", len(chunks), spec_path)
    else:
        raise ValueError(f"Unrecognised format in {spec_path}: expected OpenAPI spec or flat doc list.")

    return chunks


def _parse_openapi(spec: dict) -> list[dict]:
    chunks = []
    for path, path_item in spec.get("paths", {}).items():
        path_params = path_item.get("parameters", [])
        for method, operation in path_item.items():
            if method not in _HTTP_METHODS:
                continue
            if path_params:
                op_param_keys = {(p.get("name"), p.get("in")) for p in operation.get("parameters", [])}
                inherited = [p for p in path_params if (p.get("name"), p.get("in")) not in op_param_keys]
                operation = {**operation, "parameters": inherited + operation.get("parameters", [])}
            chunk = _operation_to_chunk(path, method, operation)
            chunks.append(chunk)
            logger.debug("Parsed chunk: %s %s", method.upper(), path)
    return chunks


def _parse_docs(docs: list[dict]) -> list[dict]:
    chunks = []
    for doc in docs:
        doc_id = doc.get("id", "")
        title = doc.get("title", "")
        content = doc.get("content", "")
        chunks.append({
            "path": doc_id,
            "method": "DOC",
            "content": f"{title}\n\n{content}" if title else content,
            "metadata": {"id": doc_id, "title": title},
        })
        logger.debug("Parsed doc chunk: %s", doc_id)
    return chunks


def _operation_to_chunk(path: str, method: str, operation: dict) -> dict:
    lines = [f"{method.upper()} {path}"]

    if summary := operation.get("summary"):
        lines.append(f"Summary: {summary}")
    if description := operation.get("description"):
        lines.append(f"Description: {description}")

    params = operation.get("parameters", [])
    if params:
        param_strs = [
            f"{p.get('name')} ({p.get('in')}, "
            f"{'required' if p.get('required') else 'optional'}, "
            f"{p.get('schema', {}).get('type', 'any')})"
            for p in params
        ]
        lines.append(f"Parameters: {' | '.join(param_strs)}")

    if request_body := operation.get("requestBody"):
        for media_type, media_schema in request_body.get("content", {}).items():
            schema = media_schema.get("schema", {})
            properties = schema.get("properties", {})
            if properties:
                prop_strs = [
                    f"{k} ({v.get('type', 'any')})" for k, v in properties.items()
                ]
                lines.append(f"Request body ({media_type}): {', '.join(prop_strs)}")

    responses = operation.get("responses", {})
    if responses:
        resp_strs = [
            f"{status} - {resp.get('description', '')}"
            for status, resp in responses.items()
        ]
        lines.append(f"Responses: {' | '.join(resp_strs)}")

    if tags := operation.get("tags"):
        lines.append(f"Tags: {', '.join(tags)}")

    return {
        "path": path,
        "method": method.upper(),
        "content": "\n".join(lines),
        "metadata": {
            "tags": operation.get("tags", []),
            "operation_id": operation.get("operationId", ""),
        },
    }


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Parse OpenAPI spec or flat doc list into chunks.")
    parser.add_argument("--input", default="data/openapi.json")
    parser.add_argument("--output", default="/tmp/chunks.json")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    chunks = parse(args.input)
    with open(args.output, "w") as f:
        json.dump(chunks, f, indent=2)
    print(f"Wrote {len(chunks)} chunks to {args.output}")

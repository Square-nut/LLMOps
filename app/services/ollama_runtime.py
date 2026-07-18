"""Small REST client for reading the Ollama model catalogue."""

import json
from typing import Any, Dict, List
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class OllamaRuntimeError(RuntimeError):
    pass


def _root_endpoint(endpoint: str) -> str:
    value = endpoint.strip().rstrip("/")
    return value[:-3] if value.endswith("/v1") else value


def list_models(endpoint: str) -> List[Dict[str, Any]]:
    request = Request(f"{_root_endpoint(endpoint)}/api/tags", method="GET")
    try:
        with urlopen(request, timeout=20) as response:
            payload: Any = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        detail = getattr(exc, "read", lambda: b"")()
        message = detail.decode("utf-8", errors="replace") if detail else str(exc)
        raise OllamaRuntimeError(f"Ollama request failed: {message}") from exc
    return payload.get("models", []) if isinstance(payload, dict) else []

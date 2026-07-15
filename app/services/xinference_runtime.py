"""Small REST client for the Xinference model-management API."""

import json
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class XinferenceRuntimeError(RuntimeError):
    pass


def _root_endpoint(endpoint: str) -> str:
    value = endpoint.rstrip("/")
    return value[:-3] if value.endswith("/v1") else value


def _request(endpoint: str, path: str, *, method: str = "GET", body: Optional[dict] = None) -> Any:
    payload = json.dumps(body).encode("utf-8") if body is not None else None
    request = Request(
        f"{_root_endpoint(endpoint)}{path}",
        data=payload,
        headers={"Content-Type": "application/json"},
        method=method,
    )
    try:
        with urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else None
    except (HTTPError, URLError, TimeoutError) as exc:
        detail = getattr(exc, "read", lambda: b"")()
        message = detail.decode("utf-8", errors="replace") if detail else str(exc)
        raise XinferenceRuntimeError(f"Xinference request failed: {message}") from exc


def list_registrations(endpoint: str, model_type: str, detailed: bool = True) -> List[Dict[str, Any]]:
    result = _request(
        endpoint,
        f"/v1/model_registrations/{model_type}?detailed={'true' if detailed else 'false'}",
    )
    return result if isinstance(result, list) else result.get("data", [])


def list_running(endpoint: str) -> List[Dict[str, Any]]:
    result = _request(endpoint, "/v1/models")
    return result.get("data", []) if isinstance(result, dict) else []


def list_cached(endpoint: str) -> List[Dict[str, Any]]:
    """Return downloaded model artifacts, not only running instances."""
    try:
        result = _request(endpoint, "/v1/cache/models")
    except XinferenceRuntimeError:
        # Older Xinference releases used this path.
        result = _request(endpoint, "/v1/cached/list_cached_models")
    if isinstance(result, list):
        return result
    if isinstance(result, dict):
        # Xinference v2 returns {"list": [...]}; some versions return
        # {"data": [...]} for OpenAI-style endpoints.
        return result.get("list", result.get("data", []))
    return []


def launch(endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    result = _request(endpoint, "/v1/models?wait_ready=false", method="POST", body=payload)
    return result if isinstance(result, dict) else {"model_uid": result}


def terminate(endpoint: str, model_uid: str) -> None:
    _request(endpoint, f"/v1/models/{model_uid}", method="DELETE")

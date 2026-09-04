"""Minimal health check for the locally hosted Ollama service."""

from __future__ import annotations

import json
from urllib.error import URLError
from urllib.request import urlopen

from app.config.settings import validate_local_endpoint


class LocalServiceUnavailable(RuntimeError):
    """Raised when the required local Ollama service cannot be reached."""


class OllamaClient:
    """A strictly local Ollama client; it never uses a cloud fallback."""

    def __init__(self, base_url: str, timeout_seconds: float = 3.0) -> None:
        self.base_url = validate_local_endpoint(base_url)
        self.timeout_seconds = timeout_seconds

    def list_models(self) -> list[str]:
        """Return model names reported by local Ollama, with an actionable failure."""
        try:
            with urlopen(f"{self.base_url}/api/tags", timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise LocalServiceUnavailable(
                "Local Ollama is unavailable. Start Ollama and ensure it listens on the configured loopback address."
            ) from exc
        return [model["name"] for model in payload.get("models", []) if "name" in model]


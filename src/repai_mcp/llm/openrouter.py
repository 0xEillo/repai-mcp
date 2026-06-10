"""Minimal OpenRouter chat client (BYOK).

Thin wrapper over the OpenRouter chat-completions endpoint, used by the persona
layer. The key is supplied by the operator via ``OPENROUTER_API_KEY`` and the
model via ``OPENROUTER_MODEL`` (Gemini Flash class by default). When no key is
configured the factory returns None and callers degrade gracefully.
"""

from __future__ import annotations

import httpx

from repai_mcp.config import Config

_BASE_URL = "https://openrouter.ai/api/v1"
_TIMEOUT_SECONDS = 30.0


class OpenRouterError(RuntimeError):
    """Raised when an OpenRouter completion request fails."""


class OpenRouterClient:
    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        base_url: str = _BASE_URL,
        timeout: float = _TIMEOUT_SECONDS,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    @property
    def model(self) -> str:
        return self._model

    def complete(self, *, system: str, user: str, temperature: float = 0.2) -> str:
        """Return the assistant text for a single system+user exchange.

        Raises OpenRouterError on transport errors or malformed responses.
        """
        payload = {
            "model": self._model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "X-Title": "Rep AI Insights MCP",
        }
        try:
            response = httpx.post(
                f"{self._base_url}/chat/completions",
                json=payload,
                headers=headers,
                timeout=self._timeout,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
        except httpx.HTTPError as exc:
            raise OpenRouterError(f"OpenRouter request failed: {exc}") from exc
        except (KeyError, IndexError, ValueError) as exc:
            raise OpenRouterError(
                f"Unexpected OpenRouter response shape: {exc}"
            ) from exc


def create_openrouter_client(config: Config) -> OpenRouterClient | None:
    """Build a client when an API key is configured, else None (LLM disabled)."""
    if not config.openrouter_api_key:
        return None
    return OpenRouterClient(config.openrouter_api_key, config.openrouter_model)

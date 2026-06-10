"""Connectivity check tool."""

from __future__ import annotations

from pydantic import BaseModel

from repai_mcp.config import Config
from repai_mcp.store import RepAIStore


class HealthCheckResult(BaseModel):
    mode: str
    supabase_url: str
    supabase_connected: bool
    supabase_error: str | None = None
    openrouter_configured: bool


def health_check(store: RepAIStore, config: Config) -> HealthCheckResult:
    """Report mode, Supabase reachability, and OpenRouter configuration."""
    connected = False
    error: str | None = None
    try:
        store.ping()
        connected = True
    except Exception as exc:
        error = str(exc)

    return HealthCheckResult(
        mode=config.mode,
        supabase_url=config.supabase_url,
        supabase_connected=connected,
        supabase_error=error,
        openrouter_configured=config.openrouter_api_key is not None,
    )

"""Configuration resolution for demo/prod modes.

Demo mode uses baked-in credentials for the hosted demo Supabase project
(read-only scope, synthetic data only). Prod mode requires credentials via
environment variables. Env vars always override baked-in demo values.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Mapping

# Hosted demo Supabase project credentials. Safe to commit: the demo project
# contains only synthetic seed data (see supabase/demo-schema.sql +
# supabase/seed-demo.sql). Fill these in after standing up the demo project
# as described in the README "Demo Supabase setup" section. Until then, demo
# mode requires SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY env overrides.
DEMO_SUPABASE_URL = ""
DEMO_SUPABASE_SERVICE_ROLE_KEY = ""

DEFAULT_AUDIT_PATH = Path.home() / ".repai-mcp" / "audit.jsonl"

# Gemini Flash class model, aligned with Rep AI production. Overridable via
# OPENROUTER_MODEL for callers who want a different model.
DEFAULT_OPENROUTER_MODEL = "google/gemini-flash-1.5"


class Mode(StrEnum):
    DEMO = "demo"
    PROD = "prod"


class ConfigError(ValueError):
    """Raised when the environment does not yield a usable configuration."""


@dataclass(frozen=True)
class Config:
    mode: Mode
    supabase_url: str
    supabase_service_role_key: str
    openrouter_api_key: str | None
    openrouter_model: str
    audit_path: Path


def load_config(env: Mapping[str, str] | None = None) -> Config:
    if env is None:
        env = os.environ

    raw_mode = env.get("REPAI_MCP_MODE", Mode.DEMO).lower()
    try:
        mode = Mode(raw_mode)
    except ValueError:
        raise ConfigError(
            f"Invalid REPAI_MCP_MODE={raw_mode!r}; expected 'demo' or 'prod'."
        ) from None

    supabase_url = env.get("SUPABASE_URL", "").strip()
    supabase_key = env.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()

    if mode is Mode.DEMO:
        supabase_url = supabase_url or DEMO_SUPABASE_URL
        supabase_key = supabase_key or DEMO_SUPABASE_SERVICE_ROLE_KEY

    if not supabase_url or not supabase_key:
        if mode is Mode.PROD:
            raise ConfigError(
                "Prod mode requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY "
                "environment variables."
            )
        raise ConfigError(
            "Demo Supabase credentials are not yet baked in. Set SUPABASE_URL "
            "and SUPABASE_SERVICE_ROLE_KEY to point at a seeded demo project."
        )

    audit_path = Path(
        env.get("REPAI_MCP_AUDIT_PATH", "").strip() or DEFAULT_AUDIT_PATH
    ).expanduser()

    return Config(
        mode=mode,
        supabase_url=supabase_url,
        supabase_service_role_key=supabase_key,
        openrouter_api_key=env.get("OPENROUTER_API_KEY", "").strip() or None,
        openrouter_model=(
            env.get("OPENROUTER_MODEL", "").strip() or DEFAULT_OPENROUTER_MODEL
        ),
        audit_path=audit_path,
    )

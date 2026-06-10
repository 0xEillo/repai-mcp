from pathlib import Path

import pytest

from repai_mcp.config import DEFAULT_AUDIT_PATH, ConfigError, Mode, load_config

PROD_ENV = {
    "REPAI_MCP_MODE": "prod",
    "SUPABASE_URL": "https://prod.supabase.co",
    "SUPABASE_SERVICE_ROLE_KEY": "prod-key",
}


def test_prod_mode_uses_env_credentials():
    config = load_config(PROD_ENV)
    assert config.mode is Mode.PROD
    assert config.supabase_url == "https://prod.supabase.co"
    assert config.supabase_service_role_key == "prod-key"


def test_prod_mode_requires_credentials():
    with pytest.raises(ConfigError, match="Prod mode requires"):
        load_config({"REPAI_MCP_MODE": "prod"})


def test_mode_defaults_to_demo():
    env = {
        "SUPABASE_URL": "https://demo.supabase.co",
        "SUPABASE_SERVICE_ROLE_KEY": "demo-key",
    }
    assert load_config(env).mode is Mode.DEMO


def test_demo_mode_env_overrides_baked_in_credentials():
    env = {
        "REPAI_MCP_MODE": "demo",
        "SUPABASE_URL": "https://override.supabase.co",
        "SUPABASE_SERVICE_ROLE_KEY": "override-key",
    }
    config = load_config(env)
    assert config.supabase_url == "https://override.supabase.co"
    assert config.supabase_service_role_key == "override-key"


def test_demo_mode_without_credentials_raises_clear_error():
    # Baked-in demo creds are empty until the demo project is seeded.
    with pytest.raises(ConfigError, match="demo"):
        load_config({"REPAI_MCP_MODE": "demo"})


def test_invalid_mode_rejected():
    with pytest.raises(ConfigError, match="Invalid REPAI_MCP_MODE"):
        load_config({"REPAI_MCP_MODE": "staging"})


def test_audit_path_default_and_override():
    assert load_config(PROD_ENV).audit_path == DEFAULT_AUDIT_PATH

    env = PROD_ENV | {"REPAI_MCP_AUDIT_PATH": "/tmp/custom-audit.jsonl"}
    assert load_config(env).audit_path == Path("/tmp/custom-audit.jsonl")


def test_openrouter_key_optional():
    assert load_config(PROD_ENV).openrouter_api_key is None

    env = PROD_ENV | {"OPENROUTER_API_KEY": "sk-or-123"}
    assert load_config(env).openrouter_api_key == "sk-or-123"

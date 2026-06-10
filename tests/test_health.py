from pathlib import Path
from repai_mcp.config import Config, Mode
from repai_mcp.store import InMemoryRepAIStore
from repai_mcp.tools.health import health_check


def make_config(**overrides) -> Config:
    defaults = dict(
        mode=Mode.DEMO,
        supabase_url="https://demo.supabase.co",
        supabase_service_role_key="demo-key",
        openrouter_api_key=None,
        openrouter_model="google/gemini-flash-1.5",
        audit_path=Path("/tmp/audit.jsonl"),
    )
    return Config(**(defaults | overrides))


def test_health_check_reports_connected():
    store = InMemoryRepAIStore()
    result = health_check(store, make_config())

    assert result.mode == "demo"
    assert result.supabase_connected is True
    assert result.supabase_error is None
    assert result.openrouter_configured is False


def test_health_check_reports_connection_failure():
    store = InMemoryRepAIStore(ping_error=ConnectionError("DNS failure"))

    result = health_check(store, make_config())

    assert result.supabase_connected is False
    assert "DNS failure" in result.supabase_error


def test_health_check_reports_openrouter_configured():
    result = health_check(
        InMemoryRepAIStore(), make_config(openrouter_api_key="sk-or-123")
    )
    assert result.openrouter_configured is True

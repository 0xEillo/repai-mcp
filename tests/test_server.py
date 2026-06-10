import asyncio
from pathlib import Path

from repai_mcp.config import Config, Mode
from repai_mcp.server import create_server


def make_config() -> Config:
    return Config(
        mode=Mode.DEMO,
        supabase_url="https://demo.supabase.co",
        supabase_service_role_key="demo-key",
        openrouter_api_key=None,
        openrouter_model="google/gemini-flash-1.5",
        audit_path=Path("/tmp/repai-audit.jsonl"),
    )


def test_server_registers_all_tools_and_prompts():
    server = create_server(make_config())

    tool_names = {t.name for t in asyncio.run(server.list_tools())}
    assert {
        "health_check",
        "investigate_user",
        "create_ops_note",
        "find_commitment_gaps",
        "find_trial_dropoff_risk",
        "find_stuck_workout_sessions",
        "summarize_coach_engagement",
        "sample_workout_inputs",
        "describe_user_base",
    } <= tool_names

    prompt_names = {p.name for p in asyncio.run(server.list_prompts())}
    assert {"investigate-quiet-user", "understand-user-base"} <= prompt_names

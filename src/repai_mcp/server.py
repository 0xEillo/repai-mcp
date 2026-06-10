"""FastMCP entrypoint. Runs over stdio."""

from __future__ import annotations

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from repai_mcp.audit import AuditLogger
from repai_mcp.config import Config, load_config
from repai_mcp.llm.openrouter import create_openrouter_client
from repai_mcp.store import create_repai_store
from typing import Any

from repai_mcp.tools.health import HealthCheckResult
from repai_mcp.tools.health import health_check as run_health_check
from repai_mcp.tools.ops_notes import OpsNote
from repai_mcp.tools.ops_notes import create_ops_note as run_create_ops_note
from repai_mcp.tools import cohort, investigate, retention


def create_server(config: Config) -> FastMCP:
    server = FastMCP(
        "repai-mcp",
        instructions=(
            "Operational insights for Rep AI, a live AI workout tracker. "
            "Tools answer founder-level questions about users, training "
            "behaviour, retention, and product health from the Supabase "
            f"backend. Running in {config.mode} mode."
        ),
    )
    audit = AuditLogger(config.audit_path, mode=config.mode)
    store = create_repai_store(config)
    llm = create_openrouter_client(config)

    @server.tool()
    @audit.audited
    def health_check() -> HealthCheckResult:
        """Check connectivity: current mode, Supabase reachability, and
        whether OpenRouter is configured for LLM-powered tools."""
        return run_health_check(store, config)

    @server.tool()
    @audit.audited
    def investigate_user(user_tag: str) -> investigate.UserDigest:
        """Return a complete structured digest for one user by user_tag:
        onboarding intent, workout history, behavioural training signals, AI
        chat volume, coach engagement, lifecycle emails, and strength snapshot.
        Errors clearly if the user_tag is unknown. Includes an LLM-classified
        training persona when OPENROUTER_API_KEY is configured."""
        return investigate.investigate_user(
            store, user_tag=user_tag, llm=llm
        )

    @server.tool()
    @audit.audited
    def create_ops_note(
        user_tag: str,
        note: str,
        metadata: dict[str, Any] | None = None,
    ) -> OpsNote:
        """Record an internal operator note about a user, linked by user_tag.

        Use this to log investigation findings or follow-ups. The note is
        stored in the Rep AI backend alongside user data."""
        return run_create_ops_note(
            store, user_tag=user_tag, note=note, metadata=metadata
        )

    @server.tool()
    @audit.audited
    def find_commitment_gaps(
        lookback_days: int = 14,
        min_gap_per_week: float = 1.0,
        limit: int = 50,
    ) -> retention.CommitmentGapsResult:
        """Find users whose stated weekly workout commitment exceeds their
        actual workout frequency. Surfaces users drifting from their intent."""
        return retention.find_commitment_gaps(
            store,
            lookback_days=lookback_days,
            min_gap_per_week=min_gap_per_week,
            limit=limit,
        )

    @server.tool()
    @audit.audited
    def find_trial_dropoff_risk(
        trial_window_days: int = 14,
        inactive_days: int = 5,
        limit: int = 50,
    ) -> retention.TrialDropoffResult:
        """Find trial users who have gone quiet — trial started recently but
        no workouts logged in the last `inactive_days`."""
        return retention.find_trial_dropoff_risk(
            store,
            trial_window_days=trial_window_days,
            inactive_days=inactive_days,
            limit=limit,
        )

    @server.tool()
    @audit.audited
    def find_stuck_workout_sessions(
        older_than_minutes: int = 15,
        limit: int = 50,
    ) -> retention.StuckSessionsResult:
        """Find workout sessions stuck in processing — a signal of failed or
        abandoned AI workout generation."""
        return retention.find_stuck_workout_sessions(
            store, older_than_minutes=older_than_minutes, limit=limit
        )

    @server.tool()
    @audit.audited
    def summarize_coach_engagement(
        lookback_days: int = 30,
    ) -> retention.CoachEngagementResult:
        """Summarize proactive coach message engagement: sent vs consumed,
        overall and by trigger type."""
        return retention.summarize_coach_engagement(
            store, lookback_days=lookback_days
        )

    @server.tool()
    @audit.audited
    def sample_workout_inputs(
        start_date: str | None = None,
        end_date: str | None = None,
        user_tag: str | None = None,
        limit: int = 20,
    ) -> cohort.WorkoutSamplesResult:
        """Return recent samples of users' raw workout text with context
        (user tag, date, session id). Filter by ISO date range, an optional
        user_tag, and limit. Useful for seeing how users phrase their logs."""
        return cohort.sample_workout_inputs(
            store,
            start_date=start_date,
            end_date=end_date,
            user_tag=user_tag,
            limit=limit,
        )

    @server.tool()
    @audit.audited
    def describe_user_base(
        lookback_days: int = 90,
    ) -> cohort.UserBaseSummary:
        """Cohort-level behavioural aggregates across active users: muscle
        group mix, top exercises, compound/isolation ratio, equipment
        breakdown, average reps, goal and experience-level distributions.
        Adds an LLM cohort synthesis when OPENROUTER_API_KEY is configured."""
        return cohort.describe_user_base(
            store, lookback_days=lookback_days, llm=llm
        )

    @server.prompt(
        name="investigate-quiet-user",
        title="Investigate a quiet user",
        description="Guided workflow for diagnosing why a user went quiet.",
    )
    def investigate_quiet_user(user_tag: str) -> str:
        """Chain investigate_user with retention signals to explain churn."""
        return (
            f"Investigate why Rep AI user `{user_tag}` may have gone quiet.\n\n"
            "Follow these steps:\n"
            f"1. Call `investigate_user` with user_tag=\"{user_tag}\" to get the "
            "full digest: onboarding intent, workout history, behavioural "
            "signals, coach engagement, and (if enabled) LLM persona.\n"
            "2. Compare their stated commitment / weekly_target against "
            "`workouts.days_since_last_workout` and recent activity. Call "
            "`find_commitment_gaps` and `find_trial_dropoff_risk` to see whether "
            "they surface in those at-risk cohorts.\n"
            "3. Inspect `coach_engagement` — were proactive coach messages sent "
            "but not consumed? Low consumption alongside inactivity suggests "
            "disengagement rather than a one-off gap.\n"
            "4. Synthesise a short hypothesis for why they went quiet and a "
            "concrete next action (e.g. a re-engagement nudge). Consider logging "
            "it with `create_ops_note`.\n\n"
            "Ground every claim in the returned data; do not speculate beyond it."
        )

    @server.prompt(
        name="understand-user-base",
        title="Understand the user base",
        description="Guided workflow for characterising who uses Rep AI.",
    )
    def understand_user_base() -> str:
        """Chain describe_user_base with raw samples for cohort understanding."""
        return (
            "Build a grounded picture of what kinds of gym goers use Rep AI.\n\n"
            "Follow these steps:\n"
            "1. Call `describe_user_base` for cohort aggregates: muscle group "
            "mix, top exercises, compound/isolation ratio, equipment breakdown, "
            "average reps, plus goal and experience-level distributions. If "
            "OPENROUTER_API_KEY is configured it also returns an LLM `synthesis`.\n"
            "2. Call `sample_workout_inputs` (e.g. limit=15) to read how users "
            "actually phrase their workouts in their own words.\n"
            "3. Reconcile the qualitative samples with the quantitative signals: "
            "do the raw logs match the dominant personas implied by the "
            "aggregates?\n"
            "4. Summarise 2-4 distinct user archetypes with the signals that "
            "characterise each. Ground every claim in the returned numbers and "
            "samples."
        )

    return server


def main() -> None:
    load_dotenv()
    config = load_config()
    server = create_server(config)
    server.run()


if __name__ == "__main__":
    main()

"""Derive a user's weekly workout target from their stated commitment.

Rep AI stores commitment two mutually-exclusive ways (see migrations
20251218120000 and 20260318120000):

- ``commitment``: text[] of weekday names, e.g. ['monday','wednesday','friday'],
  or ['not_sure'].
- ``commitment_frequency``: one of '1_time'..'4_times', '5_plus', 'not_sure'.

Both may be null/absent if the user skipped onboarding commitment.
"""

from __future__ import annotations

_WEEKDAYS = frozenset(
    {
        "sunday",
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
    }
)

_FREQUENCY_TARGETS = {
    "1_time": 1,
    "2_times": 2,
    "3_times": 3,
    "4_times": 4,
    "5_plus": 5,
}


def weekly_target_from_profile(
    commitment: list[str] | None,
    commitment_frequency: str | None,
) -> int | None:
    """Return the user's intended workouts-per-week, or None if unknown.

    'not_sure' (in either form) yields None — the user expressed no target.
    """
    if commitment:
        days = {d.lower() for d in commitment} & _WEEKDAYS
        if days:
            return len(days)
        return None

    if commitment_frequency:
        return _FREQUENCY_TARGETS.get(commitment_frequency.lower())

    return None

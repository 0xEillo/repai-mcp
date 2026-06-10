from repai_mcp.queries.commitment import weekly_target_from_profile


def test_target_from_day_array():
    assert weekly_target_from_profile(["monday", "wednesday", "friday"], None) == 3


def test_target_from_day_array_dedupes_and_ignores_invalid():
    assert weekly_target_from_profile(["Monday", "monday", "not_sure"], None) == 1


def test_target_from_not_sure_days_is_none():
    assert weekly_target_from_profile(["not_sure"], None) is None


def test_target_from_frequency():
    assert weekly_target_from_profile(None, "4_times") == 4
    assert weekly_target_from_profile(None, "5_plus") == 5
    assert weekly_target_from_profile(None, "1_time") == 1


def test_target_from_frequency_not_sure_is_none():
    assert weekly_target_from_profile(None, "not_sure") is None


def test_no_commitment_is_none():
    assert weekly_target_from_profile(None, None) is None


def test_day_array_takes_precedence_over_frequency():
    assert weekly_target_from_profile(["monday", "tuesday"], "5_plus") == 2

from app.api.endpoints.contribution import _as_numeric


def test_contribution_as_numeric_returns_default_for_non_numeric():
    assert _as_numeric("not-a-number", default=3) == 3

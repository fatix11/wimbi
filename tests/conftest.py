import pytest

from analytics_mirror.seed_data import ensure_tables_exist, seed


@pytest.fixture
def mirror_data(db):
    """Creates the unmanaged analytics_mirror tables in the test DB (they're
    managed=False so Django's migrate/test-DB setup never creates them) and
    seeds the same fixture dataset the seed_mock_analytics_mirror command
    uses for local dev."""
    ensure_tables_exist()
    seed()

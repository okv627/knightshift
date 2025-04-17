import pytest
from src.utils.db_utils import get_database_url, get_lichess_token

def test_get_database_url():
    fake_creds = {
        "PGHOST": "localhost",
        "PGPORT": "5432",
        "PGDATABASE": "test_db",
        "PGUSER": "test_user",
        "PGPASSWORD": "test_pass",
    }
    url = get_database_url(fake_creds)
    assert url == "postgresql+pg8000://test_user:test_pass@localhost:5432/test_db"


def test_get_database_url_missing_fields():
    incomplete_creds = {
        "PGHOST": "localhost",
        "PGDATABASE": "test_db",
        # PGPORT missing; should default to '5432'
        "PGUSER": "user",
        "PGPASSWORD": "pass",
    }
    url = get_database_url(incomplete_creds)
    # Assert that the default port '5432' is in the URL
    assert "5432" in url


def test_get_lichess_token(monkeypatch):
    # Set the environment variable for the test
    monkeypatch.setenv("LICHESS_TOKEN", "test_token")
    token = get_lichess_token()
    assert token == "test_token"

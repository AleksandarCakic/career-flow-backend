import pytest

from app.core.config import Settings


@pytest.mark.unit
def test_database_url_rewrites_bare_postgresql_scheme() -> None:
    settings = Settings(database_url="postgresql://user:pw@host:5432/db")
    assert settings.database_url == "postgresql+asyncpg://user:pw@host:5432/db"


@pytest.mark.unit
def test_database_url_rewrites_legacy_postgres_scheme() -> None:
    settings = Settings(database_url="postgres://user:pw@host:5432/db")
    assert settings.database_url == "postgresql+asyncpg://user:pw@host:5432/db"


@pytest.mark.unit
def test_database_url_passes_through_explicit_asyncpg() -> None:
    settings = Settings(database_url="postgresql+asyncpg://user:pw@host:5432/db")
    assert settings.database_url == "postgresql+asyncpg://user:pw@host:5432/db"


@pytest.mark.unit
def test_database_url_passes_through_other_explicit_driver() -> None:
    settings = Settings(database_url="postgresql+psycopg://user:pw@host:5432/db")
    assert settings.database_url == "postgresql+psycopg://user:pw@host:5432/db"

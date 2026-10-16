import pytest
from alembic.config import Config
from sqlalchemy.engine import make_url

from app.database import (
    get_database_url,
    make_engine,
    render_database_url_for_alembic,
)


def test_database_defaults_to_sqlite_only_without_production_configuration():
    url = get_database_url({})
    assert url.drivername == "sqlite"
    assert url.database == "./audit.db"


def test_partial_postgres_configuration_fails_instead_of_falling_back_to_sqlite():
    with pytest.raises(ValueError, match="PostgreSQL configuration is incomplete"):
        get_database_url({"POSTGRES_USER": "privacy_audit"})


def test_production_without_database_configuration_fails_instead_of_using_sqlite():
    with pytest.raises(ValueError, match="required when APP_ENV is production"):
        get_database_url({"APP_ENV": "production"})


def test_database_url_and_postgres_variables_cannot_conflict():
    env = {
        "DATABASE_URL": "postgresql+psycopg://privacy_audit:synthetic%40secret@db/privacy_audit",
        "POSTGRES_DB": "privacy_audit",
        "POSTGRES_USER": "privacy_audit",
        "POSTGRES_PASSWORD": "synthetic-secret",
    }
    with pytest.raises(ValueError, match="not both"):
        get_database_url(env)


def test_postgres_password_with_url_special_characters_is_encoded_and_round_trips():
    password = "synthetic p@ss:/?#%+word"
    env = {
        "POSTGRES_DB": "privacy_audit",
        "POSTGRES_USER": "privacy_audit",
        "POSTGRES_PASSWORD": password,
        "POSTGRES_HOST": "db",
        "POSTGRES_PORT": "5432",
    }

    url = get_database_url(env)
    engine = make_engine(url)
    try:
        assert engine.url.password == password
        rendered = render_database_url_for_alembic(env)
        assert password not in rendered
        alembic_config = Config()
        alembic_config.set_main_option("sqlalchemy.url", rendered.replace("%", "%%"))
        parsed_by_alembic_config = make_url(alembic_config.get_main_option("sqlalchemy.url"))
        assert parsed_by_alembic_config.password == password
        assert parsed_by_alembic_config.host == engine.url.host == "db"
        assert parsed_by_alembic_config.database == engine.url.database == "privacy_audit"
    finally:
        engine.dispose()


def test_explicit_encoded_database_url_is_parsed_as_a_sqlalchemy_url():
    url = get_database_url({
        "DATABASE_URL": "postgresql+psycopg://privacy_audit:synthetic%40secret@db:5432/privacy_audit"
    })
    assert url.drivername == "postgresql+psycopg"
    assert url.password == "synthetic@secret"
    assert url.host == "db"

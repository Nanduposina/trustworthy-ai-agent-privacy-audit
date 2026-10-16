"""Database configuration shared by the API and Alembic migrations."""

import os
from collections.abc import Mapping

from sqlalchemy import URL, create_engine, make_url
from sqlalchemy.exc import ArgumentError
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


POSTGRES_VARIABLES = ("POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_HOST", "POSTGRES_PORT")
REQUIRED_POSTGRES_VARIABLES = ("POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD")


def get_database_url(environ: Mapping[str, str] | None = None) -> URL:
    """Return one normalized URL shared by the API and Alembic.

    PostgreSQL settings and DATABASE_URL are mutually exclusive so a hidden
    override cannot make the API and migration target different credentials.
    SQLite remains the default only when no production DB configuration is set.
    """
    settings = os.environ if environ is None else environ
    configured_postgres = any(name in settings for name in POSTGRES_VARIABLES)
    explicit_url = settings.get("DATABASE_URL")

    if explicit_url is not None:
        if not explicit_url.strip():
            raise ValueError("DATABASE_URL is set but empty.")
        if configured_postgres:
            raise ValueError("Set DATABASE_URL or POSTGRES_* variables, not both.")
        try:
            return make_url(explicit_url)
        except ArgumentError as exc:
            raise ValueError("DATABASE_URL must be a valid SQLAlchemy URL.") from exc

    if configured_postgres:
        missing = [name for name in REQUIRED_POSTGRES_VARIABLES if not settings.get(name)]
        if missing:
            raise ValueError(
                "PostgreSQL configuration is incomplete; set POSTGRES_DB, "
                "POSTGRES_USER, and POSTGRES_PASSWORD."
            )
        return URL.create(
            "postgresql+psycopg",
            username=settings["POSTGRES_USER"],
            password=settings["POSTGRES_PASSWORD"],
            host=settings.get("POSTGRES_HOST", "localhost"),
            port=int(settings.get("POSTGRES_PORT", "5432")),
            database=settings["POSTGRES_DB"],
        )

    if settings.get("APP_ENV", "").lower() in {"prod", "production"}:
        raise ValueError("PostgreSQL settings are required when APP_ENV is production.")

    return make_url(settings.get("AUDIT_SQLITE_PATH", "sqlite:///./audit.db"))


def render_database_url_for_alembic(environ: Mapping[str, str] | None = None) -> str:
    """Render the shared URL with credentials encoded for Alembic's config parser."""
    return get_database_url(environ).render_as_string(hide_password=False)


def make_engine(url: str | URL | None = None):
    database_url = url or get_database_url()
    options = {"pool_pre_ping": True}
    drivername = database_url.drivername if isinstance(database_url, URL) else str(database_url).split(":", 1)[0]
    if drivername.startswith("sqlite"):
        options["connect_args"] = {"check_same_thread": False}
    return create_engine(database_url, **options)


engine = make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

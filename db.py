import os
from dotenv import load_dotenv
load_dotenv()

import psycopg2
from psycopg2.extras import RealDictCursor
from sqlalchemy import create_engine
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def _normalize_database_url(database_url: str) -> str:
    if not database_url.startswith("postgres"):
        return database_url

    split_url = urlsplit(database_url)
    query_params = dict(parse_qsl(split_url.query, keep_blank_values=True))

    if query_params.get("sslmode") == "verify-full":
        query_params["sslmode"] = "require"

    return urlunsplit(
        (
            split_url.scheme,
            split_url.netloc,
            split_url.path,
            urlencode(query_params),
            split_url.fragment,
        )
    )


# Primary DB URL (from .env or environment)
DATABASE_URL = _normalize_database_url(os.getenv("DATABASE_URL", "sqlite:///./agent.db"))

# Lazy-created SQLAlchemy engine
_engine = None


def get_engine():
    """Return a SQLAlchemy engine for the configured DATABASE_URL."""
    global _engine
    if _engine is None:
        if DATABASE_URL.startswith("sqlite"):
            _engine = create_engine(
                DATABASE_URL, connect_args={"check_same_thread": False}
            )
        else:
            _engine = create_engine(DATABASE_URL)
    return _engine


def get_connection():
    """Return a raw psycopg2 connection (RealDictCursor) using DATABASE_URL.

    Useful for code that expects DB-API connections.
    """
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
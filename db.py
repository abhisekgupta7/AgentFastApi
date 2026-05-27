import os
from dotenv import load_dotenv
load_dotenv()

import psycopg2
from psycopg2.extras import RealDictCursor
from sqlalchemy import create_engine


# Primary DB URL (from .env or environment)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./agent.db")

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
    return psycopg2.connect(os.environ["DATABASE_URL"], cursor_factory=RealDictCursor)
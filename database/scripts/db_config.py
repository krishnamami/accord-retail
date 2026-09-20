#!/usr/bin/env python3
"""
Single source of database configuration for every script in this repo.

Credentials are NEVER hard-coded. DATABASE_URL is read from the environment,
falling back to the repo-root .env file (which is git-ignored).

Usage:
    from db_config import connect, get_database_url, redacted_url
    conn = connect()
"""
import os
import re
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
_ASYNC_PREFIX = "postgresql+asyncpg://"


def get_database_url() -> str:
    """Return a psycopg2-compatible DSN, loading .env if DATABASE_URL is not already set."""
    if not os.getenv("DATABASE_URL"):
        load_dotenv(REPO_ROOT / ".env")
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set. Copy .env.example to .env and set DATABASE_URL "
            "(never commit credentials to source control)."
        )
    if url.startswith(_ASYNC_PREFIX):
        url = "postgresql://" + url[len(_ASYNC_PREFIX):]
    return url


def redacted_url(url: str | None = None) -> str:
    """DSN with the password masked, safe for logs."""
    url = url or get_database_url()
    return re.sub(r"(://[^:/@]+:)[^@]*@", r"\1****@", url)


def connect(**kwargs) -> psycopg2.extensions.connection:
    """Open a psycopg2 connection using DATABASE_URL."""
    kwargs.setdefault("connect_timeout", 20)
    return psycopg2.connect(get_database_url(), **kwargs)

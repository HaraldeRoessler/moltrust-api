"""Test fixtures — load secrets from .moltrust_secrets, provide DB connection."""
import os
import pytest
import pytest_asyncio
import asyncpg
import sys

# Load secrets so MOLTRUST_REGISTRY_PRIVATE_KEY is in env BEFORE app modules import
SECRETS = "/home/moltstack/.moltrust_secrets"
if os.path.exists(SECRETS):
    for line in open(SECRETS):
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k, v.strip('"').strip("'"))

# Make app importable
sys.path.insert(0, "/home/moltstack/moltstack")


@pytest_asyncio.fixture
async def test_db():
    """Live DB connection, cleaned up after test (deletes any caep_events with did starting did:moltrust:test_)."""
    conn = await asyncpg.connect(
        host="localhost",
        database=os.getenv("DB_NAME", "moltstack"),
        user="moltstack",
    )
    # Pre-clean (in case prior failed test left rows)
    await conn.execute(
        "DELETE FROM caep_events WHERE did LIKE 'did:moltrust:test_%'"
    )
    try:
        yield conn
    finally:
        # Post-clean
        await conn.execute(
            "DELETE FROM caep_events WHERE did LIKE 'did:moltrust:test_%'"
        )
        await conn.close()

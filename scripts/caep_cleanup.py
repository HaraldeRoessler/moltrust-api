#!/usr/bin/env python3
"""Nightly hard-delete of acknowledged CAEP events older than retention window.

Run via cron (see /etc/cron.d/moltstack-caep-cleanup).
Reads .moltrust_secrets for DB env. Logs to stdout.
"""
import asyncio
import asyncpg
import os
import sys

# Load secrets so MOLTRUST_REGISTRY_PRIVATE_KEY etc. are visible (not strictly required here,
# but keeps script consistent with service env).
SECRETS = "/home/moltstack/.moltrust_secrets"
if os.path.exists(SECRETS):
    for line in open(SECRETS):
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k, v.strip('"').strip("'"))

sys.path.insert(0, "/home/moltstack/moltstack")
from app.caep import cleanup_acknowledged_events

RETENTION_DAYS = int(os.environ.get("CAEP_RETENTION_DAYS", "90"))


async def main():
    conn = await asyncpg.connect(
        host="localhost",
        database=os.getenv("DB_NAME", "moltstack"),
        user="moltstack",
    )
    try:
        deleted = await cleanup_acknowledged_events(conn, retention_days=RETENTION_DAYS)
        print(f"caep_cleanup: deleted {deleted} acknowledged events older than {RETENTION_DAYS}d")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""Run Revenue Health against all prepared business contexts.

Usage:
  export DATABASE_URL='postgresql://user:password@host:5432/database'
  python scripts/run_revenue_health.py

Requires psycopg (v3) or psycopg2.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from domains.retail.agents.revenue_health.agent import run

SQL = """
SELECT *
FROM agent.revenue_health_context
ORDER BY business_name
"""


def _connect(database_url: str):
    try:
        import psycopg
        return psycopg.connect(database_url)
    except ImportError:
        try:
            import psycopg2
            return psycopg2.connect(database_url)
        except ImportError as exc:
            raise RuntimeError("Install psycopg or psycopg2 to run this script") from exc


def _rows(conn) -> list[dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(SQL)
        columns = [d.name if hasattr(d, "name") else d[0] for d in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]


def _json_default(value: Any):
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def main() -> int:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL is required", file=sys.stderr)
        return 2

    with _connect(database_url) as conn:
        rows = _rows(conn)

    packages = [run(row) for row in rows]

    print("\nRevenue Health validation\n")
    print(f"{'Business':28} {'Decision':20} {'Severity':8} {'Boundary':28} Rules Fired")
    print("-" * 120)
    for p in packages:
        fired = ",".join(r["rule_id"] for r in p["rules_fired"]) or "-"
        print(f"{p['business_name'][:28]:28} {p['decision'][:20]:20} {p['severity']:8} {p['boundary']['status'][:28]:28} {fired}")

    print("\nFull decision packages\n")
    print(json.dumps(packages, indent=2, default=_json_default))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

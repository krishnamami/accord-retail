#!/usr/bin/env python3
"""Run Margin Health against prepared product/month contexts."""
import json,os,sys
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from domains.retail.agents.margin_health.agent import run
SQL="""SELECT * FROM agent.margin_health_context ORDER BY product_name, period_start"""
def connect(url):
    import psycopg
    return psycopg.connect(url)
def rows(conn):
    with conn.cursor() as cur:
        cur.execute(SQL); cols=[d.name if hasattr(d,'name') else d[0] for d in cur.description]
        return [dict(zip(cols,r)) for r in cur.fetchall()]
def default(v): return v.isoformat() if hasattr(v,'isoformat') else str(v)
def main():
    url=os.environ.get('DATABASE_URL')
    if not url: print('ERROR: DATABASE_URL is required',file=sys.stderr); return 2
    with connect(url) as conn: data=rows(conn)
    packages=[run(r) for r in data]
    print('\nMargin Health validation\n')
    print(f"{'Product':22} {'Period':10} {'Decision':28} {'Severity':8} {'Boundary':26} Rules Fired")
    print('-'*125)
    for p in packages:
        fired=','.join(r['rule_id'] for r in p['rules_fired']) or '-'; period=str(p['context']['period_start'])
        print(f"{p['product_name'][:22]:22} {period[:10]:10} {p['decision'][:28]:28} {p['severity']:8} {p['boundary']['status'][:26]:26} {fired}")
    print('\nFull decision packages\n'); print(json.dumps(packages,indent=2,default=default)); return 0
if __name__=='__main__': raise SystemExit(main())

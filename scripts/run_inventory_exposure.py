#!/usr/bin/env python3
"""Run Inventory Exposure against all prepared product contexts."""
import json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from domains.retail.agents.inventory_exposure.agent import run
SQL='SELECT * FROM agent.inventory_exposure_context ORDER BY business_name, product_name'
def default(v): return v.isoformat() if hasattr(v,'isoformat') else str(v)
def main():
    import psycopg
    url=os.environ.get('DATABASE_URL')
    if not url: print('ERROR: DATABASE_URL is required',file=sys.stderr); return 2
    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            cur.execute(SQL); cols=[d.name if hasattr(d,'name') else d[0] for d in cur.description]; rows=[dict(zip(cols,r)) for r in cur.fetchall()]
    packages=[run(r) for r in rows]
    print('\nInventory Exposure validation\n')
    print(f"{'Business':20} {'Product':16} {'Decision':24} {'Severity':8} {'DaysSupply':10} {'InvValue':12} Rules Fired")
    print('-'*125)
    for p in packages:
        fired=','.join(r['rule_id'] for r in p['rules_fired']) or '-'; c=p['context']; ds='-' if c['days_of_supply'] is None else f"{c['days_of_supply']:.1f}"; iv='-' if c['inventory_value'] is None else f"{c['inventory_value']:.2f}"
        print(f"{p['business_name'][:20]:20} {p['product_name'][:16]:16} {p['decision'][:24]:24} {p['severity']:8} {ds:10} {iv:12} {fired}")
    from collections import Counter
    print('\nDecision counts:')
    for k,v in sorted(Counter(p['decision'] for p in packages).items()): print(f'  {k}: {v}')
    print('\nFull decision packages\n'); print(json.dumps(packages,indent=2,default=default)); return 0
if __name__=='__main__': raise SystemExit(main())

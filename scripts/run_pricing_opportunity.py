#!/usr/bin/env python3
"""Run Pricing Opportunity across prepared product contexts."""
import os,sys
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from domains.retail.agents.pricing_opportunity.agent import run
SQL="SELECT * FROM agent.pricing_opportunity_context ORDER BY business_id,product_id"
def main():
    import psycopg
    url=os.environ.get("DATABASE_URL")
    if not url: print("ERROR: DATABASE_URL is required",file=sys.stderr); return 2
    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            cur.execute(SQL); cols=[d.name if hasattr(d,"name") else d[0] for d in cur.description]; rows=[dict(zip(cols,r)) for r in cur.fetchall()]
    packages=[run(r) for r in rows]
    counts=Counter(p["decision"] for p in packages)
    print("\nPricing Opportunity decision counts:")
    for k,v in sorted(counts.items()): print(f"  {k}: {v}")
    print("\nSample decisions by class:")
    seen=Counter()
    for p in packages:
        if seen[p["decision"]]>=3: continue
        c=p["context"]; fired=",".join(r["rule_id"] for r in p["rules_fired"]) or "-"
        print(f"{p['decision']:24} severity={p['severity']:7} product={c['product_name']} realized={c['realized_unit_price']} competitor={c['competitor_price']} gap={c['competitor_price_gap_pct']} margin={c['realized_gross_margin_pct']} competitor_status={c['competitor_evidence_status']} rules={fired}")
        seen[p["decision"]]+=1
    print(f"\nTotal evaluated: {len(packages)}")
    return 0
if __name__=="__main__": raise SystemExit(main())

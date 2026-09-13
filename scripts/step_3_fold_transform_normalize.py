#!/usr/bin/env python3
import psycopg2
import sys

DB_CONFIG = {
    "host": "database-1.c1qseu4kq079.us-west-2.rds.amazonaws.com",
    "port": 5432,
    "database": "accord_retail",
    "user": "postgres",
    "password": "Sharanya87$"
}

def main():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        print("\n" + "="*70)
        print("STEP 3: FOLD, TRANSFORM & NORMALIZE")
        print("="*70)
        cursor.execute("DELETE FROM processed.processed_upload;")
        sql = """
        INSERT INTO processed.processed_upload (
            processed_id, business_id, upload_id, revenue_monthly, customer_count, 
            repeat_count, churn_count, repeat_rate, churn_rate, 
            customer_lifetime_value, customer_acquisition_cost, product_margin, 
            inventory_turnover, slow_moving_inventory_pct, confidence_score, 
            processed_at, processed_by, observation_period_start, observation_period_end
        )
        SELECT 
            gen_random_uuid(), b.business_id, (SELECT upload_id FROM raw.raw_upload WHERE business_id = b.business_id LIMIT 1),
            COALESCE(SUM(s.revenue), 0),
            COUNT(DISTINCT s.customer_id),
            COUNT(DISTINCT CASE WHEN c.repeat_count > 0 THEN s.customer_id END),
            COUNT(DISTINCT CASE WHEN c.churn_status = 'churned' THEN s.customer_id END),
            ROUND(COALESCE(COUNT(DISTINCT CASE WHEN c.repeat_count > 0 THEN s.customer_id END)::numeric / NULLIF(COUNT(DISTINCT s.customer_id), 0), 0), 4),
            ROUND(COALESCE(COUNT(DISTINCT CASE WHEN c.churn_status = 'churned' THEN s.customer_id END)::numeric / NULLIF(COUNT(DISTINCT s.customer_id), 0), 0), 4),
            ROUND(COALESCE(SUM(s.revenue), 0) / NULLIF(COUNT(DISTINCT s.customer_id), 0), 2),
            ROUND(COALESCE(SUM(s.revenue), 0) * 0.15 / NULLIF(COUNT(DISTINCT s.customer_id), 0), 2),
            ROUND(COALESCE((SUM(s.revenue) - SUM(COALESCE(p.cogs * s.quantity, 0))) / NULLIF(SUM(s.revenue), 0), 0), 2),
            ROUND(COALESCE(SUM(s.revenue) / NULLIF(SUM(COALESCE(inv.quantity_on_hand, 1)), 0), 0), 2),
            ROUND(COALESCE(COUNT(DISTINCT CASE WHEN inv.quantity_on_hand > inv.reorder_point * 2 THEN inv.inventory_id END)::numeric / NULLIF(COUNT(DISTINCT inv.inventory_id), 0), 0) * 50, 2),
            8.50,
            NOW(), 'pipeline', MIN(s.sale_date), MAX(s.sale_date)
        FROM runtime.business b
        LEFT JOIN runtime.sale s ON b.business_id = s.business_id
        LEFT JOIN runtime.customer c ON s.customer_id = c.customer_id
        LEFT JOIN runtime.product p ON s.product_id = p.product_id
        LEFT JOIN runtime.inventory inv ON b.business_id = inv.business_id
        GROUP BY b.business_id;
        """
        cursor.execute(sql)
        conn.commit()
        cursor.execute("SELECT COUNT(*) FROM processed.processed_upload;")
        count = cursor.fetchone()[0]
        print(f"✅ Transformed {count} business records")
        print(f"   └─ Table: processed.processed_upload")
        print(f"   └─ Records: {count}")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"❌ Step 3 failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

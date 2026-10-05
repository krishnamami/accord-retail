-- Accord Retail: Inventory Exposure agent preparation
-- Prepares transparent inventory/demand/financial context signals.
-- These are context signals only; final decisions and governed thresholds live in the agent.
-- Freshness is evaluated against the business data horizon, not wall-clock CURRENT_DATE.
CREATE SCHEMA IF NOT EXISTS agent;

DROP VIEW IF EXISTS agent.inventory_exposure_context;

CREATE OR REPLACE VIEW agent.inventory_exposure_context AS
WITH anchor AS (
    SELECT business_id, MAX(sale_date)::date AS data_as_of
    FROM runtime.sale
    GROUP BY business_id
),
velocity AS (
    SELECT
        s.business_id,
        s.product_id,
        a.data_as_of,
        MAX(s.sale_date)::date AS latest_sale_date,
        SUM(COALESCE(s.quantity,0)) FILTER (
            WHERE s.sale_date::date > a.data_as_of - 90
              AND s.sale_date::date <= a.data_as_of
        ) AS units_90d,
        SUM(COALESCE(s.quantity,0)) FILTER (
            WHERE s.sale_date::date > a.data_as_of - 30
              AND s.sale_date::date <= a.data_as_of
        ) AS units_30d
    FROM runtime.sale s
    JOIN anchor a ON a.business_id = s.business_id
    GROUP BY s.business_id, s.product_id, a.data_as_of
),
base AS (
    SELECT
        i.business_id,
        b.name AS business_name,
        i.product_id,
        p.name AS product_name,
        p.category,
        i.quantity_on_hand,
        i.reorder_point,
        i.last_updated,
        p.cogs,
        p.list_price,
        v.data_as_of,
        v.latest_sale_date,
        ROUND(i.quantity_on_hand * COALESCE(p.cogs,0),2) AS inventory_value,
        v.units_30d,
        v.units_90d,
        ROUND(v.units_90d / 90.0,4) AS daily_sales_velocity_90d,
        ROUND(i.quantity_on_hand / NULLIF(v.units_90d / 90.0,0),2) AS days_of_supply,
        (i.quantity_on_hand - i.reorder_point) AS reorder_gap_units,
        CASE WHEN i.quantity_on_hand <= i.reorder_point THEN TRUE ELSE FALSE END AS at_or_below_reorder,
        CASE
            WHEN v.units_90d IS NULL THEN NULL
            WHEN v.units_90d = 0 THEN 'NO_MOVEMENT'
            WHEN v.units_90d <= 10 THEN 'VERY_LOW'
            WHEN v.units_90d <= 30 THEN 'LOW'
            WHEN v.units_90d <= 90 THEN 'MODERATE'
            ELSE 'HIGH'
        END AS velocity_band
    FROM runtime.inventory i
    JOIN runtime.product p
      ON p.product_id = i.product_id
     AND p.business_id = i.business_id
    JOIN runtime.business b
      ON b.business_id = i.business_id
    LEFT JOIN velocity v
      ON v.business_id = i.business_id
     AND v.product_id = i.product_id
),
signals AS (
    SELECT
        base.*,
        CASE
            WHEN days_of_supply IS NULL THEN 'UNKNOWN'
            WHEN days_of_supply >= 365 THEN 'EXTREME'
            WHEN days_of_supply >= 180 THEN 'HIGH'
            WHEN days_of_supply >= 90 THEN 'ELEVATED'
            ELSE 'NORMAL'
        END AS supply_band,
        CASE
            WHEN quantity_on_hand > 0
             AND days_of_supply >= 180
            THEN TRUE ELSE FALSE
        END AS excess_supply_candidate,
        CASE
            WHEN quantity_on_hand > 0
             AND days_of_supply >= 180
             AND COALESCE(units_90d,0) <= 30
            THEN TRUE ELSE FALSE
        END AS slow_moving_candidate,
        CASE
            WHEN quantity_on_hand > 0
             AND days_of_supply >= 180
             AND inventory_value >= 25000
            THEN TRUE ELSE FALSE
        END AS capital_exposure_candidate,
        CASE
            WHEN last_updated IS NULL THEN 'MISSING_INVENTORY_TIMESTAMP'
            WHEN last_updated::date < data_as_of - 7 THEN 'STALE_INVENTORY'
            ELSE 'READY'
        END AS inventory_freshness_status,
        CASE
            WHEN data_as_of IS NULL THEN 'MISSING_DATA_HORIZON'
            WHEN units_90d IS NULL THEN 'INSUFFICIENT_HISTORY'
            WHEN quantity_on_hand IS NULL OR reorder_point IS NULL THEN 'MISSING_INVENTORY_POSITION'
            WHEN last_updated IS NULL THEN 'MISSING_INVENTORY_TIMESTAMP'
            WHEN last_updated::date < data_as_of - 7 THEN 'STALE_INVENTORY'
            ELSE 'READY'
        END AS inventory_evidence_status
    FROM base
)
SELECT
    business_id,
    business_name,
    product_id,
    product_name,
    category,
    quantity_on_hand,
    reorder_point,
    last_updated,
    cogs,
    list_price,
    data_as_of,
    latest_sale_date,
    inventory_value,
    units_30d,
    units_90d,
    daily_sales_velocity_90d,
    days_of_supply,
    reorder_gap_units,
    at_or_below_reorder,
    velocity_band,
    supply_band,
    excess_supply_candidate,
    slow_moving_candidate,
    capital_exposure_candidate,
    inventory_freshness_status,
    inventory_evidence_status
FROM signals;

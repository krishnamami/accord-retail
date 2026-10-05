-- Accord Retail: Customer Retention agent preparation
-- Separates observed transaction evidence from profile assertions.
-- Missing observations remain NULL; zero is reserved for an observed zero.
-- Prepared signals are context only; final decisions belong to the governed agent.
CREATE SCHEMA IF NOT EXISTS agent;

DROP VIEW IF EXISTS agent.customer_retention_business;
DROP VIEW IF EXISTS agent.customer_retention_context;

CREATE OR REPLACE VIEW agent.customer_retention_context AS
WITH anchor AS (
    SELECT business_id, MAX(sale_date)::date AS data_as_of
    FROM runtime.sale
    GROUP BY business_id
),
observed AS (
    SELECT
        c.business_id,
        c.customer_id,
        COUNT(s.sale_id)::int AS observed_orders,
        CASE WHEN COUNT(s.sale_id)=0 THEN NULL ELSE SUM(s.revenue)::numeric(15,2) END AS observed_revenue,
        MIN(s.sale_date)::date AS observed_first_purchase,
        MAX(s.sale_date)::date AS observed_last_purchase
    FROM runtime.customer c
    LEFT JOIN runtime.sale s
      ON s.business_id=c.business_id
     AND s.customer_id=c.customer_id
    GROUP BY c.business_id,c.customer_id
),
base AS (
    SELECT
        c.business_id,
        c.customer_id,
        c.acquisition_channel,
        c.first_purchase_date AS profile_first_purchase,
        c.last_purchase_date AS profile_last_purchase,
        c.repeat_count AS profile_repeat_count,
        c.churn_status AS asserted_churn_status,
        o.observed_orders,
        o.observed_revenue,
        o.observed_first_purchase,
        o.observed_last_purchase,
        a.data_as_of,
        (o.observed_orders > 0) AS behavioral_evidence_available,
        CASE
            WHEN o.observed_last_purchase IS NULL THEN NULL
            ELSE (a.data_as_of-o.observed_last_purchase)
        END AS observed_recency_days,
        CASE
            WHEN c.last_purchase_date IS NULL THEN NULL
            ELSE (a.data_as_of-c.last_purchase_date::date)
        END AS profile_recency_days,
        CASE
            WHEN o.observed_orders=0 THEN NULL
            WHEN o.observed_orders=1 THEN FALSE
            ELSE TRUE
        END AS observed_repeat_customer,
        CASE
            WHEN o.observed_orders=0 THEN NULL
            ELSE ROUND(o.observed_orders / NULLIF(GREATEST(1,(o.observed_last_purchase-o.observed_first_purchase)+1),0)::numeric,4)
        END AS observed_orders_per_day,
        CASE
            WHEN o.observed_orders=0 THEN NULL
            WHEN o.observed_last_purchase >= a.data_as_of-90 THEN 'ACTIVE'
            WHEN o.observed_last_purchase >= a.data_as_of-180 THEN 'DORMANT'
            ELSE 'CHURNED'
        END AS observed_behavior_status,
        CASE
            WHEN c.last_purchase_date IS NULL THEN 'UNKNOWN'
            WHEN c.last_purchase_date::date >= a.data_as_of-90 THEN 'ACTIVE'
            WHEN c.last_purchase_date::date >= a.data_as_of-180 THEN 'DORMANT'
            ELSE 'CHURNED'
        END AS profile_behavior_status
    FROM runtime.customer c
    JOIN anchor a ON a.business_id=c.business_id
    JOIN observed o ON o.business_id=c.business_id AND o.customer_id=c.customer_id
),
validated AS (
    SELECT
        base.*,
        CASE
            WHEN observed_orders=0 THEN FALSE
            WHEN UPPER(COALESCE(asserted_churn_status,'')) IN ('ACTIVE','DORMANT','CHURNED')
             AND UPPER(asserted_churn_status) <> observed_behavior_status THEN TRUE
            ELSE FALSE
        END AS assertion_conflict,
        CASE
            WHEN observed_orders=0 THEN 'NO_OBSERVED_TRANSACTION_EVIDENCE'
            WHEN UPPER(COALESCE(asserted_churn_status,'')) NOT IN ('ACTIVE','DORMANT','CHURNED') THEN 'UNRECOGNIZED_PROFILE_ASSERTION'
            WHEN UPPER(asserted_churn_status) <> observed_behavior_status THEN
                'PROFILE_'||UPPER(asserted_churn_status)||'_VS_OBSERVED_'||observed_behavior_status
            ELSE NULL
        END AS conflict_reason,
        CASE
            WHEN observed_orders=0 THEN 'PROFILE_ONLY_NO_OBSERVED_SALES'
            WHEN observed_last_purchase IS NULL THEN 'INSUFFICIENT_HISTORY'
            ELSE 'READY'
        END AS retention_evidence_status
    FROM base
)
SELECT
    business_id,
    customer_id,
    acquisition_channel,
    profile_first_purchase,
    profile_last_purchase,
    profile_repeat_count,
    asserted_churn_status,
    observed_orders,
    observed_revenue,
    observed_first_purchase,
    observed_last_purchase,
    data_as_of,
    behavioral_evidence_available,
    observed_recency_days AS recency_days,
    profile_recency_days,
    observed_repeat_customer AS repeat_customer,
    observed_orders_per_day,
    observed_behavior_status,
    profile_behavior_status,
    assertion_conflict,
    conflict_reason,
    CASE WHEN observed_orders>0 AND observed_last_purchase IS NOT NULL
         THEN date_trunc('month',observed_first_purchase)::date ELSE NULL END AS cohort_month,
    CASE WHEN observed_recency_days IS NULL THEN NULL ELSE observed_recency_days>90 END AS inactive_90d,
    retention_evidence_status,
    CASE
        WHEN retention_evidence_status <> 'READY' THEN 'CANNOT_DECIDE'
        WHEN assertion_conflict THEN 'READY_WITH_ASSERTION_CONFLICT'
        ELSE 'READY'
    END AS retention_decision_readiness
FROM validated;

CREATE OR REPLACE VIEW agent.customer_retention_business AS
SELECT
    business_id,
    COUNT(*) AS customer_count,
    COUNT(*) FILTER (WHERE behavioral_evidence_available) AS customers_with_observed_sales,
    COUNT(*) FILTER (WHERE retention_evidence_status <> 'READY') AS profile_only_or_insufficient,
    COUNT(*) FILTER (WHERE repeat_customer IS TRUE) AS repeat_customers,
    ROUND(100.0*COUNT(*) FILTER(WHERE repeat_customer IS TRUE)/NULLIF(COUNT(*) FILTER(WHERE repeat_customer IS NOT NULL),0),2) AS repeat_purchase_rate_pct,
    COUNT(*) FILTER (WHERE inactive_90d IS TRUE) AS inactive_customers_90d,
    ROUND(100.0*COUNT(*) FILTER(WHERE inactive_90d IS TRUE)/NULLIF(COUNT(*) FILTER(WHERE inactive_90d IS NOT NULL),0),2) AS inactivity_rate_90d_pct,
    COUNT(*) FILTER (WHERE assertion_conflict) AS assertion_conflicts,
    COUNT(*) FILTER (WHERE retention_decision_readiness='READY') AS decision_ready,
    COUNT(*) FILTER (WHERE retention_decision_readiness='READY_WITH_ASSERTION_CONFLICT') AS decision_ready_with_conflict,
    COUNT(*) FILTER (WHERE retention_decision_readiness='CANNOT_DECIDE') AS cannot_decide,
    ROUND(SUM(observed_revenue) FILTER (WHERE inactive_90d IS TRUE),2) AS historical_revenue_of_inactive_customers
FROM agent.customer_retention_context
GROUP BY business_id;

from typing import Optional
from uuid import UUID

import asyncpg
from fastapi import APIRouter, HTTPException, Query

from app.db.database import DATABASE_URL

router = APIRouter()


async def _connect() -> asyncpg.Connection:
    return await asyncpg.connect(
        DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    )


@router.get("")
async def list_opportunities(
    business_id: Optional[UUID] = Query(None),
    product_id: Optional[UUID] = Query(None),
    opportunity_type: Optional[str] = Query(None),
    priority: Optional[str] = Query(None, pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$"),
    evidence_status: Optional[str] = Query(
        None, pattern="^(READY|LIMITED|CANNOT_DECIDE)$"
    ),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List synthesized product opportunities from current Decision OS bundles."""
    conn = await _connect()
    try:
        filters = ["b.is_current = TRUE"]
        args = []

        def add(value, expression):
            args.append(value)
            filters.append(expression.format(n=len(args)))

        if business_id is not None:
            add(business_id, "o.business_id = ${n}")
        if product_id is not None:
            add(product_id, "o.product_id = ${n}")
        if opportunity_type is not None:
            add(opportunity_type, "o.opportunity_type = ${n}")
        if priority is not None:
            add(priority, "o.priority = ${n}")
        if evidence_status is not None:
            add(evidence_status, "o.evidence_status = ${n}")

        where = " AND ".join(filters)
        count = await conn.fetchval(
            f"""
            SELECT COUNT(*)
            FROM runtime.retail_product_opportunities o
            JOIN runtime.retail_decision_bundles b ON b.bundle_id = o.bundle_id
            WHERE {where}
            """,
            *args,
        )

        limit_arg = len(args) + 1
        offset_arg = len(args) + 2
        rows = await conn.fetch(
            f"""
            SELECT
                o.opportunity_id, o.bundle_id, o.business_id, o.product_id,
                o.opportunity_type, o.priority, o.recommendation,
                o.synthesis_rule_id, o.evidence_status,
                o.synthesis_version, o.created_at
            FROM runtime.retail_product_opportunities o
            JOIN runtime.retail_decision_bundles b ON b.bundle_id = o.bundle_id
            WHERE {where}
            ORDER BY
                CASE o.priority
                    WHEN 'CRITICAL' THEN 1
                    WHEN 'HIGH' THEN 2
                    WHEN 'MEDIUM' THEN 3
                    ELSE 4
                END,
                o.created_at DESC,
                o.opportunity_id
            LIMIT ${limit_arg} OFFSET ${offset_arg}
            """,
            *args,
            limit,
            offset,
        )

        return {
            "total": count,
            "limit": limit,
            "offset": offset,
            "current_bundle_only": True,
            "opportunities": [dict(row) for row in rows],
        }
    finally:
        await conn.close()


@router.get("/business/{business_id}/summary")
async def get_business_opportunity_summary(business_id: UUID):
    """Return current product-opportunity counts for one business."""
    conn = await _connect()
    try:
        exists = await conn.fetchval(
            """
            SELECT EXISTS (
                SELECT 1
                FROM runtime.retail_decision_bundles
                WHERE business_id = $1 AND is_current = TRUE
            )
            """,
            business_id,
        )
        if not exists:
            raise HTTPException(status_code=404, detail="Current bundle not found")

        rows = await conn.fetch(
            """
            SELECT
                o.opportunity_type,
                o.priority,
                o.evidence_status,
                COUNT(*) AS count
            FROM runtime.retail_product_opportunities o
            JOIN runtime.retail_decision_bundles b ON b.bundle_id = o.bundle_id
            WHERE o.business_id = $1 AND b.is_current = TRUE
            GROUP BY o.opportunity_type, o.priority, o.evidence_status
            ORDER BY
                CASE o.priority
                    WHEN 'CRITICAL' THEN 1
                    WHEN 'HIGH' THEN 2
                    WHEN 'MEDIUM' THEN 3
                    ELSE 4
                END,
                o.opportunity_type
            """,
            business_id,
        )

        total = sum(row["count"] for row in rows)
        return {
            "business_id": business_id,
            "total": total,
            "summary": [dict(row) for row in rows],
        }
    finally:
        await conn.close()


@router.get("/product/{product_id}")
async def get_product_opportunity(product_id: UUID):
    """Return the current synthesized opportunity for a product."""
    conn = await _connect()
    try:
        rows = await conn.fetch(
            """
            SELECT
                o.opportunity_id, o.bundle_id, o.business_id, o.product_id,
                o.opportunity_type, o.priority, o.recommendation,
                o.synthesis_rule_id, o.source_output_ids, o.source_decisions,
                o.evidence_status, o.allowed_actions, o.restricted_actions,
                o.synthesis_version, o.created_at
            FROM runtime.retail_product_opportunities o
            JOIN runtime.retail_decision_bundles b ON b.bundle_id = o.bundle_id
            WHERE o.product_id = $1 AND b.is_current = TRUE
            ORDER BY o.created_at DESC
            """,
            product_id,
        )
        if not rows:
            raise HTTPException(status_code=404, detail="Product opportunity not found")
        if len(rows) > 1:
            raise HTTPException(
                status_code=409,
                detail="Product exists in multiple current business bundles; query by opportunity_id.",
            )
        return dict(rows[0])
    finally:
        await conn.close()


@router.get("/{opportunity_id}")
async def get_opportunity(opportunity_id: UUID):
    """Return a complete synthesized opportunity with atomic-decision provenance."""
    conn = await _connect()
    try:
        row = await conn.fetchrow(
            """
            SELECT
                o.opportunity_id, o.bundle_id, o.business_id, o.product_id,
                o.opportunity_type, o.priority, o.recommendation,
                o.synthesis_rule_id, o.source_output_ids, o.source_decisions,
                o.evidence_status, o.allowed_actions, o.restricted_actions,
                o.synthesis_version, o.created_at,
                b.run_id, b.version AS bundle_version,
                b.retail_os_version, b.is_current,
                b.completed_at AS bundle_completed_at
            FROM runtime.retail_product_opportunities o
            JOIN runtime.retail_decision_bundles b ON b.bundle_id = o.bundle_id
            WHERE o.opportunity_id = $1
            """,
            opportunity_id,
        )
        if row is None:
            raise HTTPException(status_code=404, detail="Opportunity not found")
        return dict(row)
    finally:
        await conn.close()

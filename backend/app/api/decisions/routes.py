from typing import Optional
from uuid import UUID

import asyncpg
from fastapi import APIRouter, HTTPException, Query

from app.db import get_database_url

router = APIRouter()


async def _connect() -> asyncpg.Connection:
    """Open an asyncpg connection using the configured DATABASE_URL."""
    db_url = get_database_url()
    return await asyncpg.connect(db_url.replace("postgresql+asyncpg://", "postgresql://"))


@router.get("")
async def list_decisions(
    business_id: Optional[UUID] = Query(None),
    bundle_id: Optional[UUID] = Query(None),
    subject_type: Optional[str] = Query(None, pattern="^(business|product|customer)$"),
    subject_id: Optional[UUID] = Query(None),
    agent_id: Optional[str] = Query(None),
    decision: Optional[str] = Query(None),
    severity: Optional[str] = Query(None, pattern="^(UNKNOWN|LOW|MEDIUM|HIGH|CRITICAL)$"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """
    List deterministic Retail decisions.

    If bundle_id is omitted, only decisions from each business's current
    Decision OS bundle are returned. This prevents mixing orchestration runs.
    """
    conn = await _connect()
    try:
        filters = []
        args = []

        def add(value, expression):
            args.append(value)
            filters.append(expression.format(n=len(args)))

        if business_id is not None:
            add(business_id, "d.business_id = ${n}")
        if bundle_id is not None:
            add(bundle_id, "d.bundle_id = ${n}")
        else:
            filters.append("b.is_current = TRUE")
        if subject_type is not None:
            add(subject_type, "d.subject_type = ${n}")
        if subject_id is not None:
            add(subject_id, "d.subject_id = ${n}")
        if agent_id is not None:
            add(agent_id, "d.agent_id = ${n}")
        if decision is not None:
            add(decision, "d.decision = ${n}")
        if severity is not None:
            add(severity, "d.severity = ${n}")

        where = " AND ".join(filters) if filters else "TRUE"
        count = await conn.fetchval(
            f"""
            SELECT COUNT(*)
            FROM runtime.retail_decision_outputs d
            JOIN runtime.retail_decision_bundles b ON b.bundle_id = d.bundle_id
            WHERE {where}
            """,
            *args,
        )

        limit_arg = len(args) + 1
        offset_arg = len(args) + 2
        rows = await conn.fetch(
            f"""
            SELECT
                d.output_id, d.business_id, d.subject_type, d.subject_id,
                d.agent_id, d.agent_version, d.decision, d.severity,
                d.recommendation, d.confidence, d.bundle_id,
                d.data_as_of, d.created_at
            FROM runtime.retail_decision_outputs d
            JOIN runtime.retail_decision_bundles b ON b.bundle_id = d.bundle_id
            WHERE {where}
            ORDER BY
                CASE d.severity
                    WHEN 'CRITICAL' THEN 1
                    WHEN 'HIGH' THEN 2
                    WHEN 'MEDIUM' THEN 3
                    WHEN 'LOW' THEN 4
                    ELSE 5
                END,
                d.created_at DESC
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
            "current_bundle_only": bundle_id is None,
            "decisions": [dict(row) for row in rows],
        }
    finally:
        await conn.close()


@router.get("/{output_id}")
async def get_decision(output_id: UUID):
    """Return the complete governed decision package for one atomic output."""
    conn = await _connect()
    try:
        row = await conn.fetchrow(
            """
            SELECT
                d.output_id, d.business_id, d.subject_type, d.subject_id,
                d.agent_id, d.agent_version, d.decision, d.severity,
                d.recommendation, d.confidence,
                d.evidence, d.calculations,
                d.rules_evaluated, d.rules_fired,
                d.boundary, d.allowed_actions, d.restricted_actions,
                d.context_snapshot,
                d.kb_version, d.rule_version, d.metric_version,
                d.source_view, d.data_as_of,
                d.bundle_id, d.created_at,
                b.run_id, b.version AS bundle_version,
                b.retail_os_version, b.is_current,
                b.completed_at AS bundle_completed_at
            FROM runtime.retail_decision_outputs d
            JOIN runtime.retail_decision_bundles b ON b.bundle_id = d.bundle_id
            WHERE d.output_id = $1
            """,
            output_id,
        )
        if row is None:
            raise HTTPException(status_code=404, detail="Decision not found")
        return dict(row)
    finally:
        await conn.close()


@router.get("/business/{business_id}/bundle")
async def get_current_bundle(business_id: UUID):
    """Return the current frozen Decision OS bundle for a Retail business."""
    conn = await _connect()
    try:
        row = await conn.fetchrow(
            """
            SELECT
                bundle_id, business_id, run_id,
                context_snapshot, rules_snapshot,
                agent_outputs, all_signals,
                is_current, version, retail_os_version, completed_at
            FROM runtime.retail_decision_bundles
            WHERE business_id = $1 AND is_current = TRUE
            """,
            business_id,
        )
        if row is None:
            raise HTTPException(status_code=404, detail="Current bundle not found")
        return dict(row)
    finally:
        await conn.close()


@router.get("/business/{business_id}/history")
async def get_bundle_history(
    business_id: UUID,
    limit: int = Query(20, ge=1, le=100),
):
    """List immutable orchestration bundles for audit and replay."""
    conn = await _connect()
    try:
        rows = await conn.fetch(
            """
            SELECT
                bundle_id, run_id, is_current, version,
                retail_os_version, completed_at
            FROM runtime.retail_decision_bundles
            WHERE business_id = $1
            ORDER BY completed_at DESC
            LIMIT $2
            """,
            business_id,
            limit,
        )
        return {"business_id": business_id, "bundles": [dict(row) for row in rows]}
    finally:
        await conn.close()

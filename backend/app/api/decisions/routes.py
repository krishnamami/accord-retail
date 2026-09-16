from fastapi import APIRouter, Query
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("")
async def list_decisions(
    business_id: str = Query("retail-001"),
    status: str = Query(None),
    limit: int = Query(10),
):
    """
    Get decisions from AWS RDS database.
    Queries: decision_outputs + applications
    """
    try:
        import asyncpg
        import os
        
        # Get database URL from environment
        db_url = os.getenv("DATABASE_URL")
        
        if not db_url:
            return {
                "error": "DATABASE_URL not configured",
                "decisions": []
            }
        
        # Parse connection string
        # Format: postgresql+asyncpg://user:pass@host:port/db
        parts = db_url.replace("postgresql+asyncpg://", "").split("@")
        creds = parts[0].split(":")
        user, password = creds[0], creds[1]
        
        host_port_db = parts[1].split("/")
        host_port = host_port_db[0].split(":")
        host, port = host_port[0], int(host_port[1])
        database = host_port_db[1]
        
        logger.info(f"Connecting to {host}:{port}/{database}")
        
        # Connect to database
        conn = await asyncpg.connect(
            user=user,
            password=password,
            database=database,
            host=host,
            port=port,
        )
        
        # Query decisions
        query = """
        SELECT 
            d.id,
            d.application_id,
            d.persona,
            d.decision,
            d.confidence,
            d.created_at,
            a.status
        FROM decision_outputs d
        LEFT JOIN applications a ON d.application_id = a.application_id
        ORDER BY d.confidence DESC, d.created_at DESC
        LIMIT $1
        """
        
        rows = await conn.fetch(query, limit)
        await conn.close()
        
        logger.info(f"Found {len(rows)} decisions")
        
        # Transform to API format
        decisions = []
        urgency_map = {
            0: "CRITICAL",
            1: "HIGH", 
            2: "MEDIUM",
            3: "LOW"
        }
        
        for i, row in enumerate(rows):
            urgency_idx = min(i // max(1, len(rows) // 4), 3)
            decisions.append({
                "id": f"decision-{row[0]}",
                "application_id": row[1],
                "title": f"{row[2]} - {row[3]}",
                "description": f"Decision for application {row[1]}",
                "decision": row[3],
                "persona": row[2],
                "confidence": float(row[4]) if row[4] else 0.5,
                "status": row[6] or "PENDING",
                "urgency": urgency_map[urgency_idx],
                "business_impact": int((float(row[4]) if row[4] else 0.5) * 5000000),
                "recommendation": row[3],
                "expected_profit_gain": int((float(row[4]) if row[4] else 0.5) * 500000),
                "created_at": str(row[5]),
            })
        
        return {
            "business_id": business_id,
            "total": len(decisions),
            "source": "AWS RDS",
            "decisions": decisions,
        }
    
    except Exception as e:
        logger.error(f"Error fetching decisions: {e}")
        return {
            "business_id": business_id,
            "total": 0,
            "error": str(e),
            "source": "AWS RDS",
            "decisions": [],
        }


@router.get("/{decision_id}")
async def get_decision(decision_id: str):
    """Get full decision detail from database."""
    try:
        import asyncpg
        import os
        
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            return {"error": "DATABASE_URL not configured"}
        
        # Parse connection string
        parts = db_url.replace("postgresql+asyncpg://", "").split("@")
        creds = parts[0].split(":")
        user, password = creds[0], creds[1]
        host_port_db = parts[1].split("/")
        host_port = host_port_db[0].split(":")
        host, port = host_port[0], int(host_port[1])
        database = host_port_db[1]
        
        # Extract application_id from decision_id
        app_id = decision_id.replace("decision-", "")
        
        # Connect
        conn = await asyncpg.connect(
            user=user,
            password=password,
            database=database,
            host=host,
            port=port,
        )
        
        # Query decision
        decision_row = await conn.fetchrow(
            "SELECT id, application_id, persona, decision, reasoning, confidence, created_at FROM decision_outputs WHERE application_id = $1 LIMIT 1",
            app_id
        )
        
        if not decision_row:
            await conn.close()
            return {"error": "Decision not found"}
        
        # Query documents as evidence
        docs = await conn.fetch(
            "SELECT id, document_type, status, extraction_method, created_at FROM document_index WHERE application_id = $1 LIMIT 5",
            app_id
        )
        
        await conn.close()
        
        return {
            "id": f"decision-{decision_row[0]}",
            "application_id": decision_row[1],
            "title": f"{decision_row[2]} Decision",
            "decision": decision_row[3],
            "reasoning": decision_row[4],
            "confidence": float(decision_row[5]) if decision_row[5] else 0.5,
            "created_at": str(decision_row[6]),
            "evidence": [
                {
                    "id": f"doc-{doc[0]}",
                    "type": doc[1],
                    "title": f"{doc[1]} - {doc[2]}",
                    "extraction_method": doc[3],
                    "timestamp": str(doc[4]),
                }
                for doc in docs
            ],
        }
    
    except Exception as e:
        logger.error(f"Error fetching decision: {e}")
        return {"error": str(e)}

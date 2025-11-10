"""Session retrieval endpoint."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import ResearchSession
from src.database.session import get_db

if TYPE_CHECKING:
    pass

router = APIRouter(prefix="/v1", tags=["sessions"])


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Retrieve a research/search session by ID.

    Args:
        session_id: UUID of the session
        db: Database session

    Returns:
        Session data with results
    """
    stmt = select(ResearchSession).where(ResearchSession.id == session_id)
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "session_not_found", "message": f"Session {session_id} not found"},
        )

    return {
        "id": str(session.id),
        "query": session.query,
        "mode": session.mode,
        "status": session.status,
        "result": session.result,
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "completed_at": session.completed_at.isoformat() if session.completed_at else None,
    }

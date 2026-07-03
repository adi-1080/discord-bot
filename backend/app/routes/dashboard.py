from datetime import datetime

from pydantic import BaseModel
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models.command_log import CommandLog
from app.models.user import User

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


class CommandLogResponse(BaseModel):
    id: int
    interaction_id: str
    guild_id: str | None
    command_name: str
    user_id: str | None
    username: str | None
    actions_taken: list
    status: str
    created_at: datetime


@router.get("/logs", response_model=list[CommandLogResponse])
async def get_logs(
    limit: int = Query(default=50, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CommandLogResponse]:
    logs = (
        await db.scalars(
            select(CommandLog).order_by(CommandLog.created_at.desc()).limit(limit)
        )
    ).all()
    return [
        CommandLogResponse(
            id=log.id,
            interaction_id=log.interaction_id,
            guild_id=log.guild_id,
            command_name=log.command_name,
            user_id=log.user_id,
            username=log.username,
            actions_taken=log.actions_taken or [],
            status=log.status,
            created_at=log.created_at,
        )
        for log in logs
    ]


@router.get("/stats")
async def get_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    logs = (await db.scalars(select(CommandLog))).all()
    by_status: dict[str, int] = {}
    for log in logs:
        by_status[log.status] = by_status.get(log.status, 0) + 1
    return {"total": len(logs), "by_status": by_status}

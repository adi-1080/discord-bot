from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.processed_interaction import ProcessedInteraction


async def try_claim_interaction(session: AsyncSession, interaction_id: str) -> bool:
    """Return True if this is the first time we've seen this interaction."""
    existing = await session.scalar(
        select(ProcessedInteraction).where(
            ProcessedInteraction.interaction_id == interaction_id
        )
    )
    if existing:
        return False

    session.add(ProcessedInteraction(interaction_id=interaction_id))
    try:
        await session.commit()
        return True
    except IntegrityError:
        await session.rollback()
        return False

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.command_log import CommandLog
from app.services.commands import run_command_background
from app.services.dedup import try_claim_interaction
from app.services.verify import verify_discord_signature

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/discord", tags=["discord"])

INTERACTION_PING = 1
INTERACTION_APPLICATION_COMMAND = 2
INTERACTION_DEFERRED_CHANNEL_MESSAGE = 5


@router.post("/interactions")
async def handle_interaction(request: Request, db: AsyncSession = Depends(get_db)) -> Response:
    settings = get_settings()
    body = await request.body()
    signature = request.headers.get("X-Signature-Ed25519", "")
    timestamp = request.headers.get("X-Signature-Timestamp", "")

    if not verify_discord_signature(body, signature, timestamp, settings.discord_public_key):
        raise HTTPException(status_code=401, detail="Invalid request signature")

    interaction = json.loads(body)
    interaction_type = interaction.get("type")
    interaction_id = str(interaction.get("id", ""))

    if interaction_type == INTERACTION_PING:
        return Response(content='{"type":1}', media_type="application/json")

    if interaction_type == INTERACTION_APPLICATION_COMMAND:
        is_new = await try_claim_interaction(db, interaction_id)
        if not is_new:
            logger.info("Duplicate interaction %s ignored", interaction_id)
            return Response(
                content='{"type":5,"data":{"flags":64}}',
                media_type="application/json",
            )

        member = interaction.get("member") or {}
        user = member.get("user") or interaction.get("user") or {}
        command_name = interaction.get("data", {}).get("name", "unknown")

        command_log = CommandLog(
            interaction_id=interaction_id,
            guild_id=interaction.get("guild_id"),
            command_name=command_name,
            user_id=str(user.get("id", "")),
            username=user.get("username"),
            payload=interaction,
            actions_taken=["deferred"],
            status="pending",
        )
        db.add(command_log)
        await db.commit()
        await db.refresh(command_log)

        import asyncio

        asyncio.create_task(run_command_background(interaction, command_log.id))

        return Response(
            content='{"type":5,"data":{"flags":0}}',
            media_type="application/json",
        )

    raise HTTPException(status_code=400, detail="Unsupported interaction type")

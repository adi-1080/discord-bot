import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.command_log import CommandLog
from app.models.pending_action import PendingAction
from app.services.discord_api import post_to_channel
from app.services.mirror import send_webhook_message

logger = logging.getLogger(__name__)

RETRY_INTERVAL_SECONDS = 30
MAX_BACKOFF_SECONDS = 300


async def execute_pending_action(session: AsyncSession, action: PendingAction) -> None:
    payload = action.payload
    if action.action_type == "mirror":
        await send_webhook_message(
            payload["webhook_url"],
            payload.get("content", ""),
            embeds=[payload["embed"]] if payload.get("embed") else None,
        )
    elif action.action_type == "channel_post":
        await post_to_channel(
            payload["channel_id"],
            payload.get("content", ""),
            embeds=[payload["embed"]] if payload.get("embed") else None,
        )
    else:
        raise ValueError(f"Unknown action type: {action.action_type}")


async def process_pending_actions_once() -> int:
    now = datetime.now(UTC)
    processed = 0

    async with async_session() as session:
        pending_actions = (
            await session.scalars(
                select(PendingAction)
                .where(PendingAction.status == "pending")
                .where(PendingAction.next_retry_at <= now)
                .order_by(PendingAction.next_retry_at)
                .limit(20)
            )
        ).all()

        for action in pending_actions:
            try:
                await execute_pending_action(session, action)
                action.status = "completed"
                command_log = await session.get(CommandLog, action.command_log_id)
                if command_log and command_log.status == "partial":
                    command_log.status = "success"
                    if command_log.actions_taken is None:
                        command_log.actions_taken = []
                    command_log.actions_taken = list(command_log.actions_taken) + [
                        f"{action.action_type}_retried_ok"
                    ]
                processed += 1
            except Exception as exc:
                action.retry_count += 1
                action.last_error = str(exc)
                if action.retry_count >= action.max_retries:
                    action.status = "failed"
                    command_log = await session.get(CommandLog, action.command_log_id)
                    if command_log:
                        command_log.status = "failed"
                        if command_log.actions_taken is None:
                            command_log.actions_taken = []
                        command_log.actions_taken = list(command_log.actions_taken) + [
                            f"{action.action_type}_failed"
                        ]
                else:
                    backoff = min(RETRY_INTERVAL_SECONDS * (2 ** action.retry_count), MAX_BACKOFF_SECONDS)
                    action.next_retry_at = now + timedelta(seconds=backoff)
                logger.warning("Retry failed for pending action %s: %s", action.id, exc)

        await session.commit()

    return processed


async def retry_loop(stop_event: asyncio.Event) -> None:
    logger.info("Pending action retry loop started")
    while not stop_event.is_set():
        try:
            count = await process_pending_actions_once()
            if count:
                logger.info("Processed %d pending actions", count)
        except Exception:
            logger.exception("Retry loop error")
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=RETRY_INTERVAL_SECONDS)
            break
        except TimeoutError:
            continue
    logger.info("Pending action retry loop stopped")

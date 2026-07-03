import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.command_log import CommandLog
from app.models.guild_config import GuildConfig
from app.models.pending_action import PendingAction
from app.services.discord_api import post_to_channel, send_followup
from app.services.mirror import send_webhook_message

logger = logging.getLogger(__name__)

APP_START_TIME = datetime.now(UTC)


def classify_report(text: str, rules: dict) -> str:
    keywords = rules.get("report_keywords", {})
    lower = text.lower()
    for keyword, tag in keywords.items():
        if keyword in lower:
            return tag
    return "normal"


def extract_option(interaction: dict, name: str) -> str | None:
    for option in interaction.get("data", {}).get("options", []):
        if option.get("name") == name:
            return option.get("value")
    return None


async def get_guild_config(session: AsyncSession, guild_id: str | None) -> GuildConfig | None:
    if not guild_id:
        return None
    return await session.scalar(select(GuildConfig).where(GuildConfig.guild_id == guild_id))


async def schedule_pending_action(
    session: AsyncSession,
    command_log_id: int,
    action_type: str,
    payload: dict,
    error: str,
) -> None:
    pending = PendingAction(
        command_log_id=command_log_id,
        action_type=action_type,
        payload=payload,
        retry_count=0,
        next_retry_at=datetime.now(UTC) + timedelta(seconds=30),
        last_error=error,
        status="pending",
    )
    session.add(pending)
    await session.commit()


async def process_command(
    session: AsyncSession,
    interaction: dict,
    command_log: CommandLog,
) -> None:
    settings = get_settings()
    command_name = interaction.get("data", {}).get("name", "")
    guild_id = interaction.get("guild_id")
    application_id = interaction["application_id"]
    interaction_token = interaction["token"]

    guild_config = await get_guild_config(session, guild_id)
    actions: list[str] = []
    status = "success"

    try:
        if command_name == "report":
            text = extract_option(interaction, "text") or ""
            rules = guild_config.command_rules if guild_config else {}
            tag = classify_report(text, rules)
            username = interaction.get("member", {}).get("user", {}).get("username", "unknown")

            embed = {
                "title": f"Report [{tag.upper()}]",
                "description": text,
                "color": 0x5865F2 if tag == "normal" else 0xED4245,
                "fields": [
                    {"name": "Submitted by", "value": username, "inline": True},
                    {"name": "Priority", "value": tag, "inline": True},
                ],
            }

            followup = f"Report recorded with priority **{tag}**. Thank you!"
            await send_followup(application_id, interaction_token, followup, ephemeral=True)
            actions.append("replied_to_user")

            if guild_config:
                try:
                    await post_to_channel(
                        guild_config.channel_id,
                        f"New report from {username}",
                        embeds=[embed],
                    )
                    actions.append("posted_to_channel")
                except Exception as exc:
                    logger.exception("Failed to post to channel")
                    await schedule_pending_action(
                        session,
                        command_log.id,
                        "channel_post",
                        {"channel_id": guild_config.channel_id, "embed": embed, "content": f"New report from {username}"},
                        str(exc),
                    )
                    actions.append("channel_post_queued")
                    status = "partial"

                if rules.get("auto_mirror", True):
                    mirror_content = f"**Mirror** | /report from {username} in guild `{guild_id}`\nPriority: **{tag}**\n{text}"
                    try:
                        await send_webhook_message(
                            guild_config.mirror_webhook_url,
                            mirror_content,
                            embeds=[embed],
                        )
                        actions.append("mirrored")
                    except Exception as exc:
                        logger.exception("Failed to mirror")
                        await schedule_pending_action(
                            session,
                            command_log.id,
                            "mirror",
                            {"webhook_url": guild_config.mirror_webhook_url, "content": mirror_content, "embed": embed},
                            str(exc),
                        )
                        actions.append("mirror_queued")
                        status = "partial"

        elif command_name == "status":
            count_stmt = select(func.count()).select_from(CommandLog).where(
                CommandLog.created_at >= datetime.now(UTC) - timedelta(hours=24)
            )
            if guild_id:
                count_stmt = count_stmt.where(CommandLog.guild_id == guild_id)
            recent_count = await session.scalar(count_stmt) or 0

            uptime = datetime.now(UTC) - APP_START_TIME
            hours, remainder = divmod(int(uptime.total_seconds()), 3600)
            minutes, _ = divmod(remainder, 60)
            guild_name = guild_config.guild_name if guild_config else "Not configured"

            message = (
                f"**Bot Status**\n"
                f"Uptime: {hours}h {minutes}m\n"
                f"Guild: {guild_name}\n"
                f"Commands (24h): {recent_count}"
            )
            await send_followup(application_id, interaction_token, message)
            actions.append("replied_to_user")

            if guild_config and guild_config.command_rules.get("auto_mirror", True):
                mirror_content = f"**Mirror** | /status used in guild `{guild_id}` — {recent_count} commands in last 24h"
                try:
                    await send_webhook_message(guild_config.mirror_webhook_url, mirror_content)
                    actions.append("mirrored")
                except Exception as exc:
                    logger.exception("Failed to mirror status")
                    await schedule_pending_action(
                        session,
                        command_log.id,
                        "mirror",
                        {"webhook_url": guild_config.mirror_webhook_url, "content": mirror_content},
                        str(exc),
                    )
                    actions.append("mirror_queued")
                    status = "partial"
        else:
            await send_followup(
                application_id,
                interaction_token,
                f"Unknown command: {command_name}",
                ephemeral=True,
            )
            actions.append("unknown_command")
            status = "failed"

    except Exception as exc:
        logger.exception("Command processing failed")
        status = "failed"
        actions.append(f"error: {exc}")
        try:
            await send_followup(
                application_id,
                interaction_token,
                "Something went wrong processing your command.",
                ephemeral=True,
            )
        except Exception:
            logger.exception("Failed to send error followup")

    command_log.actions_taken = actions
    command_log.status = status
    await session.commit()


async def run_command_background(interaction: dict, command_log_id: int) -> None:
    from app.database import async_session

    await asyncio.sleep(0.5)
    async with async_session() as session:
        command_log = await session.get(CommandLog, command_log_id)
        if command_log is None:
            return
        await process_command(session, interaction, command_log)

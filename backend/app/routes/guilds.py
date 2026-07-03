from pydantic import BaseModel, Field, field_validator
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.deps import get_current_user, mask_secret
from app.models.guild_config import DEFAULT_COMMAND_RULES, GuildConfig
from app.models.user import User
from app.services.discord_api import register_slash_commands

router = APIRouter(prefix="/api/guilds", tags=["guilds"])


class GuildConfigCreate(BaseModel):
    guild_id: str = Field(min_length=1, max_length=32)
    guild_name: str | None = None
    channel_id: str = Field(min_length=1, max_length=32)
    mirror_webhook_url: str = Field(min_length=1, max_length=512)
    command_rules: dict | None = None

    @field_validator("guild_id", "channel_id", "mirror_webhook_url")
    @classmethod
    def strip_whitespace(cls, value: str) -> str:
        return value.strip()

    @field_validator("guild_name")
    @classmethod
    def normalize_guild_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class GuildConfigUpdate(BaseModel):
    guild_name: str | None = None
    channel_id: str | None = None
    mirror_webhook_url: str | None = None
    command_rules: dict | None = None


class GuildConfigResponse(BaseModel):
    id: int
    guild_id: str
    guild_name: str | None
    channel_id: str
    mirror_webhook_url: str
    command_rules: dict
    bot_invite_url: str


def to_response(config: GuildConfig) -> GuildConfigResponse:
    settings = get_settings()
    invite_url = (
        f"https://discord.com/api/oauth2/authorize"
        f"?client_id={settings.discord_application_id}"
        f"&permissions=3072&scope=bot%20applications.commands"
    )
    return GuildConfigResponse(
        id=config.id,
        guild_id=config.guild_id,
        guild_name=config.guild_name,
        channel_id=config.channel_id,
        mirror_webhook_url=mask_secret(config.mirror_webhook_url),
        command_rules=config.command_rules,
        bot_invite_url=invite_url,
    )


@router.get("/invite-url")
async def get_invite_url(current_user: User = Depends(get_current_user)) -> dict:
    settings = get_settings()
    if not settings.discord_application_id:
        raise HTTPException(status_code=400, detail="DISCORD_APPLICATION_ID is not configured")
    invite_url = (
        f"https://discord.com/api/oauth2/authorize"
        f"?client_id={settings.discord_application_id}"
        f"&permissions=3072&scope=bot%20applications.commands"
    )
    return {"bot_invite_url": invite_url}


@router.get("", response_model=list[GuildConfigResponse])
async def list_guilds(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[GuildConfigResponse]:
    configs = (
        await db.scalars(
            select(GuildConfig).where(GuildConfig.owner_user_id == current_user.id)
        )
    ).all()
    return [to_response(c) for c in configs]


@router.post("", response_model=GuildConfigResponse)
async def create_guild(
    body: GuildConfigCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GuildConfigResponse:
    existing = await db.scalar(select(GuildConfig).where(GuildConfig.guild_id == body.guild_id))
    if existing:
        if existing.owner_user_id != current_user.id:
            raise HTTPException(status_code=400, detail="Guild already configured by another account")
        existing.guild_name = body.guild_name
        existing.channel_id = body.channel_id
        existing.mirror_webhook_url = body.mirror_webhook_url
        if body.command_rules is not None:
            existing.command_rules = body.command_rules
        await db.commit()
        await db.refresh(existing)
        return to_response(existing)

    config = GuildConfig(
        guild_id=body.guild_id,
        guild_name=body.guild_name,
        channel_id=body.channel_id,
        mirror_webhook_url=body.mirror_webhook_url,
        command_rules=body.command_rules or DEFAULT_COMMAND_RULES,
        owner_user_id=current_user.id,
    )
    db.add(config)
    await db.commit()
    await db.refresh(config)
    return to_response(config)


@router.put("/{guild_id}", response_model=GuildConfigResponse)
async def update_guild(
    guild_id: str,
    body: GuildConfigUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GuildConfigResponse:
    config = await db.scalar(
        select(GuildConfig).where(
            GuildConfig.guild_id == guild_id,
            GuildConfig.owner_user_id == current_user.id,
        )
    )
    if config is None:
        raise HTTPException(status_code=404, detail="Guild not found")

    if body.guild_name is not None:
        config.guild_name = body.guild_name
    if body.channel_id is not None:
        config.channel_id = body.channel_id
    if body.mirror_webhook_url is not None:
        config.mirror_webhook_url = body.mirror_webhook_url
    if body.command_rules is not None:
        config.command_rules = body.command_rules

    await db.commit()
    await db.refresh(config)
    return to_response(config)


@router.post("/register-commands")
async def register_commands(current_user: User = Depends(get_current_user)) -> dict:
    try:
        commands = await register_slash_commands()
        return {"registered": len(commands), "commands": [c["name"] for c in commands]}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to register commands: {exc}")

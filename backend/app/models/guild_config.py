from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

DEFAULT_COMMAND_RULES = {
    "auto_mirror": True,
    "report_keywords": {
        "urgent": "high",
        "critical": "high",
        "bug": "medium",
        "help": "low",
    },
}


class GuildConfig(Base):
    __tablename__ = "guild_configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    guild_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    guild_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    channel_id: Mapped[str] = mapped_column(String(32))
    mirror_webhook_url: Mapped[str] = mapped_column(String(512))
    command_rules: Mapped[dict] = mapped_column(JSONB, default=DEFAULT_COMMAND_RULES)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ProcessedInteraction(Base):
    __tablename__ = "processed_interactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    interaction_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

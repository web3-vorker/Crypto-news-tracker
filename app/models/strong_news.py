from datetime import datetime

from sqlalchemy import String, Integer, DateTime, func

from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from app.models.base import Base


class StrongNews(Base):

    __tablename__ = "strong_news"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    title: Mapped[str] = mapped_column(
        String,
        unique=True,
    )

    abridged_text: Mapped[str] = mapped_column(
        String,
    )

    sentiment: Mapped[str] = mapped_column(
        String,
    )

    score: Mapped[int] = mapped_column(
        Integer,
    )

    reason: Mapped[str] = mapped_column(
        String,
    )

    category: Mapped[str] = mapped_column(
        String,
    )

    source: Mapped[str] = mapped_column(
        String,
    )

    url: Mapped[str] = mapped_column(
        String,
        unique=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
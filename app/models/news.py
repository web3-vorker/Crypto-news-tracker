from datetime import datetime

from sqlalchemy import String, DateTime, func

from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from app.models.base import Base


class News(Base):

    __tablename__ = "news"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    title: Mapped[str] = mapped_column(
        String,
        unique=True,
    )

    text: Mapped[str] = mapped_column(
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
        default=datetime.now(),
    )
"""SQLAlchemy ORM model for the resonance-line cache (plan §6).

Conceptually owned by the search module: resonance lines are LLM-generated
per `(query, book)` pair on first ask and cached here. Cache key:
`sha256(query || book_id)`, stored as `query_hash CHAR(64)`.
"""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import CHAR, DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from sentido.shared.db import Base


class ResonanceCacheORM(Base):
    __tablename__ = "resonance_cache"

    query_hash: Mapped[str] = mapped_column(CHAR(64), primary_key=True)
    book_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("books.id", ondelete="CASCADE"),
        primary_key=True,
    )
    line: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

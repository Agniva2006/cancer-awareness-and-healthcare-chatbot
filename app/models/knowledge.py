"""Knowledge document model — replaces the JSON files."""

from typing import Optional

from sqlalchemy import Boolean, String, Text

try:  # pgvector SDK present — but the SERVER must also have the extension
    from pgvector.sqlalchemy import Vector

    from app.core.database import engine as _engine

    def _server_has_vector() -> bool:
        try:
            with _engine.connect() as conn:
                row = conn.exec_driver_sql(
                    "SELECT count(*) FROM pg_extension WHERE extname = 'vector'"
                ).fetchone()
                return bool(row and row[0])
        except Exception:
            return False

    VECTOR_AVAILABLE = _server_has_vector()
except ImportError:  # pragma: no cover - sqlite/test environments
    Vector = None
    VECTOR_AVAILABLE = False

from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, new_uuid

EMBEDDING_DIM = 384  # all-MiniLM-L6-v2


class KnowledgeDocument(Base, TimestampMixin):
    __tablename__ = "knowledge_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    title: Mapped[str] = mapped_column(String(500), index=True, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(255), default="")
    category: Mapped[str] = mapped_column(String(100), default="general", index=True)
    cancer_type: Mapped[str] = mapped_column(String(100), default="lung", index=True)
    difficulty: Mapped[str] = mapped_column(String(20), default="patient")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # External identifier so seeding from JSON stays idempotent
    external_key: Mapped[Optional[str]] = mapped_column(
        String(120), unique=True, nullable=True
    )

    if VECTOR_AVAILABLE:
        embedding = mapped_column(Vector(EMBEDDING_DIM), nullable=True)
    else:
        # Server lacks pgvector — no embedding column in the ORM at all,
        # so queries/inserts never reference it.
        embedding = None

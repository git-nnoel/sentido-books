"""initial schema — authors, books, editions, collections, collection_books, resonance_cache

Revision ID: 0001
Revises:
Create Date: 2026-06-14 00:00:00

Creates the Phase 0 schema declared in
docs/instructions/backend-implementation-plan.md §4 + §6:

- Enables `vector` (pgvector) and `pgcrypto` (for gen_random_uuid()) extensions.
- Creates authors, books, editions, collections, collection_books tables.
- Creates the resonance_cache table (search-module-owned).
- Creates all documented indexes including a partial ivfflat (cosine_ops)
  index on books.embedding for pgvector similarity search.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- Extensions ---
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # --- authors ---
    op.create_table(
        "authors",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("slug", sa.Text(), nullable=False, unique=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("nationality", sa.Text(), nullable=True),
        sa.Column("born", sa.Date(), nullable=True),
        sa.Column(
            "awards",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("ol_id", sa.Text(), nullable=True),
        sa.Column("wiki_url", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # --- books ---
    op.create_table(
        "books",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("slug", sa.Text(), nullable=False, unique=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("original_title", sa.Text(), nullable=True),
        sa.Column(
            "author_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("authors.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("year_published", sa.Integer(), nullable=True),
        sa.Column("synopsis", sa.Text(), nullable=True),
        sa.Column(
            "emotional_profile",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "atmosphere_tags",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("ARRAY[]::text[]"),
        ),
        sa.Column("narrative_pace", sa.Text(), nullable=True),
        sa.Column("cover_url", sa.Text(), nullable=True),
        sa.Column("ol_id", sa.Text(), nullable=True),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column(
            "embedding_status",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column(
            "profile_status",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column(
            "published",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # books indexes — names + predicates per plan §4.1
    op.create_index(
        "books_published_idx",
        "books",
        ["published"],
        postgresql_where=sa.text("published = true"),
    )
    op.create_index("books_author_idx", "books", ["author_id"])
    # pgvector ivfflat cosine index, partial where embedding IS NOT NULL,
    # lists=100 (plan §11 D6).
    op.execute(
        "CREATE INDEX books_embedding_idx ON books "
        "USING ivfflat (embedding vector_cosine_ops) "
        "WITH (lists = 100) "
        "WHERE embedding IS NOT NULL"
    )

    # --- editions ---
    op.create_table(
        "editions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "book_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("books.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("publisher", sa.Text(), nullable=True),
        sa.Column("language", sa.Text(), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("isbn", sa.Text(), nullable=True),
        sa.Column("cover_url", sa.Text(), nullable=True),
    )

    op.create_index("editions_book_idx", "editions", ["book_id"])
    op.create_index(
        "editions_isbn_idx",
        "editions",
        ["isbn"],
        postgresql_where=sa.text("isbn IS NOT NULL"),
    )

    # --- collections ---
    op.create_table(
        "collections",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("slug", sa.Text(), nullable=False, unique=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "published",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # --- collection_books ---
    op.create_table(
        "collection_books",
        sa.Column(
            "collection_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("collections.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "book_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("books.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("position", sa.Integer(), nullable=False),
    )

    # --- resonance_cache (plan §6) ---
    op.create_table(
        "resonance_cache",
        sa.Column("query_hash", sa.CHAR(64), primary_key=True),
        sa.Column(
            "book_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("books.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("line", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("resonance_cache")
    op.drop_table("collection_books")
    op.drop_table("collections")
    op.drop_index("editions_isbn_idx", table_name="editions")
    op.drop_index("editions_book_idx", table_name="editions")
    op.drop_table("editions")
    op.execute("DROP INDEX IF EXISTS books_embedding_idx")
    op.drop_index("books_author_idx", table_name="books")
    op.drop_index("books_published_idx", table_name="books")
    op.drop_table("books")
    op.drop_table("authors")
    # Extensions are intentionally NOT dropped — they may be used by
    # other databases on the cluster.

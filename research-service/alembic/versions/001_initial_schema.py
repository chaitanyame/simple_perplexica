"""Initial database schema.

Revision ID: 001
Revises:
Create Date: 2025-01-01 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create initial schema."""
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Create research_sessions table
    op.create_table(
        "research_sessions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("mode", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("execution_time_seconds", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_research_sessions_mode"), "research_sessions", ["mode"], unique=False)
    op.create_index(
        op.f("ix_research_sessions_status"),
        "research_sessions",
        ["status"],
        unique=False,
    )

    # Create rag_documents table
    op.create_table(
        "rag_documents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("source_type", sa.String(length=20), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("embedding", Vector(384), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_accessed", sa.DateTime(), nullable=True),
        sa.Column("access_count", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_rag_documents_content_hash"),
        "rag_documents",
        ["content_hash"],
        unique=True,
    )
    op.create_index(
        op.f("ix_rag_documents_source_type"),
        "rag_documents",
        ["source_type"],
        unique=False,
    )

    # Create vector index for similarity search
    op.execute(
        """
        CREATE INDEX ix_rag_documents_embedding ON rag_documents
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
        """
    )

    # Create session_documents association table
    op.create_table(
        "session_documents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("relevance_score", sa.Float(), nullable=True),
        sa.Column("used_in_synthesis", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["rag_documents.id"],
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["research_sessions.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_session_documents_document_id"),
        "session_documents",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_session_documents_session_id"),
        "session_documents",
        ["session_id"],
        unique=False,
    )

    # Create function and trigger for updating document access stats
    op.execute(
        """
        CREATE OR REPLACE FUNCTION update_document_access()
        RETURNS TRIGGER AS $$
        BEGIN
            UPDATE rag_documents
            SET last_accessed = NOW(),
                access_count = access_count + 1
            WHERE id = NEW.document_id;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    op.execute(
        """
        CREATE TRIGGER trigger_update_document_access
        AFTER INSERT ON session_documents
        FOR EACH ROW
        EXECUTE FUNCTION update_document_access();
        """
    )


def downgrade() -> None:
    """Drop all tables and extensions."""
    op.execute("DROP TRIGGER IF EXISTS trigger_update_document_access ON session_documents")
    op.execute("DROP FUNCTION IF EXISTS update_document_access()")

    op.drop_index(op.f("ix_session_documents_session_id"), table_name="session_documents")
    op.drop_index(op.f("ix_session_documents_document_id"), table_name="session_documents")
    op.drop_table("session_documents")

    op.execute("DROP INDEX IF EXISTS ix_rag_documents_embedding")
    op.drop_index(op.f("ix_rag_documents_source_type"), table_name="rag_documents")
    op.drop_index(op.f("ix_rag_documents_content_hash"), table_name="rag_documents")
    op.drop_table("rag_documents")

    op.drop_index(op.f("ix_research_sessions_status"), table_name="research_sessions")
    op.drop_index(op.f("ix_research_sessions_mode"), table_name="research_sessions")
    op.drop_table("research_sessions")

    op.execute("DROP EXTENSION IF EXISTS vector")

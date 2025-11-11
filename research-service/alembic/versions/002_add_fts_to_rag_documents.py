"""add_fts_to_rag_documents

Revision ID: 002
Revises: 001
Create Date: 2025-11-10 23:13:09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add Full-Text Search support to rag_documents table.
    
    This migration:
    1. Adds content_fts tsvector column for Full-Text Search
    2. Creates GIN index on content_fts for fast search
    3. Creates trigger to auto-update content_fts when content changes
    4. Initializes content_fts for existing rows
    """
    
    # Add tsvector column for Full-Text Search
    op.execute("""
        ALTER TABLE rag_documents 
        ADD COLUMN content_fts tsvector;
    """)
    
    # Create GIN index for fast full-text search
    op.execute("""
        CREATE INDEX idx_rag_documents_content_fts 
        ON rag_documents 
        USING GIN(content_fts);
    """)
    
    # Create function to update tsvector column
    op.execute("""
        CREATE OR REPLACE FUNCTION rag_documents_content_fts_trigger()
        RETURNS trigger AS $$
        BEGIN
            NEW.content_fts := to_tsvector('english', COALESCE(NEW.content, ''));
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # Create trigger to auto-update tsvector on INSERT/UPDATE
    op.execute("""
        CREATE TRIGGER tsvector_update_trigger
        BEFORE INSERT OR UPDATE OF content
        ON rag_documents
        FOR EACH ROW
        EXECUTE FUNCTION rag_documents_content_fts_trigger();
    """)
    
    # Initialize content_fts for existing rows
    op.execute("""
        UPDATE rag_documents
        SET content_fts = to_tsvector('english', COALESCE(content, ''))
        WHERE content_fts IS NULL;
    """)


def downgrade() -> None:
    """Remove Full-Text Search support from rag_documents table."""
    
    # Drop trigger first
    op.execute("DROP TRIGGER IF EXISTS tsvector_update_trigger ON rag_documents;")
    
    # Drop trigger function
    op.execute("DROP FUNCTION IF EXISTS rag_documents_content_fts_trigger();")
    
    # Drop GIN index
    op.execute("DROP INDEX IF EXISTS idx_rag_documents_content_fts;")
    
    # Drop tsvector column
    op.execute("ALTER TABLE rag_documents DROP COLUMN IF EXISTS content_fts;")

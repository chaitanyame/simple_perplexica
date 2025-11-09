-- Initialize PostgreSQL database with pgvector extension

-- Enable pgvector extension for vector similarity search
CREATE EXTENSION IF NOT EXISTS vector;

-- Research sessions table
CREATE TABLE IF NOT EXISTS research_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query TEXT NOT NULL,
    mode VARCHAR(20) NOT NULL CHECK (mode IN ('search', 'research')),
    status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    result JSONB,
    error_message TEXT,
    execution_time_seconds FLOAT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP
);

-- Indexes for research_sessions
CREATE INDEX IF NOT EXISTS idx_research_sessions_mode ON research_sessions(mode);
CREATE INDEX IF NOT EXISTS idx_research_sessions_status ON research_sessions(status);
CREATE INDEX IF NOT EXISTS idx_research_sessions_created_at ON research_sessions(created_at DESC);

-- RAG documents table with vector embeddings
CREATE TABLE IF NOT EXISTS rag_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT NOT NULL,
    content_hash VARCHAR(64) NOT NULL UNIQUE,
    source_url TEXT,
    source_type VARCHAR(20) NOT NULL CHECK (source_type IN ('web', 'pdf', 'excel', 'word')),
    metadata JSONB,
    embedding vector(384) NOT NULL,
    token_count INTEGER,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_accessed TIMESTAMP,
    access_count INTEGER NOT NULL DEFAULT 0
);

-- Indexes for rag_documents
CREATE INDEX IF NOT EXISTS idx_rag_documents_content_hash ON rag_documents(content_hash);
CREATE INDEX IF NOT EXISTS idx_rag_documents_source_type ON rag_documents(source_type);
CREATE INDEX IF NOT EXISTS idx_rag_documents_embedding ON rag_documents USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Session-document association table
CREATE TABLE IF NOT EXISTS session_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES research_sessions(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES rag_documents(id) ON DELETE CASCADE,
    relevance_score FLOAT,
    used_in_synthesis BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(session_id, document_id)
);

-- Indexes for session_documents
CREATE INDEX IF NOT EXISTS idx_session_documents_session_id ON session_documents(session_id);
CREATE INDEX IF NOT EXISTS idx_session_documents_document_id ON session_documents(document_id);
CREATE INDEX IF NOT EXISTS idx_session_documents_relevance_score ON session_documents(relevance_score DESC);

-- Function to update last_accessed and access_count
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

-- Trigger to automatically update document access stats
CREATE TRIGGER trigger_update_document_access
AFTER INSERT ON session_documents
FOR EACH ROW
EXECUTE FUNCTION update_document_access();

-- Comments for documentation
COMMENT ON TABLE research_sessions IS 'Tracks user research sessions with queries and results';
COMMENT ON TABLE rag_documents IS 'Vector store for RAG retrieval with pgvector embeddings';
COMMENT ON TABLE session_documents IS 'Association between sessions and documents used';
COMMENT ON COLUMN rag_documents.embedding IS '384-dimensional vector from sentence-transformers/all-MiniLM-L6-v2';

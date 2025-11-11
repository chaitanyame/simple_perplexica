"""Test hybrid search integration in ResearchAgent.

This script demonstrates:
1. Storing documents in vector database
2. Performing hybrid search (vector + FTS)
3. Comparing hybrid vs vector-only results
"""

import asyncio
import uuid

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.agents.research_agent import ResearchAgent, ResearchAgentDeps, SearchSource
from src.agents.search_agent import SearchAgent, SearchAgentDeps
from src.core.config import settings
from src.rag.vector_store_repository import VectorStoreRepository
from src.services.embedding.embedding_service import EmbeddingService
from src.services.llm.langfuse_tracer import LangfuseTracer
from src.services.llm.openrouter_client import OpenRouterClient


async def test_hybrid_search():
    """Test hybrid search with sample documents."""
    
    # Setup database
    engine = create_async_engine(str(settings.DATABASE_URL), echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        # Initialize services
        llm_client = OpenRouterClient(
            api_key=settings.OPENROUTER_API_KEY,
            model=settings.LLM_MODEL,
        )
        
        tracer = LangfuseTracer(
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            secret_key=settings.LANGFUSE_SECRET_KEY,
            host=settings.LANGFUSE_HOST,
        )
        
        embedding_service = EmbeddingService(
            model_name="all-MiniLM-L6-v2",
            device="cpu",
        )
        
        vector_store = VectorStoreRepository(db=db, dimension=384)
        
        # Create test session
        from src.database.models import ResearchSession
        from datetime import datetime
        
        session_id = uuid.uuid4()
        test_session = ResearchSession(
            id=session_id,
            query="test hybrid search",
            mode="search",
            status="processing",
            created_at=datetime.utcnow()
        )
        db.add(test_session)
        await db.commit()
        
        print(f"📝 Test Session ID: {session_id}")
        
        # Create sample documents
        sample_docs = [
            {
                "content": "Transformer architecture uses self-attention mechanisms to process sequences in parallel. The attention mechanism computes relationships between all positions in the sequence.",
                "metadata": {
                    "title": "Understanding Transformers",
                    "url": "https://example.com/transformers",
                    "source_type": "web",
                    "relevance": 0.9,
                }
            },
            {
                "content": "BERT (Bidirectional Encoder Representations from Transformers) is a pre-trained language model. BERT uses masked language modeling and next sentence prediction.",
                "metadata": {
                    "title": "BERT Explained",
                    "url": "https://example.com/bert",
                    "source_type": "academic",
                    "relevance": 0.95,
                }
            },
            {
                "content": "Neural networks learn through backpropagation. The gradient descent algorithm updates weights to minimize the loss function.",
                "metadata": {
                    "title": "Neural Network Basics",
                    "url": "https://example.com/nn-basics",
                    "source_type": "web",
                    "relevance": 0.8,
                }
            },
            {
                "content": "GPT-3 is a large language model with 175 billion parameters. It uses a decoder-only transformer architecture and is trained on diverse internet text.",
                "metadata": {
                    "title": "GPT-3 Overview",
                    "url": "https://example.com/gpt3",
                    "source_type": "academic",
                    "relevance": 0.92,
                }
            },
        ]
        
        # Store documents
        print("\n📦 Storing documents in vector database...")
        for idx, doc in enumerate(sample_docs):
            embedding = await embedding_service.embed_text(doc["content"])
            
            await vector_store.store_vector(
                session_id=session_id,
                content=doc["content"],
                embedding=embedding,
                metadata=doc["metadata"],
            )
            
            print(f"  ✅ Stored doc {idx + 1}: {doc['metadata']['title']}")
        
        # Test queries
        test_queries = [
            ("transformer architecture", "Technical term - should favor keyword match"),
            ("BERT model", "Exact acronym - FTS should find this"),
            ("how do neural networks learn", "Semantic query - vector search strength"),
        ]
        
        print("\n" + "="*80)
        print("🔍 Testing Hybrid Search vs Vector-Only Search")
        print("="*80)
        
        for query, description in test_queries:
            print(f"\n📋 Query: '{query}'")
            print(f"   Description: {description}")
            print("-" * 80)
            
            # Generate query embedding
            query_embedding = await embedding_service.embed_text(query)
            
            # 1. Vector-only search
            print("\n   🎯 Vector-Only Search:")
            vector_results = await vector_store.similarity_search(
                session_id=session_id,
                query_vector=query_embedding,
                top_k=3,
            )
            
            for idx, result in enumerate(vector_results[:3], 1):
                print(f"      {idx}. [{result.similarity_score:.3f}] {result.metadata['title']}")
            
            # 2. Hybrid search (vector + FTS)
            print("\n   🔥 Hybrid Search (0.6 semantic + 0.4 keyword):")
            try:
                hybrid_results = await vector_store.hybrid_search(
                    session_id=session_id,
                    query_text=query,
                    query_vector=query_embedding,
                    top_k=3,
                    semantic_weight=0.6,
                    keyword_weight=0.4,
                )
                
                for idx, result in enumerate(hybrid_results[:3], 1):
                    print(f"      {idx}. [{result.similarity_score:.3f}] {result.metadata['title']}")
                    
            except Exception as e:
                print(f"      ❌ Error: {e}")
            
            # 3. Keyword-heavy hybrid (0.3 semantic + 0.7 keyword)
            print("\n   📝 Keyword-Heavy Hybrid (0.3 semantic + 0.7 keyword):")
            try:
                keyword_results = await vector_store.hybrid_search(
                    session_id=session_id,
                    query_text=query,
                    query_vector=query_embedding,
                    top_k=3,
                    semantic_weight=0.3,
                    keyword_weight=0.7,
                )
                
                for idx, result in enumerate(keyword_results[:3], 1):
                    print(f"      {idx}. [{result.similarity_score:.3f}] {result.metadata['title']}")
                    
            except Exception as e:
                print(f"      ❌ Error: {e}")
        
        print("\n" + "="*80)
        print("✅ Hybrid Search Test Complete!")
        print("="*80)
        
        # Cleanup
        deleted = await vector_store.delete_by_session(session_id)
        print(f"\n🗑️  Cleaned up {deleted} test documents")


if __name__ == "__main__":
    asyncio.run(test_hybrid_search())

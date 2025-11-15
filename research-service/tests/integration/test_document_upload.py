"""Test document upload and query functionality.

This script tests the new document endpoints:
1. Upload a test document
2. Query the document
3. List documents
4. Delete document
"""

import asyncio
import sys
from pathlib import Path

import httpx

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

API_BASE = "http://localhost:8001/api/v1"  # External port is 8001


async def test_document_endpoints():
    """Test all document endpoints."""
    print("🧪 Testing Document Upload Endpoints\n")

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Step 1: Create a test text file
        print("1️⃣ Creating test document...")
        test_content = """
# Introduction to AI Agents

AI agents are autonomous systems that can perceive their environment, make decisions, 
and take actions to achieve specific goals. They are a key component of artificial 
intelligence and are used in various applications.

## Key Characteristics

1. **Autonomy**: AI agents can operate without human intervention
2. **Reactivity**: They respond to changes in their environment
3. **Pro-activeness**: They take initiative to achieve goals
4. **Social ability**: They can interact with other agents and humans

## Types of AI Agents

- Simple reflex agents
- Model-based reflex agents
- Goal-based agents
- Utility-based agents
- Learning agents

## Applications

AI agents are used in:
- Robotics
- Game playing
- Virtual assistants
- Autonomous vehicles
- Trading systems
"""

        # Step 2: Upload document
        print("\n2️⃣ Uploading document...")
        files = {"file": ("test_doc.txt", test_content, "text/plain")}
        data = {"collection": "test"}

        response = await client.post(f"{API_BASE}/documents/upload", files=files, data=data)
        if response.status_code != 201:
            print(f"❌ Upload failed: {response.status_code}")
            print(response.text)
            return

        upload_result = response.json()
        print(f"✅ Upload successful!")
        print(f"   Document ID: {upload_result['document_id']}")
        print(f"   Chunks: {upload_result['chunks_created']}")
        print(f"   Embedding Dimension: {upload_result['embedding_dimension']}")

        document_id = upload_result["document_id"]

        # Step 3: Query document
        print("\n3️⃣ Querying document...")
        query_data = {
            "query": "What are the key characteristics of AI agents?",
            "collection": "test",
            "top_k": 5,
            "similarity_threshold": 0.3,
        }

        response = await client.post(f"{API_BASE}/documents/query", json=query_data)
        if response.status_code != 200:
            print(f"❌ Query failed: {response.status_code}")
            print(response.text)
            return

        query_result = response.json()
        print(f"✅ Query successful!")
        print(f"\n📝 Answer:\n{query_result['answer']}\n")
        print(f"📚 Sources found: {len(query_result['sources'])}")
        for i, source in enumerate(query_result["sources"][:3], 1):
            print(f"   [{i}] Similarity: {source['similarity']:.3f}")

        # Step 4: List documents
        print("\n4️⃣ Listing documents...")
        response = await client.get(f"{API_BASE}/documents?collection=test")
        if response.status_code != 200:
            print(f"❌ List failed: {response.status_code}")
            print(response.text)
            return

        list_result = response.json()
        print(f"✅ Found {list_result['total_count']} documents:")
        for doc in list_result["documents"]:
            print(f"   - {doc['filename']} ({doc['chunks_count']} chunks)")

        # Step 5: Delete document
        print("\n5️⃣ Deleting document...")
        response = await client.delete(f"{API_BASE}/documents/{document_id}")
        if response.status_code != 200:
            print(f"❌ Delete failed: {response.status_code}")
            print(response.text)
            return

        delete_result = response.json()
        print(f"✅ Document deleted!")
        print(f"   Chunks deleted: {delete_result['chunks_deleted']}")

        print("\n✅ All tests passed! 🎉")


if __name__ == "__main__":
    asyncio.run(test_document_endpoints())

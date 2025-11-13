#!/usr/bin/env python3
"""Test Document Library UI functionality via API."""

import httpx

API_BASE = "http://localhost:8001/api/v1"
TEST_FILE = "test_sample_document.txt"
COLLECTION = "pydantic-ai-docs"


def test_document_workflow():
    """Test complete document workflow: upload → query → list → delete."""
    print("🧪 Testing Document Library Workflow\n")

    # 1. Upload document
    print("1️⃣ Uploading document...")
    with open(TEST_FILE, "rb") as f:
        files = {"file": (TEST_FILE, f, "text/plain")}
        data = {"collection": COLLECTION}
        response = httpx.post(
            f"{API_BASE}/documents/upload",
            files=files,
            data=data,
            timeout=120.0,
        )

    if response.status_code == 201:
        result = response.json()
        document_id = result["document_id"]
        print(f"✅ Upload successful!")
        print(f"   📄 Document ID: {document_id}")
        print(f"   📦 Chunks: {result['chunks_created']}")
        print(f"   🧮 Dimension: {result['embedding_dimension']}")
        print(f"   📁 Collection: {result['collection']}\n")
    else:
        print(f"❌ Upload failed: {response.status_code}")
        print(response.text)
        return

    # 2. Query document
    print("2️⃣ Querying document...")
    response = httpx.post(
        f"{API_BASE}/documents/query",
        json={
            "query": "What are the key features of Pydantic AI?",
            "collection": COLLECTION,
            "top_k": 5,
            "similarity_threshold": 0.3,
        },
        timeout=60.0,
    )

    if response.status_code == 200:
        result = response.json()
        print(f"✅ Query successful!\n")
        print(f"📝 Answer:\n{result['answer']}\n")
        print(f"📊 Metadata:")
        print(f"   ⏱️  Time: {result['execution_time']:.2f}s")
        print(f"   📄 Chunks found: {result['total_chunks_found']}")
        print(f"   📚 Chunks used: {result['chunks_used']}\n")
        print(f"📚 Sources:")
        for idx, source in enumerate(result["sources"][:3], 1):
            print(f"   [{idx}] Similarity: {source['similarity']:.3f}")
            print(f"       {source['content'][:100]}...\n")
    else:
        print(f"❌ Query failed: {response.status_code}")
        print(response.text)

    # 3. List documents
    print("3️⃣ Listing documents...")
    response = httpx.get(
        f"{API_BASE}/documents",
        params={"collection": COLLECTION},
        timeout=30.0,
    )

    if response.status_code == 200:
        result = response.json()
        print(f"✅ Found {result['total_count']} document(s):")
        for doc in result["documents"]:
            print(f"   📄 {doc['filename']}")
            print(f"      ID: {doc['document_id']}")
            print(f"      Chunks: {doc['chunks_count']}")
            print(f"      Created: {doc['created_at']}\n")
    else:
        print(f"❌ List failed: {response.status_code}")
        print(response.text)

    # 4. Delete document
    print("4️⃣ Deleting document...")
    response = httpx.delete(
        f"{API_BASE}/documents/{document_id}",
        timeout=30.0,
    )

    if response.status_code == 200:
        result = response.json()
        print(f"✅ Document deleted!")
        print(f"   🗑️  Chunks deleted: {result['chunks_deleted']}\n")
    else:
        print(f"❌ Delete failed: {response.status_code}")
        print(response.text)

    print("✅ All tests completed! 🎉")
    print("\n📱 Now try the Streamlit UI at: http://localhost:8503")
    print("   Go to 'Document Library' mode → Upload tab → Upload a document!")


if __name__ == "__main__":
    test_document_workflow()

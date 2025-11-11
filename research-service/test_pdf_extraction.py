"""Test PDF extraction functionality."""

import asyncio
import httpx

async def test_pdf_search():
    """Test search with PDF results."""
    
    # Query that should return PDF results
    query = "attention is all you need paper pdf"
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        print(f"🔍 Searching for: {query}")
        
        response = await client.post(
            "http://localhost:8001/api/v1/search",
            json={"query": query, "mode": "balanced"}
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Check for PDF sources
            pdf_sources = [
                s for s in data.get("sources", []) 
                if ".pdf" in s["url"].lower()
            ]
            
            print(f"\n✅ Search completed successfully")
            print(f"📄 Found {len(pdf_sources)} PDF sources out of {len(data.get('sources', []))} total")
            
            for idx, source in enumerate(pdf_sources, 1):
                content_len = len(source.get("content", ""))
                has_content = content_len > 0
                
                print(f"\n  [{idx}] {source['title']}")
                print(f"      URL: {source['url']}")
                print(f"      Content extracted: {'✅ YES' if has_content else '❌ NO'}")
                if has_content:
                    print(f"      Content length: {content_len} chars")
                    print(f"      Content preview: {source['content'][:150]}...")
            
            if len(pdf_sources) == 0:
                print("\n⚠️  No PDF sources found in search results")
                print(f"   Total sources: {len(data.get('sources', []))}")
                
        else:
            print(f"❌ Search failed: {response.status_code}")
            print(f"   Error: {response.text}")

if __name__ == "__main__":
    asyncio.run(test_pdf_search())

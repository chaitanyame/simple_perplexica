"""
Test URL/PDF fetching functionality
"""

import asyncio
from app.utils.fetch_urls import fetch_and_process_urls


async def test_html_fetch():
    """Test HTML fetching and parsing"""
    print("\n=== Testing HTML Fetch ===")
    urls = ["https://www.python.org/about/"]
    docs = await fetch_and_process_urls(urls)

    print(f"Total documents: {len(docs)}")
    for i, doc in enumerate(docs[:2]):  # Show first 2 chunks
        print(f"\n--- Document {i + 1} ---")
        print(f"URL: {doc['url']}")
        print(f"Title: {doc['title']}")
        print(f"Content length: {len(doc['pageContent'])} chars")
        print(f"Preview: {doc['pageContent'][:300]}...")
        print(f"Metadata: {doc['metadata']}")


async def test_pdf_fetch():
    """Test PDF fetching and parsing"""
    print("\n=== Testing PDF Fetch ===")
    # Using a sample PDF from arXiv
    urls = ["https://arxiv.org/pdf/1706.03762.pdf"]  # Attention is All You Need paper
    docs = await fetch_and_process_urls(urls, max_chunks_per_url=2)

    print(f"Total documents: {len(docs)}")
    for i, doc in enumerate(docs[:2]):
        print(f"\n--- Document {i + 1} ---")
        print(f"URL: {doc['url']}")
        print(f"Title: {doc['title']}")
        print(f"Content length: {len(doc['pageContent'])} chars")
        print(f"Preview: {doc['pageContent'][:300]}...")
        print(f"Failed: {doc['metadata'].get('failed', False)}")


async def test_mixed_urls():
    """Test mixed HTML and PDF URLs"""
    print("\n=== Testing Mixed URLs ===")
    urls = [
        "https://www.python.org/",
        "https://fastapi.tiangolo.com/",
    ]
    docs = await fetch_and_process_urls(urls, max_chunks_per_url=1)

    print(f"Total documents: {len(docs)}")
    for doc in docs:
        print(f"\nURL: {doc['url']}")
        print(f"Success: {not doc['metadata'].get('failed', False)}")
        print(f"Content length: {len(doc['pageContent'])} chars")


async def test_failed_url():
    """Test handling of failed URLs"""
    print("\n=== Testing Failed URL ===")
    urls = ["https://this-url-does-not-exist-12345.com/"]
    docs = await fetch_and_process_urls(urls)

    print(f"Total documents: {len(docs)}")
    for doc in docs:
        print(f"\nURL: {doc['url']}")
        print(f"Failed: {doc['metadata'].get('failed', False)}")
        print(f"Error: {doc['metadata'].get('error', 'N/A')}")
        print(f"Content: {doc['pageContent']}")


async def main():
    print("=" * 60)
    print("URL/PDF Fetching Tests")
    print("=" * 60)

    await test_html_fetch()
    await test_mixed_urls()
    await test_failed_url()
    # PDF test can be slow, uncomment if needed
    # await test_pdf_fetch()

    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

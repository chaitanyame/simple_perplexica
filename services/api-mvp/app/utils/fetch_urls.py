"""
Fetch and process URLs/PDFs similar to Perplexica's getDocumentsFromLinks.
Fetches content, parses HTML/PDF, chunks text, and returns documents.
"""

import logging
from typing import List, Dict, Any
import httpx
from bs4 import BeautifulSoup
from pypdf import PdfReader
from io import BytesIO

logger = logging.getLogger(__name__)

# Chunking configuration
CHUNK_SIZE = 2000
CHUNK_OVERLAP = 200


def _chunk_text(
    text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP
) -> List[str]:
    """
    Split text into overlapping chunks.
    Similar to RecursiveCharacterTextSplitter behavior.
    """
    if not text or len(text) <= chunk_size:
        return [text] if text else []

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap  # overlap for context continuity

    return chunks


async def _fetch_url_content(url: str, timeout: int = 10) -> Dict[str, Any]:
    """
    Fetch content from a URL and return parsed text.
    Returns dict with 'success', 'text', 'error' keys.
    """
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                },
            )
            response.raise_for_status()

            content_type = response.headers.get("content-type", "").lower()

            # PDF handling
            if "application/pdf" in content_type or url.lower().endswith(".pdf"):
                try:
                    pdf_file = BytesIO(response.content)
                    reader = PdfReader(pdf_file)
                    text_parts = []
                    for page in reader.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text_parts.append(page_text)
                    text = "\n".join(text_parts)
                    return {"success": True, "text": text, "error": None}
                except Exception as e:
                    logger.warning(f"PDF parsing failed for {url}: {e}")
                    return {
                        "success": False,
                        "text": "",
                        "error": f"PDF parsing error: {str(e)}",
                    }

            # HTML handling
            else:
                try:
                    soup = BeautifulSoup(response.text, "lxml")
                    # Remove script and style elements
                    for script in soup(["script", "style", "nav", "footer", "header"]):
                        script.decompose()

                    # Get text
                    text = soup.get_text(separator="\n", strip=True)
                    # Clean up whitespace
                    lines = (line.strip() for line in text.splitlines())
                    text = "\n".join(line for line in lines if line)

                    return {"success": True, "text": text, "error": None}
                except Exception as e:
                    logger.warning(f"HTML parsing failed for {url}: {e}")
                    return {
                        "success": False,
                        "text": "",
                        "error": f"HTML parsing error: {str(e)}",
                    }

    except httpx.TimeoutException:
        logger.warning(f"Timeout fetching {url}")
        return {"success": False, "text": "", "error": "Request timeout"}
    except httpx.HTTPStatusError as e:
        logger.warning(f"HTTP error fetching {url}: {e.response.status_code}")
        return {"success": False, "text": "", "error": f"HTTP {e.response.status_code}"}
    except Exception as e:
        logger.warning(f"Error fetching {url}: {e}")
        return {"success": False, "text": "", "error": str(e)}


async def fetch_and_process_urls(
    urls: List[str], max_chunks_per_url: int = 10
) -> List[Dict[str, Any]]:
    """
    Fetch URLs, parse content, chunk text, and return document objects.

    Args:
        urls: List of URLs to fetch
        max_chunks_per_url: Maximum number of chunks per URL (default: 10)

    Returns:
        List of document dicts with 'url', 'title', 'pageContent', 'metadata'
    """
    documents = []

    for url in urls:
        try:
            result = await _fetch_url_content(url)

            if not result["success"]:
                # Add failed document marker
                documents.append(
                    {
                        "url": url,
                        "title": url,
                        "pageContent": f"Failed to retrieve content: {result['error']}",
                        "metadata": {
                            "url": url,
                            "failed": True,
                            "error": result["error"],
                        },
                    }
                )
                continue

            text = result["text"]
            if not text or len(text.strip()) < 50:
                # Too short or empty
                documents.append(
                    {
                        "url": url,
                        "title": url,
                        "pageContent": "Content too short or empty",
                        "metadata": {"url": url, "failed": True, "error": "No content"},
                    }
                )
                continue

            # Chunk the text
            chunks = _chunk_text(text)

            # Limit chunks per URL
            chunks = chunks[:max_chunks_per_url]

            # Create documents from chunks
            for i, chunk in enumerate(chunks):
                documents.append(
                    {
                        "url": url,
                        "title": f"{url} (chunk {i + 1}/{len(chunks)})",
                        "pageContent": chunk,
                        "metadata": {
                            "url": url,
                            "chunk_index": i,
                            "total_chunks": len(chunks),
                            "failed": False,
                        },
                    }
                )

            logger.info(f"Processed {url}: {len(chunks)} chunks")

        except Exception as e:
            logger.error(f"Unexpected error processing {url}: {e}")
            documents.append(
                {
                    "url": url,
                    "title": url,
                    "pageContent": f"Unexpected error: {str(e)}",
                    "metadata": {"url": url, "failed": True, "error": str(e)},
                }
            )

    return documents

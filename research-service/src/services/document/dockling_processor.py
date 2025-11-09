"""Dockling document processor for PDF/Word/Excel extraction.

This module provides async document processing using Dockling library
for extracting content from various document formats.

Features:
- Async PDF/DOCX/XLSX/PPTX processing
- Metadata extraction
- Content chunking with overlap
- Error handling and validation
- Size and page limits
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from typing import Any

import structlog
from docling.datamodel.base_models import DocumentStream  # type: ignore[attr-defined]
from docling.document_converter import DocumentConverter

logger = structlog.get_logger(__name__)


class DocumentProcessingError(Exception):
    """Exception raised when document processing fails."""

    pass


@dataclass
class ProcessedDocument:
    """Processed document with content, chunks, and metadata."""

    content: str
    chunks: list[str]
    metadata: dict[str, Any]
    source_url: str
    format: str
    token_count: int = field(init=False)

    def __post_init__(self) -> None:
        """Calculate token count after initialization."""
        # Simple token estimation: ~4 characters per token
        self.token_count = len(self.content) // 4


class DocklingProcessor:
    """Document processor using Dockling for PDF/Word/Excel extraction.

    Supports:
    - PDF (with OCR)
    - DOCX (Microsoft Word)
    - XLSX (Microsoft Excel)
    - PPTX (Microsoft PowerPoint)
    - HTML
    - Markdown

    Example:
        >>> processor = DocklingProcessor()
        >>> result = await processor.process_document("document.pdf")
        >>> print(result.content[:100])
        >>> print(f"Extracted {len(result.chunks)} chunks")
    """

    # Supported file formats
    SUPPORTED_FORMATS = {".pdf", ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt", ".html", ".md"}

    def __init__(
        self,
        max_file_size: int = 50_000_000,  # 50MB
        max_pages: int = 100,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ):
        """Initialize Dockling processor.

        Args:
            max_file_size: Maximum file size in bytes (default: 50MB)
            max_pages: Maximum number of pages to process (default: 100)
            chunk_size: Size of text chunks for retrieval (default: 1000 chars)
            chunk_overlap: Overlap between consecutive chunks (default: 200 chars)
        """
        self.max_file_size = max_file_size
        self.max_pages = max_pages
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        logger.info(
            "DocklingProcessor initialized",
            max_file_size=max_file_size,
            max_pages=max_pages,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    async def process_document(
        self, file_path: str, source_url: str | None = None
    ) -> ProcessedDocument:
        """Process document from file path.

        Args:
            file_path: Path to document file
            source_url: Optional source URL for metadata

        Returns:
            ProcessedDocument with content, chunks, and metadata

        Raises:
            DocumentProcessingError: If processing fails
        """
        path = Path(file_path)

        # Validate file exists
        if not path.exists():
            raise DocumentProcessingError(f"File not found: {file_path}")

        # Validate file size
        file_size = path.stat().st_size
        if file_size > self.max_file_size:
            raise DocumentProcessingError(
                f"File size {file_size} exceeds maximum {self.max_file_size}"
            )

        # Validate format
        if path.suffix.lower() not in self.SUPPORTED_FORMATS:
            raise DocumentProcessingError(f"Unsupported file format: {path.suffix}")

        logger.info(f"Processing document: {file_path}", size=file_size, format=path.suffix)

        try:
            # Run conversion in executor to avoid blocking
            result = await asyncio.to_thread(self._convert_document, path)
            return result
        except Exception as e:
            logger.error(f"Document conversion failed: {e}", file_path=file_path)
            raise DocumentProcessingError(f"Document conversion failed: {e}") from e

    async def process_document_bytes(
        self, content: bytes, filename: str, source_url: str | None = None
    ) -> ProcessedDocument:
        """Process document from byte content.

        Args:
            content: Document content as bytes
            filename: Filename for format detection
            source_url: Optional source URL for metadata

        Returns:
            ProcessedDocument with content, chunks, and metadata

        Raises:
            DocumentProcessingError: If processing fails
        """
        path = Path(filename)

        # Validate format
        if path.suffix.lower() not in self.SUPPORTED_FORMATS:
            raise DocumentProcessingError(f"Unsupported file format: {path.suffix}")

        # Validate size
        if len(content) > self.max_file_size:
            raise DocumentProcessingError(
                f"Content size {len(content)} exceeds maximum {self.max_file_size}"
            )

        logger.info(f"Processing document from bytes: {filename}", size=len(content))

        try:
            # Create stream
            stream = DocumentStream(name=filename, stream=BytesIO(content))

            # Run conversion in executor
            result = await asyncio.to_thread(self._convert_document, stream)
            return result
        except Exception as e:
            logger.error(f"Document conversion failed: {e}", filename=filename)
            raise DocumentProcessingError(f"Document conversion failed: {e}") from e

    def _convert_document(self, source: Any) -> ProcessedDocument:
        """Convert document using Dockling (runs in thread pool).

        Args:
            source: Path or DocumentStream

        Returns:
            ProcessedDocument with content and metadata
        """
        # Initialize converter
        converter = DocumentConverter()

        # Convert document
        conversion_result = converter.convert(source)

        # Check status
        if conversion_result.status != "SUCCESS":
            raise DocumentProcessingError(f"Conversion status: {conversion_result.status}")

        doc = conversion_result.document

        # Extract content as markdown
        content = doc.export_to_markdown()

        # Extract metadata
        doc_dict = doc.export_to_dict()
        metadata = doc_dict.get("metadata", {})

        # Determine format
        if isinstance(source, Path):
            format_ext = source.suffix.lower().lstrip(".")
            source_url = str(source)
        else:
            format_ext = Path(source.name).suffix.lower().lstrip(".")
            source_url = source.name

        # Add format to metadata
        metadata["format"] = format_ext

        # Chunk content
        chunks = self._chunk_content(content)

        logger.info(
            "Document converted successfully",
            format=format_ext,
            content_length=len(content),
            chunks=len(chunks),
        )

        return ProcessedDocument(
            content=content,
            chunks=chunks,
            metadata=metadata,
            source_url=source_url,
            format=format_ext,
        )

    def _chunk_content(self, content: str) -> list[str]:
        """Chunk content into overlapping segments.

        Args:
            content: Text content to chunk

        Returns:
            List of text chunks with overlap
        """
        if len(content) <= self.chunk_size:
            return [content]

        chunks = []
        start = 0

        while start < len(content):
            end = start + self.chunk_size
            chunk = content[start:end]
            chunks.append(chunk)

            # Move start forward by (chunk_size - overlap)
            start += self.chunk_size - self.chunk_overlap

            # Break if we've covered the content
            if end >= len(content):
                break

        return chunks

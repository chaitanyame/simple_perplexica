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

# Fallback PDF extractors
try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    from PyPDF2 import PdfReader
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

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

        # For PDFs, try Dockling first, then fallback to simpler extractors
        is_pdf = path.suffix.lower() == '.pdf'
        
        if is_pdf:
            # Try Dockling first
            try:
                stream = DocumentStream(name=filename, stream=BytesIO(content))
                result = await asyncio.to_thread(self._convert_document, stream)
                logger.info(f"✅ Dockling extraction successful: {filename}")
                return result
            except Exception as dockling_error:
                logger.warning(
                    f"⚠️  Dockling failed for {filename}, trying fallback extractors",
                    error=str(dockling_error)[:100]
                )
                
                # Try pdfplumber fallback
                if PDFPLUMBER_AVAILABLE:
                    try:
                        logger.info(f"Trying pdfplumber for {filename}")
                        text = await asyncio.to_thread(self._extract_pdf_with_pdfplumber, content)
                        
                        if text and len(text.strip()) > 100:  # Ensure we got meaningful content
                            chunks = self._chunk_content(text)
                            logger.info(
                                f"✅ pdfplumber extraction successful: {filename}",
                                content_length=len(text),
                                chunks=len(chunks)
                            )
                            return ProcessedDocument(
                                content=text,
                                chunks=chunks,
                                metadata={"format": "pdf", "extractor": "pdfplumber"},
                                source_url=source_url or filename,
                                format="pdf"
                            )
                    except Exception as pdfplumber_error:
                        logger.warning(f"pdfplumber failed: {pdfplumber_error}")
                
                # Try PyPDF2 fallback
                if PYPDF2_AVAILABLE:
                    try:
                        logger.info(f"Trying PyPDF2 for {filename}")
                        text = await asyncio.to_thread(self._extract_pdf_with_pypdf2, content)
                        
                        if text and len(text.strip()) > 100:
                            chunks = self._chunk_content(text)
                            logger.info(
                                f"✅ PyPDF2 extraction successful: {filename}",
                                content_length=len(text),
                                chunks=len(chunks)
                            )
                            return ProcessedDocument(
                                content=text,
                                chunks=chunks,
                                metadata={"format": "pdf", "extractor": "pypdf2"},
                                source_url=source_url or filename,
                                format="pdf"
                            )
                    except Exception as pypdf2_error:
                        logger.warning(f"PyPDF2 failed: {pypdf2_error}")
                
                # All extractors failed
                logger.error(f"❌ All PDF extractors failed for {filename}")
                raise DocumentProcessingError(
                    f"All PDF extraction methods failed. Dockling error: {str(dockling_error)[:100]}"
                ) from dockling_error
        
        else:
            # Non-PDF documents: use Dockling only
            try:
                stream = DocumentStream(name=filename, stream=BytesIO(content))
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

        # Check status - conversion_result.status is an enum (ConversionStatus.SUCCESS)
        # We can access the document if conversion didn't completely fail
        if not conversion_result.document:
            raise DocumentProcessingError(f"Conversion failed: no document returned")

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

    def _extract_pdf_with_pdfplumber(self, content: bytes) -> str:
        """Extract text from PDF using pdfplumber (fallback method).

        Args:
            content: PDF file content as bytes

        Returns:
            Extracted text content

        Raises:
            DocumentProcessingError: If extraction fails
        """
        if not PDFPLUMBER_AVAILABLE:
            raise DocumentProcessingError("pdfplumber not available")

        try:
            with pdfplumber.open(BytesIO(content)) as pdf:
                text_parts = []
                for page in pdf.pages[:self.max_pages]:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                
                return "\n\n".join(text_parts)
        except Exception as e:
            raise DocumentProcessingError(f"pdfplumber extraction failed: {e}") from e

    def _extract_pdf_with_pypdf2(self, content: bytes) -> str:
        """Extract text from PDF using PyPDF2 (fallback method).

        Args:
            content: PDF file content as bytes

        Returns:
            Extracted text content

        Raises:
            DocumentProcessingError: If extraction fails
        """
        if not PYPDF2_AVAILABLE:
            raise DocumentProcessingError("PyPDF2 not available")

        try:
            reader = PdfReader(BytesIO(content))
            text_parts = []
            
            for page_num, page in enumerate(reader.pages[:self.max_pages]):
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            
            return "\n\n".join(text_parts)
        except Exception as e:
            raise DocumentProcessingError(f"PyPDF2 extraction failed: {e}") from e

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

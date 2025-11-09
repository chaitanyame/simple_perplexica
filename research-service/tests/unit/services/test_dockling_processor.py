"""Tests for Dockling document processor.

Following TDD RED-GREEN-REFACTOR:
- RED: Write tests first (they should fail - module doesn't exist yet)
- GREEN: Implement minimal code to pass tests
- REFACTOR: Clean up while keeping tests green

Test Coverage:
- DocklingProcessor initialization
- PDF document processing
- DOCX/Excel document processing
- Error handling
- Metadata extraction
- Content chunking
- Async operations
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from src.services.document.dockling_processor import DocklingProcessor, ProcessedDocument


class TestDocklingProcessorInitialization:
    """Test DocklingProcessor initialization."""

    def test_init_with_defaults(self) -> None:
        """Test initialization with default parameters."""
        processor = DocklingProcessor()

        assert processor.max_file_size > 0
        assert processor.max_pages > 0
        assert processor.chunk_size > 0
        assert processor.chunk_overlap >= 0

    def test_init_with_custom_parameters(self) -> None:
        """Test initialization with custom parameters."""
        processor = DocklingProcessor(
            max_file_size=100_000_000,
            max_pages=200,
            chunk_size=2000,
            chunk_overlap=300,
        )

        assert processor.max_file_size == 100_000_000
        assert processor.max_pages == 200
        assert processor.chunk_size == 2000
        assert processor.chunk_overlap == 300


class TestDocklingProcessorPDFProcessing:
    """Test PDF document processing."""

    @pytest.fixture
    def processor(self) -> DocklingProcessor:
        """Create a DocklingProcessor instance."""
        return DocklingProcessor()

    @pytest.fixture
    def mock_docling_result(self) -> Mock:
        """Create a mock Docling conversion result."""
        mock_result = Mock()
        mock_result.status = "SUCCESS"
        mock_doc = Mock()
        mock_doc.export_to_markdown.return_value = "# Test Document\n\nThis is test content."
        mock_doc.export_to_dict.return_value = {
            "content": "Test content",
            "metadata": {"title": "Test Document", "pages": 1},
        }
        mock_result.document = mock_doc
        return mock_result

    @pytest.mark.asyncio
    async def test_process_pdf_success(
        self, processor: DocklingProcessor, mock_docling_result: Mock
    ) -> None:
        """Test successful PDF processing."""
        with patch("src.services.document.dockling_processor.DocumentConverter") as mock_converter:
            with patch("pathlib.Path.exists", return_value=True):
                with patch("pathlib.Path.stat") as mock_stat:
                    mock_stat.return_value.st_size = 1000
                    mock_instance = Mock()
                    mock_instance.convert.return_value = mock_docling_result
                    mock_converter.return_value = mock_instance

                    result = await processor.process_document(
                        file_path="test.pdf", source_url="https://example.com/test.pdf"
                    )

                    assert isinstance(result, ProcessedDocument)
                    assert result.content == "# Test Document\n\nThis is test content."
                    assert result.source_url == "test.pdf"  # source_url from file path, not param
                    assert result.metadata["title"] == "Test Document"
                    assert result.metadata["pages"] == 1
                    assert len(result.chunks) > 0

    @pytest.mark.asyncio
    async def test_process_pdf_from_bytes(
        self, processor: DocklingProcessor, mock_docling_result: Mock
    ) -> None:
        """Test PDF processing from byte stream."""
        pdf_bytes = b"%PDF-1.4 fake content"

        with patch("src.services.document.dockling_processor.DocumentConverter") as mock_converter:
            with patch("src.services.document.dockling_processor.DocumentStream") as mock_stream:
                mock_instance = Mock()
                mock_instance.convert.return_value = mock_docling_result
                mock_converter.return_value = mock_instance

                result = await processor.process_document_bytes(
                    content=pdf_bytes,
                    filename="test.pdf",
                    source_url="https://example.com/test.pdf",
                )

                assert isinstance(result, ProcessedDocument)
                mock_stream.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_pdf_with_chunking(
        self, processor: DocklingProcessor, mock_docling_result: Mock
    ) -> None:
        """Test PDF processing with content chunking."""
        # Create longer content to ensure multiple chunks
        long_content = "Test content. " * 500  # Create content longer than default chunk size
        mock_docling_result.document.export_to_markdown.return_value = long_content

        with patch("src.services.document.dockling_processor.DocumentConverter") as mock_converter:
            with patch("pathlib.Path.exists", return_value=True):
                with patch("pathlib.Path.stat") as mock_stat:
                    mock_stat.return_value.st_size = 1000
                    mock_instance = Mock()
                    mock_instance.convert.return_value = mock_docling_result
                    mock_converter.return_value = mock_instance

                    result = await processor.process_document(file_path="test.pdf")

                    # Should have multiple chunks due to long content
                    assert len(result.chunks) > 1
                    # Each chunk should respect size limits
                    assert all(len(chunk) <= processor.chunk_size for chunk in result.chunks)


class TestDocklingProcessorDocxExcelProcessing:
    """Test DOCX and Excel document processing."""

    @pytest.fixture
    def processor(self) -> DocklingProcessor:
        """Create a DocklingProcessor instance."""
        return DocklingProcessor()

    @pytest.mark.asyncio
    async def test_process_docx_success(self, processor: DocklingProcessor) -> None:
        """Test successful DOCX processing."""
        mock_result = Mock()
        mock_result.status = "SUCCESS"
        mock_doc = Mock()
        mock_doc.export_to_markdown.return_value = "# Word Document\n\nContent from Word."
        mock_doc.export_to_dict.return_value = {"content": "Word content", "metadata": {}}
        mock_result.document = mock_doc

        with patch("src.services.document.dockling_processor.DocumentConverter") as mock_converter:
            with patch("pathlib.Path.exists", return_value=True):
                with patch("pathlib.Path.stat") as mock_stat:
                    mock_stat.return_value.st_size = 1000
                    mock_instance = Mock()
                    mock_instance.convert.return_value = mock_result
                    mock_converter.return_value = mock_instance

                    result = await processor.process_document(file_path="test.docx")

                    assert result.content == "# Word Document\n\nContent from Word."
                    assert result.metadata.get("format") == "docx"

    @pytest.mark.asyncio
    async def test_process_excel_success(self, processor: DocklingProcessor) -> None:
        """Test successful Excel processing."""
        mock_result = Mock()
        mock_result.status = "SUCCESS"
        mock_doc = Mock()
        mock_doc.export_to_markdown.return_value = (
            "| Header1 | Header2 |\n| --- | --- |\n| Data1 | Data2 |"
        )
        mock_doc.export_to_dict.return_value = {"content": "Excel data", "metadata": {}}
        mock_result.document = mock_doc

        with patch("src.services.document.dockling_processor.DocumentConverter") as mock_converter:
            with patch("pathlib.Path.exists", return_value=True):
                with patch("pathlib.Path.stat") as mock_stat:
                    mock_stat.return_value.st_size = 1000
                    mock_instance = Mock()
                    mock_instance.convert.return_value = mock_result
                    mock_converter.return_value = mock_instance

                    result = await processor.process_document(file_path="test.xlsx")

                    assert "Header1" in result.content
                    assert "Header2" in result.content
                    assert result.metadata.get("format") == "xlsx"


class TestDocklingProcessorErrorHandling:
    """Test error handling in document processor."""

    @pytest.fixture
    def processor(self) -> DocklingProcessor:
        """Create a DocklingProcessor instance."""
        return DocklingProcessor()

    @pytest.mark.asyncio
    async def test_process_nonexistent_file(self, processor: DocklingProcessor) -> None:
        """Test processing nonexistent file raises error."""
        from src.services.document.dockling_processor import DocumentProcessingError

        with pytest.raises(DocumentProcessingError) as exc_info:
            await processor.process_document(file_path="/nonexistent/file.pdf")

        assert "not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_process_file_too_large(self, processor: DocklingProcessor) -> None:
        """Test processing file exceeding size limit."""
        from src.services.document.dockling_processor import DocumentProcessingError

        processor.max_file_size = 100  # Set very small limit

        with patch("pathlib.Path.stat") as mock_stat:
            mock_stat.return_value.st_size = 1000  # File larger than limit
            with patch("pathlib.Path.exists", return_value=True):
                with pytest.raises(DocumentProcessingError) as exc_info:
                    await processor.process_document(file_path="large_file.pdf")

                assert "exceeds maximum" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_process_unsupported_format(self, processor: DocklingProcessor) -> None:
        """Test processing unsupported file format."""
        from src.services.document.dockling_processor import DocumentProcessingError

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.stat") as mock_stat:
                mock_stat.return_value.st_size = 1000
                with pytest.raises(DocumentProcessingError) as exc_info:
                    await processor.process_document(file_path="test.unsupported")

                assert "unsupported" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_process_conversion_failure(self, processor: DocklingProcessor) -> None:
        """Test handling of Docling conversion failure."""
        from src.services.document.dockling_processor import DocumentProcessingError

        with patch("src.services.document.dockling_processor.DocumentConverter") as mock_converter:
            mock_instance = Mock()
            mock_instance.convert.side_effect = Exception("Conversion failed")
            mock_converter.return_value = mock_instance

            with patch("pathlib.Path.exists", return_value=True):
                with patch("pathlib.Path.stat") as mock_stat:
                    mock_stat.return_value.st_size = 1000
                    with pytest.raises(DocumentProcessingError) as exc_info:
                        await processor.process_document(file_path="test.pdf")

                    assert "conversion failed" in str(exc_info.value).lower()


class TestDocklingProcessorMetadataExtraction:
    """Test metadata extraction from documents."""

    @pytest.fixture
    def processor(self) -> DocklingProcessor:
        """Create a DocklingProcessor instance."""
        return DocklingProcessor()

    @pytest.mark.asyncio
    async def test_extract_basic_metadata(self, processor: DocklingProcessor) -> None:
        """Test extraction of basic document metadata."""
        mock_result = Mock()
        mock_result.status = "SUCCESS"
        mock_doc = Mock()
        mock_doc.export_to_markdown.return_value = "# Title\n\nContent"
        mock_doc.export_to_dict.return_value = {
            "content": "Test",
            "metadata": {
                "title": "Test Document",
                "author": "Test Author",
                "creation_date": "2025-01-01",
                "page_count": 5,
            },
        }
        mock_result.document = mock_doc

        with patch("src.services.document.dockling_processor.DocumentConverter") as mock_converter:
            with patch("pathlib.Path.exists", return_value=True):
                with patch("pathlib.Path.stat") as mock_stat:
                    mock_stat.return_value.st_size = 1000
                    mock_instance = Mock()
                    mock_instance.convert.return_value = mock_result
                    mock_converter.return_value = mock_instance

                    result = await processor.process_document(file_path="test.pdf")

                    assert result.metadata["title"] == "Test Document"
                    assert result.metadata["author"] == "Test Author"
                    assert result.metadata["creation_date"] == "2025-01-01"
                    assert result.metadata["page_count"] == 5

    @pytest.mark.asyncio
    async def test_extract_format_metadata(self, processor: DocklingProcessor) -> None:
        """Test extraction of format-specific metadata."""
        mock_result = Mock()
        mock_result.status = "SUCCESS"
        mock_doc = Mock()
        mock_doc.export_to_markdown.return_value = "Content"
        mock_doc.export_to_dict.return_value = {"content": "Test", "metadata": {}}
        mock_result.document = mock_doc

        with patch("src.services.document.dockling_processor.DocumentConverter") as mock_converter:
            with patch("pathlib.Path.exists", return_value=True):
                with patch("pathlib.Path.stat") as mock_stat:
                    mock_stat.return_value.st_size = 1000
                    mock_instance = Mock()
                    mock_instance.convert.return_value = mock_result
                    mock_converter.return_value = mock_instance

                    result = await processor.process_document(file_path="test.pdf")

                    # Should include format in metadata
                    assert "format" in result.metadata
                    assert result.metadata["format"] == "pdf"


class TestDocklingProcessorChunking:
    """Test content chunking strategies."""

    @pytest.fixture
    def processor(self) -> DocklingProcessor:
        """Create a DocklingProcessor with small chunk size for testing."""
        return DocklingProcessor(chunk_size=100, chunk_overlap=20)

    def test_chunk_respects_size_limit(self, processor: DocklingProcessor) -> None:
        """Test that chunks respect the maximum size."""
        content = "A" * 500  # Create content much larger than chunk size

        chunks = processor._chunk_content(content)

        # All chunks should be at most chunk_size
        assert all(len(chunk) <= processor.chunk_size for chunk in chunks)

    def test_chunk_has_overlap(self, processor: DocklingProcessor) -> None:
        """Test that consecutive chunks have overlap."""
        content = "Word " * 100  # Create repeatable content

        chunks = processor._chunk_content(content)

        # Should have multiple chunks
        assert len(chunks) >= 2

        # Check overlap exists between consecutive chunks
        for i in range(len(chunks) - 1):
            # Last part of current chunk should appear in next chunk
            current_end = chunks[i][-processor.chunk_overlap :]
            next_start = chunks[i + 1][: processor.chunk_overlap]
            # There should be some overlap
            assert len(current_end) > 0 and len(next_start) > 0

    def test_chunk_small_content(self, processor: DocklingProcessor) -> None:
        """Test chunking of content smaller than chunk size."""
        content = "Small content"

        chunks = processor._chunk_content(content)

        # Should return single chunk
        assert len(chunks) == 1
        assert chunks[0] == content


class TestDocklingProcessorAsyncOperations:
    """Test async operation handling."""

    @pytest.fixture
    def processor(self) -> DocklingProcessor:
        """Create a DocklingProcessor instance."""
        return DocklingProcessor()

    @pytest.mark.asyncio
    async def test_concurrent_processing(self, processor: DocklingProcessor) -> None:
        """Test processing multiple documents concurrently."""
        import asyncio

        mock_result = Mock()
        mock_result.status = "SUCCESS"
        mock_doc = Mock()
        mock_doc.export_to_markdown.return_value = "Content"
        mock_doc.export_to_dict.return_value = {"content": "Test", "metadata": {}}
        mock_result.document = mock_doc

        with patch("src.services.document.dockling_processor.DocumentConverter") as mock_converter:
            with patch("pathlib.Path.exists", return_value=True):
                with patch("pathlib.Path.stat") as mock_stat:
                    mock_stat.return_value.st_size = 1000
                    mock_instance = Mock()
                    mock_instance.convert.return_value = mock_result
                    mock_converter.return_value = mock_instance

                    # Process multiple documents concurrently
                    tasks = [processor.process_document(file_path=f"test{i}.pdf") for i in range(3)]
                    results = await asyncio.gather(*tasks)

                    assert len(results) == 3
                    assert all(isinstance(r, ProcessedDocument) for r in results)


class TestProcessedDocument:
    """Test ProcessedDocument data class."""

    def test_processed_document_creation(self) -> None:
        """Test creating a ProcessedDocument instance."""
        doc = ProcessedDocument(
            content="Test content",
            chunks=["chunk1", "chunk2"],
            metadata={"title": "Test"},
            source_url="https://example.com/doc.pdf",
            format="pdf",
        )

        assert doc.content == "Test content"
        assert len(doc.chunks) == 2
        assert doc.metadata["title"] == "Test"
        assert doc.source_url == "https://example.com/doc.pdf"
        assert doc.format == "pdf"

    def test_processed_document_token_count(self) -> None:
        """Test token count estimation in ProcessedDocument."""
        content = "word " * 100  # 100 words
        doc = ProcessedDocument(
            content=content, chunks=["chunk"], metadata={}, source_url="", format="pdf"
        )

        # Simple estimation: ~1 token per 4 characters
        estimated_tokens = len(content) // 4
        assert doc.token_count > 0
        assert abs(doc.token_count - estimated_tokens) < estimated_tokens * 0.5  # Within 50%

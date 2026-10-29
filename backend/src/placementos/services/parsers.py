"""File Parsers, Safety Scanners, and Text Extraction Service.

Extracts plain text with precise page and paragraph locators from PDF, DOCX,
and plain text while enforcing strict decompression limits, magic byte checks,
and corruption/encryption detection.
"""

from __future__ import annotations

import io
import zipfile
from dataclasses import asdict, dataclass
from typing import Any

import pypdf
from docx import Document


class ParseError(Exception):
    """Base error for document parsing failures."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class OversizedFileError(ParseError):
    def __init__(self, message: str = "File size exceeds the 15MB limit") -> None:
        super().__init__("OVERSIZED_FILE", message)


class MimeTypeMismatchError(ParseError):
    def __init__(self, message: str = "File content headers do not match claimed file type") -> None:
        super().__init__("MIMETYPE_MISMATCH", message)


class CorruptFileError(ParseError):
    def __init__(self, message: str = "Document is corrupt or unreadable") -> None:
        super().__init__("CORRUPT_FILE", message)


class EncryptedFileError(ParseError):
    def __init__(self, message: str = "Encrypted or password-protected documents are not supported") -> None:
        super().__init__("ENCRYPTED_FILE", message)


class DecompressionBombError(ParseError):
    def __init__(self, message: str = "File triggered decompression bomb safety threshold") -> None:
        super().__init__("DECOMPRESSION_BOMB", message)


class EmptyOrScannedError(ParseError):
    def __init__(self, message: str = "Document contains no extractable text (likely an image-only scan)") -> None:
        super().__init__("EMPTY_OR_SCANNED", message)


@dataclass
class TextLocator:
    """Represents a traceable location within extracted document source."""

    locator_type: str  # "page" or "paragraph"
    paragraph_index: int
    char_offset_start: int
    char_offset_end: int
    preview: str
    page_number: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ExtractionResult:
    """Outcome of document text extraction."""

    extracted_text: str
    locators: list[TextLocator]
    page_count: int | None
    paragraph_count: int
    is_empty_or_scanned: bool
    parser_version: str = "1.0.0"

    def to_dict(self) -> dict[str, Any]:
        return {
            "extracted_text": self.extracted_text,
            "locators": [loc.to_dict() for loc in self.locators],
            "page_count": self.page_count,
            "paragraph_count": self.paragraph_count,
            "is_empty_or_scanned": self.is_empty_or_scanned,
            "parser_version": self.parser_version,
        }


class DocumentScanner:
    """Pre-scan validation for file limits, magic headers, and compression safety."""

    MAX_FILE_BYTES = 15 * 1024 * 1024  # 15 MB
    MAX_UNCOMPRESSED_BYTES = 30 * 1024 * 1024  # 30 MB
    MAX_COMPRESSION_RATIO = 25.0
    MAX_PDF_PAGES = 50
    MAX_DOCX_PARAGRAPHS = 5000

    @classmethod
    def scan_bytes(cls, data: bytes, extension: str) -> str:
        """Validate size, magic bytes, and sniff real format. Returns canonical type ('pdf', 'docx', 'text')."""
        if len(data) > cls.MAX_FILE_BYTES:
            raise OversizedFileError(f"File size {len(data)} exceeds maximum allowed {cls.MAX_FILE_BYTES} bytes")

        if len(data) == 0:
            raise CorruptFileError("Uploaded file is empty (0 bytes)")

        clean_ext = extension.lower().strip().lstrip(".")

        # Check for executable magic headers (MZ, ELF, Mach-O)
        if data.startswith(b"MZ") or data.startswith(b"\x7fELF") or data.startswith(b"\xca\xfe\xba\xbe"):
            raise MimeTypeMismatchError("Executable binaries are strictly prohibited")

        if clean_ext == "pdf":
            if not data.startswith(b"%PDF-"):
                raise MimeTypeMismatchError("Claimed PDF file does not start with standard PDF header (%PDF-)")
            return "pdf"

        if clean_ext in ("docx", "doc"):
            if not data.startswith(b"PK\x03\x04"):
                raise MimeTypeMismatchError("Claimed DOCX file is not a valid OpenXML package (missing PK header)")
            # Validate zip contents for Word OpenXML signatures
            cls._validate_docx_zip(data)
            return "docx"

        if clean_ext in ("txt", "text", "md"):
            # Ensure text is valid UTF-8 and does not have excessive binary null bytes
            try:
                data.decode("utf-8")
            except UnicodeDecodeError as e:
                raise CorruptFileError(f"Plain text file is not valid UTF-8: {e}") from e
            if b"\x00" in data:
                raise MimeTypeMismatchError("Text file contains null bytes and appears to be binary")
            return "text"

        raise MimeTypeMismatchError(f"Unsupported file extension: .{clean_ext}")

    @classmethod
    def _validate_docx_zip(cls, data: bytes) -> None:
        """Inspect zip structure for decompression bomb or missing Word files."""
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                total_uncompressed = 0
                has_word_document = False

                for info in zf.infolist():
                    total_uncompressed += info.file_size
                    if total_uncompressed > cls.MAX_UNCOMPRESSED_BYTES:
                        raise DecompressionBombError(
                            f"Uncompressed archive size exceeds limit of {cls.MAX_UNCOMPRESSED_BYTES} bytes"
                        )
                    if info.filename in ("word/document.xml", "[Content_Types].xml"):
                        has_word_document = True

                ratio = total_uncompressed / max(len(data), 1)
                if ratio > cls.MAX_COMPRESSION_RATIO:
                    raise DecompressionBombError(
                        f"Archive compression ratio ({ratio:.1f}:1) exceeds safety threshold of {cls.MAX_COMPRESSION_RATIO}:1"
                    )

                if not has_word_document:
                    raise MimeTypeMismatchError("Archive is not a valid Word (.docx) document")
        except zipfile.BadZipFile as e:
            raise CorruptFileError(f"Malformed DOCX zip package: {e}") from e


class TextExtractor:
    """Extracts text and locator mappings from validated document payloads."""

    @classmethod
    def extract(cls, data: bytes, canonical_type: str) -> ExtractionResult:
        """Route to appropriate extractor based on validated canonical type."""
        if canonical_type == "pdf":
            return cls.extract_pdf(data)
        elif canonical_type == "docx":
            return cls.extract_docx(data)
        elif canonical_type == "text":
            return cls.extract_text(data)
        else:
            raise MimeTypeMismatchError(f"Unknown canonical type: {canonical_type}")

    @classmethod
    def extract_pdf(cls, data: bytes) -> ExtractionResult:
        """Extract text from PDF pages with page-level locators."""
        try:
            reader = pypdf.PdfReader(io.BytesIO(data))
        except Exception as e:
            raise CorruptFileError(f"Failed to parse PDF document: {e}") from e

        if reader.is_encrypted:
            raise EncryptedFileError("Encrypted PDF files cannot be processed")

        page_count = len(reader.pages)
        if page_count > DocumentScanner.MAX_PDF_PAGES:
            raise OversizedFileError(
                f"PDF has {page_count} pages, exceeding maximum limit of {DocumentScanner.MAX_PDF_PAGES} pages"
            )

        full_text_chunks: list[str] = []
        locators: list[TextLocator] = []
        total_chars = 0
        total_meaningful_chars = 0
        paragraph_idx = 0

        for page_idx, page in enumerate(reader.pages, start=1):
            try:
                page_text = page.extract_text() or ""
            except Exception:
                page_text = ""

            meaningful_chars = len(page_text.strip())
            total_meaningful_chars += meaningful_chars

            if page_text:
                # Split page text into readable paragraphs
                paras = [p.strip() for p in page_text.split("\n\n") if p.strip()]
                if not paras:
                    paras = [page_text.strip()]

                for para in paras:
                    p_start = total_chars
                    p_end = p_start + len(para)
                    preview = (para[:117] + "...") if len(para) > 120 else para
                    locators.append(
                        TextLocator(
                            locator_type="page",
                            page_number=page_idx,
                            paragraph_index=paragraph_idx,
                            char_offset_start=p_start,
                            char_offset_end=p_end,
                            preview=preview,
                        )
                    )
                    paragraph_idx += 1
                    full_text_chunks.append(para)
                    total_chars = p_end + 2  # newline separation

        joined_text = "\n\n".join(full_text_chunks)
        is_empty_or_scanned = total_meaningful_chars < 20

        return ExtractionResult(
            extracted_text=joined_text,
            locators=locators,
            page_count=page_count,
            paragraph_count=len(locators),
            is_empty_or_scanned=is_empty_or_scanned,
        )

    @classmethod
    def extract_docx(cls, data: bytes) -> ExtractionResult:
        """Extract text from DOCX paragraphs with paragraph-level locators."""
        try:
            doc = Document(io.BytesIO(data))
        except Exception as e:
            raise CorruptFileError(f"Failed to read DOCX document: {e}") from e

        paras = [p.text.strip() for p in doc.paragraphs if p.text and p.text.strip()]
        if len(paras) > DocumentScanner.MAX_DOCX_PARAGRAPHS:
            raise OversizedFileError(
                f"DOCX has {len(paras)} paragraphs, exceeding maximum limit of {DocumentScanner.MAX_DOCX_PARAGRAPHS}"
            )

        locators: list[TextLocator] = []
        full_text_chunks: list[str] = []
        total_chars = 0

        for idx, text in enumerate(paras):
            start = total_chars
            end = start + len(text)
            preview = (text[:117] + "...") if len(text) > 120 else text
            locators.append(
                TextLocator(
                    locator_type="paragraph",
                    page_number=None,
                    paragraph_index=idx,
                    char_offset_start=start,
                    char_offset_end=end,
                    preview=preview,
                )
            )
            full_text_chunks.append(text)
            total_chars = end + 2

        joined_text = "\n\n".join(full_text_chunks)
        is_empty = len(joined_text.strip()) == 0

        return ExtractionResult(
            extracted_text=joined_text,
            locators=locators,
            page_count=None,
            paragraph_count=len(locators),
            is_empty_or_scanned=is_empty,
        )

    @classmethod
    def extract_text(cls, data: bytes) -> ExtractionResult:
        """Extract text from plain text or pasted content with paragraph locators."""
        try:
            content = data.decode("utf-8")
        except UnicodeDecodeError as e:
            raise CorruptFileError(f"Content is not valid UTF-8 text: {e}") from e

        # Normalize line breaks
        normalized = content.replace("\r\n", "\n").replace("\r", "\n")
        raw_paras = [p.strip() for p in normalized.split("\n\n") if p.strip()]
        if not raw_paras and normalized.strip():
            raw_paras = [p.strip() for p in normalized.split("\n") if p.strip()]

        locators: list[TextLocator] = []
        full_text_chunks: list[str] = []
        total_chars = 0

        for idx, para in enumerate(raw_paras):
            start = total_chars
            end = start + len(para)
            preview = (para[:117] + "...") if len(para) > 120 else para
            locators.append(
                TextLocator(
                    locator_type="paragraph",
                    page_number=None,
                    paragraph_index=idx,
                    char_offset_start=start,
                    char_offset_end=end,
                    preview=preview,
                )
            )
            full_text_chunks.append(para)
            total_chars = end + 2

        joined = "\n\n".join(full_text_chunks)
        return ExtractionResult(
            extracted_text=joined,
            locators=locators,
            page_count=None,
            paragraph_count=len(locators),
            is_empty_or_scanned=len(joined.strip()) == 0,
        )


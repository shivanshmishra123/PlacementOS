"""Unit tests for document parsers, security scanners, and locator extraction."""

import io
import zipfile

import pypdf
import pytest
from docx import Document

from placementos.services.parsers import (
    CorruptFileError,
    DecompressionBombError,
    DocumentScanner,
    EncryptedFileError,
    MimeTypeMismatchError,
    OversizedFileError,
    TextExtractor,
)


def create_minimal_pdf(pages: list[str]) -> bytes:
    """Generate in-memory valid PDF with given text across pages."""
    writer = pypdf.PdfWriter()
    for _ in pages:
        writer.add_blank_page(width=612, height=792)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def create_minimal_docx(paragraphs: list[str]) -> bytes:
    """Generate in-memory valid DOCX package with given paragraphs."""
    doc = Document()
    for p in paragraphs:
        doc.add_paragraph(p)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


class TestDocumentScanner:
    """Tests for file pre-scanning and safety controls."""

    def test_oversized_file_rejected(self):
        huge_data = b"A" * (DocumentScanner.MAX_FILE_BYTES + 1024)
        with pytest.raises(OversizedFileError) as exc_info:
            DocumentScanner.scan_bytes(huge_data, "pdf")
        assert exc_info.value.code == "OVERSIZED_FILE"

    def test_empty_file_rejected(self):
        with pytest.raises(CorruptFileError) as exc_info:
            DocumentScanner.scan_bytes(b"", "pdf")
        assert exc_info.value.code == "CORRUPT_FILE"

    def test_executable_spoofing_rejected(self):
        # Fake MZ header disguised as PDF
        fake_pdf = b"MZ\x90\x00\x03\x00\x00\x00" + b"\x00" * 200
        with pytest.raises(MimeTypeMismatchError) as exc_info:
            DocumentScanner.scan_bytes(fake_pdf, "pdf")
        assert exc_info.value.code == "MIMETYPE_MISMATCH"

    def test_invalid_pdf_header_rejected(self):
        fake_pdf = b"NOT_A_PDF_STREAM"
        with pytest.raises(MimeTypeMismatchError):
            DocumentScanner.scan_bytes(fake_pdf, "pdf")

    def test_invalid_docx_header_rejected(self):
        fake_docx = b"NOT_A_ZIP_PACKAGE"
        with pytest.raises(MimeTypeMismatchError):
            DocumentScanner.scan_bytes(fake_docx, "docx")

    def test_docx_decompression_bomb_rejected(self):
        """Create zip with high compression ratio simulating zip bomb."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            # 35MB of zeroes compresses to very few KB
            zf.writestr("word/document.xml", b"\x00" * (35 * 1024 * 1024))
            zf.writestr("[Content_Types].xml", b"<Types/>")

        bomb_bytes = buf.getvalue()
        with pytest.raises(DecompressionBombError) as exc_info:
            DocumentScanner.scan_bytes(bomb_bytes, "docx")
        assert exc_info.value.code == "DECOMPRESSION_BOMB"

    def test_valid_docx_scanned_successfully(self):
        valid_docx = create_minimal_docx(["Hello world"])
        canonical = DocumentScanner.scan_bytes(valid_docx, "docx")
        assert canonical == "docx"

    def test_plain_text_with_null_byte_rejected(self):
        binary_text = b"Hello\x00World"
        with pytest.raises(MimeTypeMismatchError):
            DocumentScanner.scan_bytes(binary_text, "txt")


class TestTextExtractor:
    """Tests for text chunking and exact locator mapping."""

    def test_extract_plain_text_locators(self):
        raw_text = (
            "Job Title: Software Development Engineer\n\n"
            "Eligibility Criteria:\n"
            "Candidates must possess a minimum CGPA of 7.50 on a 10.0 scale.\n"
            "No active backlogs allowed at time of interview.\n\n"
            "Compensation:\n"
            "Annual CTC is 18,00,000 INR."
        )
        res = TextExtractor.extract_text(raw_text.encode("utf-8"))
        assert not res.is_empty_or_scanned
        assert res.paragraph_count >= 3
        assert len(res.locators) == res.paragraph_count

        # Verify first locator
        loc0 = res.locators[0]
        assert loc0.paragraph_index == 0
        assert loc0.char_offset_start == 0
        assert "Software Development Engineer" in loc0.preview

        # Verify second locator offset aligns with text
        loc1 = res.locators[1]
        assert loc1.paragraph_index == 1
        assert loc1.char_offset_start > loc0.char_offset_end
        assert "Eligibility Criteria" in loc1.preview

    def test_extract_docx_locators(self):
        paras = [
            "Placement Drive: Cloud Software Engineer 2026",
            "Department: Computer Science and Engineering",
            "Eligible Branches: CSE, IT, ECE with CGPA >= 8.0",
        ]
        docx_bytes = create_minimal_docx(paras)
        res = TextExtractor.extract_docx(docx_bytes)

        assert not res.is_empty_or_scanned
        assert res.paragraph_count == 3
        assert res.locators[0].preview == paras[0]
        assert res.locators[1].preview == paras[1]
        assert res.locators[2].preview == paras[2]

    def test_encrypted_pdf_rejected(self):
        writer = pypdf.PdfWriter()
        writer.add_blank_page(width=100, height=100)
        writer.encrypt("top_secret")
        buf = io.BytesIO()
        writer.write(buf)
        encrypted_bytes = buf.getvalue()

        with pytest.raises(EncryptedFileError) as exc_info:
            TextExtractor.extract_pdf(encrypted_bytes)
        assert exc_info.value.code == "ENCRYPTED_FILE"

    def test_empty_or_scanned_pdf_detected(self):
        # Blank PDF without text streams
        writer = pypdf.PdfWriter()
        writer.add_blank_page(width=100, height=100)
        buf = io.BytesIO()
        writer.write(buf)
        blank_pdf_bytes = buf.getvalue()

        res = TextExtractor.extract_pdf(blank_pdf_bytes)
        assert res.is_empty_or_scanned is True


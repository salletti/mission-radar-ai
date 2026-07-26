"""Unit tests for PdfMinerCVExtractorGateway.

These tests call the REAL pdfminer implementation — the gateway IS the I/O boundary.
No mocking of pdfminer; fixture PDF files are used for the extraction tests.
"""
import pathlib

import pytest

from src.Infrastructure.External.CV.exceptions import CVExtractionError
from src.Infrastructure.External.CV.pdfminer_cv_extractor_gateway import PdfMinerCVExtractorGateway

_FIXTURES = pathlib.Path(__file__).parents[3] / "Fixtures" / "CV"


def _make_gateway() -> PdfMinerCVExtractorGateway:
    return PdfMinerCVExtractorGateway()


# ---------------------------------------------------------------------------
# Nominal cases
# ---------------------------------------------------------------------------


async def test_extract_text_nominal() -> None:
    gateway = _make_gateway()

    result = await gateway.extract_text(str(_FIXTURES / "cv_simple.pdf"))

    assert "Jean Dupont" in result


async def test_extract_text_empty_pdf() -> None:
    gateway = _make_gateway()

    result = await gateway.extract_text(str(_FIXTURES / "cv_empty.pdf"))

    assert result == ""


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


async def test_extract_text_file_not_found() -> None:
    gateway = _make_gateway()

    with pytest.raises(CVExtractionError) as exc_info:
        await gateway.extract_text("/nonexistent/path/cv.pdf")

    assert exc_info.value.file_path == "/nonexistent/path/cv.pdf"
    assert exc_info.value.reason == "file not found"


async def test_extract_text_corrupted_pdf(tmp_path: pathlib.Path) -> None:
    corrupt = tmp_path / "corrupt.pdf"
    corrupt.write_bytes(b"this is not a pdf \x00\xff\xfe garbage content")
    gateway = _make_gateway()

    with pytest.raises(CVExtractionError) as exc_info:
        await gateway.extract_text(str(corrupt))

    assert exc_info.value.file_path == str(corrupt)


# ---------------------------------------------------------------------------
# _clean method — tested directly via @staticmethod access
# ---------------------------------------------------------------------------


def test_clean_collapses_multiple_spaces() -> None:
    result = PdfMinerCVExtractorGateway._clean("Jean   Dupont    Python")

    assert result == "Jean Dupont Python"


def test_clean_collapses_blank_lines() -> None:
    result = PdfMinerCVExtractorGateway._clean("Jean Dupont\n\n\n\nDeveloppeur Python")

    assert result == "Jean Dupont\n\nDeveloppeur Python"

"""
Generate minimal PDF fixture files for unit tests.

Run once inside the backend container:
    python tests/Fixtures/CV/create_fixtures.py

Generates:
    tests/Fixtures/CV/cv_simple.pdf  — one-page PDF with text content
    tests/Fixtures/CV/cv_empty.pdf   — one-page PDF with no text (empty page)

No external library required — PDFs are built from raw bytes.
"""
import pathlib

HERE = pathlib.Path(__file__).parent


def _build_simple_pdf(text: str) -> bytes:
    """Minimal valid PDF with a single text run (Type1/Helvetica, 5 objects)."""
    stream_content = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode("latin-1")
    stream_length = len(stream_content)

    header = b"%PDF-1.4\n"
    objs = [
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        (
            b"3 0 obj\n"
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
            b" /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\n"
            b"endobj\n"
        ),
        (
            f"4 0 obj\n<< /Length {stream_length} >>\nstream\n".encode()
            + stream_content
            + b"\nendstream\nendobj\n"
        ),
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
    ]

    return _assemble(header, objs)


def _build_empty_pdf() -> bytes:
    """Minimal valid PDF with a single blank page (no content stream)."""
    header = b"%PDF-1.4\n"
    objs = [
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n",
    ]

    return _assemble(header, objs)


def _assemble(header: bytes, objs: list[bytes]) -> bytes:
    """Build the PDF body, xref table, and trailer from pre-encoded objects."""
    body = header
    offsets: list[int] = []
    for obj in objs:
        offsets.append(len(body))
        body += obj

    xref_pos = len(body)
    n = len(objs) + 1  # +1 for the mandatory free entry (object 0)

    xref = f"xref\n0 {n}\n0000000000 65535 f \n".encode()
    for offset in offsets:
        # Each entry is exactly 20 bytes: 10-digit offset + space + 5-digit gen +
        # space + status + space + newline
        xref += f"{offset:010d} 00000 n \n".encode()

    trailer = (
        f"trailer\n<< /Size {n} /Root 1 0 R >>\n"
        f"startxref\n{xref_pos}\n%%EOF\n"
    ).encode()

    return body + xref + trailer


if __name__ == "__main__":
    (HERE / "cv_simple.pdf").write_bytes(
        _build_simple_pdf("Jean Dupont - Python Senior TJM 700 EUR/j")
    )
    (HERE / "cv_empty.pdf").write_bytes(_build_empty_pdf())
    print("Fixtures generated:")
    print(f"  {HERE / 'cv_simple.pdf'}")
    print(f"  {HERE / 'cv_empty.pdf'}")

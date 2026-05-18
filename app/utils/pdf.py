"""PDF text extraction. Thin wrapper around pypdf."""
from io import BytesIO

from pypdf import PdfReader

from ..core.errors import ValidationError


def extract_text(data: bytes) -> str:
    """Extract concatenated page text from a PDF byte stream."""
    try:
        reader = PdfReader(BytesIO(data))
    except Exception as e:
        raise ValidationError(f"could not parse PDF: {e}") from e

    if reader.is_encrypted:
        raise ValidationError("encrypted PDFs are not supported")

    pages: list[str] = []
    for page in reader.pages:
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        if text.strip():
            pages.append(text.strip())

    if not pages:
        raise ValidationError("no extractable text in PDF (is it scanned? OCR not enabled)")

    return "\n\n".join(pages)

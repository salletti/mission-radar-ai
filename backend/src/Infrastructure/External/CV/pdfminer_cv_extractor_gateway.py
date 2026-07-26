import re

from pdfminer.high_level import extract_text
from pdfminer.pdfparser import PDFSyntaxError

from src.Application.Gateway.cv_extractor_gateway import CVExtractorGateway
from src.Infrastructure.External.CV.exceptions import CVExtractionError


class PdfMinerCVExtractorGateway(CVExtractorGateway):
    """PDF extractor backed by pdfminer.six.

    Phase 2.0: pdfminer.extract_text is synchronous — called directly inside
    async method. Acceptable for small CVs. Phase 2.1+ should wrap with
    asyncio.get_event_loop().run_in_executor(None, ...) for production workloads.
    """

    async def extract_text(self, file_path: str) -> str:
        try:
            raw = extract_text(file_path)
        except FileNotFoundError as e:
            raise CVExtractionError(file_path=file_path, reason="file not found") from e
        except PDFSyntaxError as e:
            raise CVExtractionError(file_path=file_path, reason=f"invalid PDF: {e}") from e
        except Exception as e:
            raise CVExtractionError(file_path=file_path, reason=str(e)) from e

        return self._clean(raw)

    @staticmethod
    def _clean(text: str) -> str:
        text = re.sub(r"[ \t]+", " ", text)
        text = "\n".join(line.rstrip() for line in text.splitlines())
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

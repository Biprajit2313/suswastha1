from pathlib import Path

from app.core.logging import get_logger

logger = get_logger(__name__)


class OCRService:
    """
    Production-safe OCR service.

    - Uses pytesseract if available
    - Gracefully handles missing dependencies
    - Never crashes the backend
    """

    def extract_text(self, image_path: Path) -> str:
        """
        Main OCR entry point.
        Returns extracted text or empty string safely.
        """
        text = self._pytesseract(image_path)

        if text and text.strip():
            return text.strip()

        logger.warning(
            "ocr_no_text_extracted",
            extra={"path": str(image_path)}
        )
        return ""

    def _pytesseract(self, image_path: Path) -> str:
        """
        OCR using pytesseract.
        Requires system-level Tesseract installation.
        Safe fallback if unavailable.
        """
        try:
            from PIL import Image
            import pytesseract
        except ImportError:
            logger.warning("pytesseract_not_installed")
            return ""

        try:
            image = Image.open(image_path)
        except Exception:
            logger.exception(
                "image_open_failed",
                extra={"path": str(image_path)}
            )
            return ""

        try:
            return pytesseract.image_to_string(image)
        except Exception:
            logger.exception(
                "pytesseract_ocr_failed",
                extra={"path": str(image_path)}
            )
            return ""

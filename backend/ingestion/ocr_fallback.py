"""
OCR Fallback Layer for MAANAKNETRA.
Enforces strict anti-hallucination / anti-degradation rule:
Never replace readable digital text with OCR.
Triggers OCR only when extracted text character count is below MIN_TEXT_THRESHOLD.
"""

import logging
from typing import Tuple, List, Optional
from .models import TextBlock

logger = logging.getLogger(__name__)

# Threshold below which a page is considered near-empty or scanned image
DEFAULT_OCR_TEXT_THRESHOLD = 40


def should_trigger_ocr(text: str, threshold: int = DEFAULT_OCR_TEXT_THRESHOLD) -> bool:
    """
    Determines whether a page contains insufficient digital text to warrant OCR fallback.
    Returns True ONLY when clean text is below threshold.
    """
    clean = text.strip() if text else ""
    return len(clean) < threshold


class OCRFallbackEngine:
    """
    Lazy-loading wrapper for PaddleOCR fallback.
    Does not initialize OCR models into memory until a scanned/near-empty page is encountered.
    """

    def __init__(self):
        self._ocr = None
        self._initialized = False
        self._available = None

    def is_available(self) -> bool:
        if self._available is not None:
            return self._available
        try:
            import paddleocr  # noqa: F401
            self._available = True
        except ImportError:
            self._available = False
            logger.info("PaddleOCR not installed; OCR fallback will operate in degradation mode.")
        return self._available

    def _get_ocr(self):
        if not self._initialized:
            if not self.is_available():
                raise RuntimeError(
                    "PaddleOCR is not installed in the environment. "
                    "Install with: pip install paddlepaddle paddleocr"
                )
            from paddleocr import PaddleOCR
            # Initialize with English/Hindi language detection
            self._ocr = PaddleOCR(use_angle_cls=True, lang='en')
            self._initialized = True
        return self._ocr

    def extract_text_from_image(
        self,
        image_bytes: bytes,
        page_number: int
    ) -> Tuple[str, List[TextBlock]]:
        """
        Executes OCR on an image byte array.
        Returns extracted text and structured TextBlocks.
        """
        if not self.is_available():
            logger.warning(
                f"Page {page_number} triggered OCR fallback, but PaddleOCR is not installed. "
                "Returning empty OCR text."
            )
            return "", []

        try:
            ocr = self._get_ocr()
            import numpy as np
            import io
            from PIL import Image

            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            img_arr = np.array(image)

            result = ocr.ocr(img_arr, cls=True)
            extracted_lines: List[str] = []
            blocks: List[TextBlock] = []

            if result and result[0]:
                for idx, line in enumerate(result[0]):
                    text = line[1][0]
                    confidence = line[1][1]
                    if confidence >= 0.5:  # confidence filter
                        extracted_lines.append(text)
                        blocks.append(TextBlock(
                            block_id=f"ocr_p{page_number}_b{idx+1}",
                            text=text,
                            page_number=page_number
                        ))

            full_text = "\n".join(extracted_lines)
            return full_text, blocks

        except Exception as e:
            logger.error(f"Error executing OCR fallback on page {page_number}: {e}")
            return "", []

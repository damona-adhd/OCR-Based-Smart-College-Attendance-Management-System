"""
Tesseract OCR extractor with improved config for attendance registers.

Key improvements:
- Uses --psm 6 (assume uniform block of text) for better line grouping
- Tries multiple PSM modes if first yields nothing
- Adds logging for diagnostics
- Returns per-word data with proper block_num/line_num grouping
"""
from __future__ import annotations
from typing import List, Dict, Any
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# Tesseract page segmentation modes to try in order
# PSM 6 = assume uniform block of text (best for registers)
# PSM 4 = assume single column of text of variable sizes
# PSM 3 = fully automatic (default)
_PSM_MODES = [6, 4, 3]

# OEM 3 = default based on what is available (LSTM preferred)
_TESSERACT_CONFIG = "--oem 3 --psm {psm} -c preserve_interword_spaces=1"


def _require_pytesseract():
    try:
        import pytesseract
        from pytesseract import Output
        pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD
        return pytesseract, Output
    except ImportError as exc:
        raise RuntimeError(
            "pytesseract is required for OCR. "
            "Install it: pip install pytesseract  "
            "Also ensure Tesseract OCR is installed at: " + settings.TESSERACT_CMD
        ) from exc


def run_ocr(image) -> List[Dict[str, Any]]:
    """
    Run Tesseract on a preprocessed image.
    Tries PSM 6 → 4 → 3 until words are extracted.
    Returns word-level dicts with text, confidence, block_num, line_num, bbox.
    """
    pytesseract, Output = _require_pytesseract()

    for psm in _PSM_MODES:
        config = _TESSERACT_CONFIG.format(psm=psm)
        try:
            data = pytesseract.image_to_data(
                image, output_type=Output.DICT, lang="eng", config=config
            )
            words = []
            n = len(data["text"])
            for i in range(n):
                text = data["text"][i].strip()
                conf = int(data["conf"][i])
                if text and conf >= 0:
                    words.append({
                        "text": text,
                        "conf": conf,
                        "left": data["left"][i],
                        "top": data["top"][i],
                        "width": data["width"][i],
                        "height": data["height"][i],
                        "line_num": data["line_num"][i],
                        "block_num": data["block_num"][i],
                        "par_num": data["par_num"][i],
                        "word_num": data["word_num"][i],
                    })

            if words:
                logger.info("run_ocr: PSM %d extracted %d words", psm, len(words))
                return words
            else:
                logger.warning("run_ocr: PSM %d returned 0 words, trying next mode", psm)

        except RuntimeError:
            raise
        except Exception as e:
            logger.exception("run_ocr: PSM %d raised %s", psm, e)

    logger.error("run_ocr: all PSM modes failed to extract text")
    return []


def get_full_text(image) -> str:
    """Return full page text string from Tesseract."""
    try:
        pytesseract, _ = _require_pytesseract()
        config = _TESSERACT_CONFIG.format(psm=6)
        text = pytesseract.image_to_string(image, lang="eng", config=config)
        logger.info("get_full_text: extracted %d chars", len(text))
        return text
    except RuntimeError:
        raise
    except Exception as e:
        logger.exception("get_full_text failed: %s", e)
        return ""

"""
OpenCV-based image preprocessor for attendance register images.

Key improvements:
- Better DPI upscaling (min 300 DPI equivalent)
- Contrast enhancement (CLAHE) before thresholding
- Morphological cleanup to remove noise
- PDF → image conversion support via pdf2image / Pillow
- Logging for all steps
"""
from __future__ import annotations
from typing import Optional, List
import os
import logging

logger = logging.getLogger(__name__)


def _require_cv2():
    try:
        import cv2
        import numpy as np
        return cv2, np
    except ImportError as exc:
        raise RuntimeError(
            "OpenCV (cv2) is required. Install: pip install opencv-python-headless"
        ) from exc


def load_image(path: str):
    """Load an image from disk. Returns None if loading fails."""
    cv2, np = _require_cv2()
    img = cv2.imread(path)
    if img is None:
        logger.error("load_image: cv2.imread returned None for %s", path)
    else:
        logger.info("load_image: loaded %s shape=%s", path, img.shape)
    return img


def preprocess_image(img) -> any:
    """
    Full preprocessing pipeline for attendance register images:
    1. Grayscale
    2. Upscale to ≥1800px wide (minimum 300 DPI equivalent)
    3. CLAHE contrast enhancement
    4. Denoise
    5. Adaptive threshold
    6. Morphological cleanup
    7. Deskew
    """
    cv2, np = _require_cv2()

    if img is None:
        return None

    # Grayscale
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img.copy()

    h, w = gray.shape[:2]
    logger.info("preprocess_image: input size=%dx%d", w, h)

    # Upscale — aim for at least 1800px wide for good OCR quality
    TARGET_WIDTH = 1800
    if w < TARGET_WIDTH:
        scale = TARGET_WIDTH / w
        new_w = int(w * scale)
        new_h = int(h * scale)
        gray = cv2.resize(gray, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
        logger.info("preprocess_image: upscaled to %dx%d", new_w, new_h)

    # CLAHE contrast enhancement (helps with uneven lighting)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)

    # Denoise
    denoised = cv2.fastNlMeansDenoising(enhanced, h=10, templateWindowSize=7, searchWindowSize=21)

    # Adaptive threshold — use larger block size for printed registers
    binary = cv2.adaptiveThreshold(
        denoised, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=21,
        C=10,
    )

    # Morphological cleanup — remove speckles
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

    # Deskew
    result = _deskew(cleaned, cv2, np)
    logger.info("preprocess_image: output size=%dx%d", result.shape[1], result.shape[0])
    return result


def _deskew(image, cv2, np):
    """Correct skew up to 15 degrees using minAreaRect."""
    try:
        coords = np.column_stack(np.where(image < 128))
        if len(coords) < 100:
            return image
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        if abs(angle) > 15:
            logger.warning("_deskew: angle %.1f° exceeds 15°, skipping deskew", angle)
            return image
        if abs(angle) < 0.5:
            return image  # negligible skew
        h, w = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(
            image, M, (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE,
        )
        logger.info("_deskew: corrected %.2f°", angle)
        return rotated
    except Exception as e:
        logger.warning("_deskew: failed with %s", e)
        return image


def preprocess_file(path: str) -> Optional[any]:
    """Load and preprocess an image file. Returns None on failure."""
    img = load_image(path)
    if img is None:
        return None
    return preprocess_image(img)


def pdf_to_images(path: str) -> List:
    """
    Convert a PDF to a list of preprocessed numpy arrays (one per page).
    Requires: pip install pdf2image pillow
    Also requires: poppler installed on system.
    Falls back to Pillow for single-page PDFs if pdf2image unavailable.
    """
    cv2, np = _require_cv2()

    # Try pdf2image (best quality, requires poppler)
    try:
        from pdf2image import convert_from_path
        logger.info("pdf_to_images: converting %s with pdf2image", path)
        pil_images = convert_from_path(path, dpi=300)
        logger.info("pdf_to_images: got %d page(s)", len(pil_images))
        results = []
        for i, pil_img in enumerate(pil_images):
            img_array = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            processed = preprocess_image(img_array)
            if processed is not None:
                results.append(processed)
        return results
    except ImportError:
        logger.warning("pdf_to_images: pdf2image not installed, trying Pillow")
    except Exception as e:
        logger.error("pdf_to_images: pdf2image failed: %s", e)

    # Fallback: Pillow (works for text-based PDFs)
    try:
        from PIL import Image
        logger.info("pdf_to_images: trying Pillow for %s", path)
        pil_img = Image.open(path)
        img_array = cv2.cvtColor(np.array(pil_img.convert("RGB")), cv2.COLOR_RGB2BGR)
        processed = preprocess_image(img_array)
        return [processed] if processed is not None else []
    except Exception as e:
        logger.error("pdf_to_images: Pillow fallback failed: %s", e)

    return []

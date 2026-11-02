"""
OpenCV table border, grid, and cell detection service.
Identifies grid lines, table bounding boxes, and row regions in scanned attendance sheets.
"""
import logging
from typing import Optional, List, Dict, Tuple, Any
import numpy as np

logger = logging.getLogger(__name__)


def _require_cv2():
    try:
        import cv2
        return cv2
    except ImportError as e:
        raise RuntimeError("OpenCV (cv2) is required for grid detection.") from e


class OpenCVGridDetector:
    """Detects table boundaries, grid lines, and cell coordinates in images."""

    @staticmethod
    def preprocess_for_ocr(image: np.ndarray) -> np.ndarray:
        """Standard high-contrast enhancement and deskewing for OCR."""
        cv2 = _require_cv2()
        if image is None:
            return None

        # Grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # CLAHE contrast enhancement
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        # Deskew if needed
        deskewed = OpenCVGridDetector._deskew(enhanced)
        return deskewed

    @staticmethod
    def _deskew(image: np.ndarray) -> np.ndarray:
        cv2 = _require_cv2()
        try:
            # Threshold to get text / lines
            thresh = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
            coords = np.column_stack(np.where(thresh > 0))
            if len(coords) < 100:
                return image

            angle = cv2.minAreaRect(coords)[-1]
            if angle < -45:
                angle = -(90 + angle)
            else:
                angle = -angle

            if abs(angle) > 15 or abs(angle) < 0.5:
                return image

            h, w = image.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            rotated = cv2.warpAffine(
                image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
            )
            return rotated
        except Exception as e:
            logger.debug("Deskew skipped: %s", e)
            return image

    @staticmethod
    def detect_table_grid(image: np.ndarray) -> Dict[str, Any]:
        """
        Detect horizontal and vertical table lines.
        Returns:
            {
                "has_grid": bool,
                "cell_count": int,
                "row_boxes": List[Tuple[int, int, int, int]],  # (x, y, w, h) per row
                "table_mask": np.ndarray (or None),
            }
        """
        cv2 = _require_cv2()
        if image is None:
            return {"has_grid": False, "cell_count": 0, "row_boxes": []}

        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        h, w = gray.shape[:2]

        # Invert and adaptive threshold
        thresh = cv2.adaptiveThreshold(
            ~gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, -2
        )

        # Horizontal kernel: length proportional to image width
        h_len = max(20, w // 40)
        h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (h_len, 1))
        h_lines = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, h_kernel)

        # Vertical kernel: length proportional to image height
        v_len = max(20, h // 40)
        v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, v_len))
        v_lines = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, v_kernel)

        # Table grid mask
        table_grid = cv2.bitwise_or(h_lines, v_lines)

        # Find contours of grid cells
        contours, _ = cv2.findContours(table_grid, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        cells = []
        for c in contours:
            x_box, y_box, w_box, h_box = cv2.boundingRect(c)
            # Filter noise and whole image
            if (
                w_box > 25
                and h_box > 12
                and w_box < w * 0.95
                and h_box < h * 0.95
                and (w_box * h_box) > 400
            ):
                cells.append((x_box, y_box, w_box, h_box))

        if len(cells) < 10:
            # Not enough regular cells detected
            return {"has_grid": False, "cell_count": len(cells), "row_boxes": []}

        # Cluster cells by y-coordinate to identify table rows
        cells.sort(key=lambda b: (b[1], b[0]))
        rows: List[List[Tuple[int, int, int, int]]] = []
        row_tolerance = 18

        current_row = [cells[0]]
        current_y = cells[0][1]

        for box in cells[1:]:
            if abs(box[1] - current_y) <= row_tolerance:
                current_row.append(box)
            else:
                rows.append(current_row)
                current_row = [box]
                current_y = box[1]
        if current_row:
            rows.append(current_row)

        # Merge cell bounding boxes in each row to get a full row bounding box
        row_boxes = []
        for row in rows:
            if len(row) >= 2:  # at least 2 cells in row
                min_x = min(b[0] for b in row)
                min_y = min(b[1] for b in row)
                max_x = max(b[0] + b[2] for b in row)
                max_y = max(b[1] + b[3] for b in row)
                row_boxes.append((min_x, min_y, max_x - min_x, max_y - min_y))

        row_boxes.sort(key=lambda b: b[1])

        return {
            "has_grid": True,
            "cell_count": len(cells),
            "row_boxes": row_boxes,
            "row_count": len(row_boxes),
        }

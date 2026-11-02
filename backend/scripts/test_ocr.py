"""Diagnostic script — tests the full OCR pipeline."""
import sys, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from app.core.config import settings

print("=" * 60)
print("OCR DIAGNOSTIC")
print("=" * 60)
print(f"TESSERACT_CMD: {settings.TESSERACT_CMD}")
print(f"Tesseract exists: {os.path.exists(settings.TESSERACT_CMD)}")

# 1. Test cv2
try:
    import cv2, numpy as np
    print(f"\n[OK] OpenCV {cv2.__version__}")
except Exception as e:
    print(f"\n[FAIL] OpenCV: {e}")
    sys.exit(1)

# 2. Test pytesseract
try:
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD
    v = pytesseract.get_tesseract_version()
    print(f"[OK] Tesseract {v}")
except Exception as e:
    print(f"[FAIL] Tesseract: {e}")
    sys.exit(1)

# 3. Create a synthetic attendance register image and OCR it
print("\n--- Synthetic image test ---")
img = np.ones((350, 800), dtype=np.uint8) * 255
lines = [
    "1  1CS21CS001  Aditya Kumar",
    "2  1CS21CS002  Bhavana Singh",
    "3  1CS21CS003  Chetan Reddy",
]
for i, line in enumerate(lines):
    cv2.putText(img, line, (10, 80 + i * 80), cv2.FONT_HERSHEY_SIMPLEX, 0.9, 0, 2)

text = pytesseract.image_to_string(img)
print("Full text output:")
print(repr(text))

data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
words = [(data['text'][i], data['conf'][i]) for i in range(len(data['text'])) if data['text'][i].strip()]
print(f"\nWords extracted: {len(words)}")
for w, c in words[:15]:
    print(f"  {w!r:25} conf={c}")

# 4. Test the preprocessor on the synthetic image
print("\n--- Preprocessor test ---")
cv2.imwrite("test_register.png", img)
from app.services.ocr.preprocessor import preprocess_file
processed = preprocess_file("test_register.png")
if processed is not None:
    print(f"[OK] Preprocessor returned image shape: {processed.shape}")
else:
    print("[FAIL] Preprocessor returned None")

# 5. Test the extractor on the processed image
print("\n--- Extractor test ---")
from app.services.ocr.extractor import run_ocr
words2 = run_ocr(processed)
print(f"[OK] Extractor returned {len(words2)} words")
for w in words2[:10]:
    print(f"  {w['text']!r:25} conf={w['conf']}")

# 6. Test matcher
print("\n--- Matcher test ---")
from app.services.ocr.matcher import extract_usns_from_words, match_students
candidates = extract_usns_from_words(words2)
print(f"USN candidates found: {len(candidates)}")
for c in candidates:
    print(f"  {c['usn_candidate']!r:25} line={c['line']} text={c['line_text']!r:.50}")

roster = [
    {"id": 1, "usn": "1CS21CS001", "full_name": "Aditya Kumar"},
    {"id": 2, "usn": "1CS21CS002", "full_name": "Bhavana Singh"},
    {"id": 3, "usn": "1CS21CS003", "full_name": "Chetan Reddy"},
]
matched = match_students(candidates, roster)
print(f"\nMatched: {len(matched)} rows")
for m in matched:
    print(f"  USN={m.get('extracted_usn')} status={m['match_status']} student={m.get('matched_student_name')}")

# Clean up
import os
for f in ["test_register.png"]:
    if os.path.exists(f): os.remove(f)

print("\n" + "=" * 60)
print("DIAGNOSTIC COMPLETE")

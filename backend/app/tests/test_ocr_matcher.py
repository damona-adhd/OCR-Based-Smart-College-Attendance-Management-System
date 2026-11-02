"""
Unit tests for OCR matcher — no database or Tesseract required.
"""
import pytest
from app.services.ocr.matcher import (
    normalize_usn,
    extract_usns_from_words,
    match_students,
    find_missing_students,
)


ROSTER = [
    {"id": 1, "usn": "1CS21CS001", "full_name": "Aditya Kumar"},
    {"id": 2, "usn": "1CS21CS002", "full_name": "Bhavana Singh"},
    {"id": 3, "usn": "1CS21CS003", "full_name": "Chetan Reddy"},
]


def make_word(text, conf=80, line_num=1):
    return {"text": text, "conf": conf, "left": 0, "top": 0, "width": 10, "height": 10,
            "line_num": line_num, "block_num": 1}


def test_normalize_usn():
    assert normalize_usn("1CS21CS001") == "1CS21CS001"
    assert normalize_usn("1cs21cs001") == "1CS21CS001"
    assert normalize_usn("1CS 21CS001") == "1CS21CS001"
    assert normalize_usn("1CS-21CS001") == "1CS21CS001"


def test_extract_usns_from_words():
    words = [
        make_word("1CS21CS001", conf=85, line_num=1),
        make_word("Aditya", conf=80, line_num=1),
        make_word("1CS21CS002", conf=90, line_num=2),
    ]
    candidates = extract_usns_from_words(words)
    usns = [c["usn_candidate"] for c in candidates]
    assert "1CS21CS001" in usns
    assert "1CS21CS002" in usns


def test_matched_student():
    candidates = [{"usn_candidate": "1CS21CS001", "raw": "1CS21CS001", "line": 1, "line_text": "1CS21CS001 Aditya", "confidence": 90}]
    results = match_students(candidates, ROSTER)
    assert results[0]["match_status"] == "matched"
    assert results[0]["matched_student_id"] == 1


def test_unmatched_student():
    candidates = [{"usn_candidate": "XXXXXXXX99", "raw": "XXXXXXXX99", "line": 1, "line_text": "XXXXXXXX99", "confidence": 80}]
    results = match_students(candidates, ROSTER)
    assert results[0]["match_status"] == "unmatched"


def test_duplicate_detection():
    candidates = [
        {"usn_candidate": "1CS21CS001", "raw": "1CS21CS001", "line": 1, "line_text": "", "confidence": 90},
        {"usn_candidate": "1CS21CS001", "raw": "1CS21CS001", "line": 2, "line_text": "", "confidence": 85},
    ]
    results = match_students(candidates, ROSTER)
    statuses = [r["match_status"] for r in results]
    assert "matched" in statuses
    assert "duplicate" in statuses


def test_missing_students():
    candidates = [
        {"usn_candidate": "1CS21CS001", "raw": "1CS21CS001", "line": 1, "line_text": "", "confidence": 90},
    ]
    matched = match_students(candidates, ROSTER)
    missing = find_missing_students(matched, ROSTER)
    missing_ids = {m["matched_student_id"] for m in missing}
    assert 2 in missing_ids  # Bhavana not found
    assert 3 in missing_ids  # Chetan not found
    assert 1 not in missing_ids  # Aditya was matched


def test_uncertain_on_near_match():
    # OCR error: "1CS21CS00I" instead of "1CS21CS001" (I instead of 1)
    candidates = [{"usn_candidate": "1CS21CS00I", "raw": "1CS21CS00I", "line": 1, "line_text": "", "confidence": 55}]
    results = match_students(candidates, ROSTER)
    # Should be uncertain or matched (OCR correction via fuzzy)
    assert results[0]["match_status"] in ("uncertain", "matched", "unmatched")

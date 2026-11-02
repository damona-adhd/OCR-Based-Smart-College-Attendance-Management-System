"""
Student matching: normalize extracted USNs and match against DB roster.

Key fixes:
- USN pattern now requires at least one digit AND one letter (avoids matching plain names)
- Lines are grouped by block_num+line_num combination (not just line_num)
- Name words filtered before USN candidate extraction
"""
import re
import logging
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# Stricter USN pattern:
#  - 6–20 chars, alphanumeric
#  - Must contain at least one digit AND at least one letter
#  - Must start with a digit or uppercase letter
#  - Excludes pure-word tokens like "ADITYA", "KUMAR" (all letters, no digits)
USN_PATTERN = re.compile(r"\b[A-Z0-9]{4,20}\b", re.IGNORECASE)

# Known Indian USN prefixes — extend as needed
USN_PREFIX_PATTERN = re.compile(
    r"\b\d{1,2}[A-Z]{2,4}\d{2}[A-Z]{2}\d{3}\b"   # e.g. 1CS21CS001
    r"|\b[A-Z]{3}\d{2}[A-Z]{2}\d{3}\b"              # e.g. VTU21CS001
    r"|\b\d{3}[A-Z]{2}\d{4}\b",                     # roll numbers like 001CS2024
    re.IGNORECASE,
)


def normalize_usn(raw: str) -> str:
    """Normalize a USN: uppercase, strip non-alphanumeric."""
    return re.sub(r"[^A-Z0-9]", "", raw.upper())


def _has_digit(s: str) -> bool:
    return any(c.isdigit() for c in s)


def _has_letter(s: str) -> bool:
    return any(c.isalpha() for c in s)


def _looks_like_usn(token: str) -> bool:
    """Return True if token looks like a USN (has both letters and digits)."""
    t = normalize_usn(token)
    if len(t) < 4:
        return False
    # Must have at least one digit
    if not _has_digit(t):
        return False
    # Must have at least one letter
    if not _has_letter(t):
        return False
    return True


def extract_usns_from_words(words: List[Dict]) -> List[Dict]:
    """
    Group words by (block_num, line_num) and extract USN candidates.
    Filters out pure-word tokens (names like ADITYA, KUMAR).
    """
    # Group by block+line
    lines: Dict[tuple, List[Dict]] = {}
    for w in words:
        key = (w.get("block_num", 0), w.get("line_num", 0))
        lines.setdefault(key, []).append(w)

    candidates = []
    seen: set = set()

    for (block_num, line_num), line_words in sorted(lines.items()):
        # Sort words left-to-right
        line_words_sorted = sorted(line_words, key=lambda x: x.get("left", 0))
        line_text = " ".join(w["text"] for w in line_words_sorted)

        confs = [w["conf"] for w in line_words_sorted if w.get("conf", -1) > 0]
        avg_conf = sum(confs) / len(confs) if confs else 0.0

        # Try strict USN prefix pattern first
        strict_matches = USN_PREFIX_PATTERN.findall(line_text)
        if strict_matches:
            for m in strict_matches:
                norm = normalize_usn(m)
                if norm not in seen:
                    seen.add(norm)
                    candidates.append({
                        "usn_candidate": norm,
                        "raw": m,
                        "line": line_num,
                        "block": block_num,
                        "line_text": line_text.strip(),
                        "confidence": avg_conf,
                    })
            continue  # strict match found — don't also do loose match on this line

        # Fallback: general alphanumeric pattern, filter to USN-like tokens
        for m in USN_PATTERN.findall(line_text):
            if _looks_like_usn(m):
                norm = normalize_usn(m)
                if norm not in seen:
                    seen.add(norm)
                    candidates.append({
                        "usn_candidate": norm,
                        "raw": m,
                        "line": line_num,
                        "block": block_num,
                        "line_text": line_text.strip(),
                        "confidence": avg_conf,
                    })

    logger.info("extract_usns_from_words: found %d candidates from %d lines", len(candidates), len(lines))
    return candidates


def match_students(
    candidates: List[Dict],
    roster: List[Dict],
) -> List[Dict]:
    """Match extracted USN candidates against the class roster."""
    roster_map = {normalize_usn(s["usn"]): s for s in roster}
    seen_usns: Dict[str, int] = {}
    results = []

    for idx, cand in enumerate(candidates):
        norm = normalize_usn(cand["usn_candidate"])
        student = roster_map.get(norm)
        conf = cand["confidence"]

        if norm in seen_usns:
            results.append({
                "row_index": idx,
                "extracted_usn": cand["usn_candidate"],
                "extracted_name": None,
                "confidence": conf,
                "match_status": "duplicate",
                "matched_student_id": student["id"] if student else None,
                "matched_student_name": student["full_name"] if student else None,
                "matched_student_usn": student["usn"] if student else None,
                "proposed_status": None,
                "needs_review": True,
            })
        elif student:
            seen_usns[norm] = idx
            needs_review = conf < 60
            results.append({
                "row_index": idx,
                "extracted_usn": cand["usn_candidate"],
                "extracted_name": None,
                "confidence": conf,
                "match_status": "matched",
                "matched_student_id": student["id"],
                "matched_student_name": student["full_name"],
                "matched_student_usn": student["usn"],
                "proposed_status": None,
                "needs_review": needs_review,
            })
        else:
            best_match, best_sim = _best_fuzzy_match(norm, roster_map)
            if best_sim >= 0.75:
                results.append({
                    "row_index": idx,
                    "extracted_usn": cand["usn_candidate"],
                    "extracted_name": None,
                    "confidence": conf * best_sim,
                    "match_status": "uncertain",
                    "matched_student_id": best_match["id"],
                    "matched_student_name": best_match["full_name"],
                    "matched_student_usn": best_match["usn"],
                    "proposed_status": None,
                    "needs_review": True,
                })
            else:
                results.append({
                    "row_index": idx,
                    "extracted_usn": cand["usn_candidate"],
                    "extracted_name": None,
                    "confidence": conf,
                    "match_status": "unmatched",
                    "matched_student_id": None,
                    "matched_student_name": None,
                    "matched_student_usn": None,
                    "proposed_status": None,
                    "needs_review": True,
                })

    logger.info("match_students: %d candidates → %d results", len(candidates), len(results))
    return results


def find_missing_students(matched_results: List[Dict], roster: List[Dict]) -> List[Dict]:
    matched_ids = {r["matched_student_id"] for r in matched_results if r["matched_student_id"]}
    missing = []
    for student in roster:
        if student["id"] not in matched_ids:
            missing.append({
                "row_index": -1,
                "extracted_usn": None,
                "extracted_name": None,
                "confidence": 0.0,
                "match_status": "missing",
                "matched_student_id": student["id"],
                "matched_student_name": student["full_name"],
                "matched_student_usn": student["usn"],
                "proposed_status": None,
                "needs_review": True,
            })
    return missing


def _best_fuzzy_match(usn: str, roster_map: Dict[str, Dict]) -> Tuple[Optional[Dict], float]:
    best = None
    best_sim = 0.0
    for roster_usn, student in roster_map.items():
        sim = _similarity(usn, roster_usn)
        if sim > best_sim:
            best_sim = sim
            best = student
    return best, best_sim


def _similarity(a: str, b: str) -> float:
    """Jaccard similarity on character bigrams."""
    def bigrams(s):
        return set(s[i:i+2] for i in range(len(s) - 1))
    ba, bb = bigrams(a), bigrams(b)
    if not ba or not bb:
        return 0.0
    return len(ba & bb) / len(ba | bb)

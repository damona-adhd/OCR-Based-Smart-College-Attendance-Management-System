"""Extract structured identifiers from PDF text or optional vision models."""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings
from app.services.ocr.matcher import USN_PREFIX_PATTERN, normalize_usn, _looks_like_usn

logger = logging.getLogger(__name__)

MARK_PRESENT = re.compile(r"\b(P|PR|PRESENT|YES|1)\b", re.IGNORECASE)
MARK_ABSENT = re.compile(r"\b(A|AB|ABSENT|NO|0)\b", re.IGNORECASE)
NAME_TOKEN = re.compile(r"^[A-Za-z][A-Za-z .'-]{1,60}$")


def extract_rows_from_text(text: str) -> List[Dict[str, Any]]:
    """Parse digital PDF / register text into USN-oriented rows. Empty cells are not Absent."""
    rows: List[Dict[str, Any]] = []
    seen = set()
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        usn = None
        prefix_match = USN_PREFIX_PATTERN.search(line.replace(" ", ""))
        if prefix_match:
            usn = normalize_usn(prefix_match.group(0))
        else:
            for token in re.split(r"[\s,;|/]+", line):
                if _looks_like_usn(token):
                    usn = normalize_usn(token)
                    break
        if not usn or usn in seen:
            continue
        seen.add(usn)
        mark = None
        if MARK_PRESENT.search(line) and not MARK_ABSENT.search(line):
            mark = "present"
        elif MARK_ABSENT.search(line) and not MARK_PRESENT.search(line):
            mark = "absent"
        name = None
        leftover = USN_PREFIX_PATTERN.sub("", line)
        leftover = re.sub(r"\b(P|A|PR|AB|PRESENT|ABSENT)\b", "", leftover, flags=re.I)
        leftover = re.sub(r"\s+", " ", leftover).strip(" -|,")
        if leftover and NAME_TOKEN.match(leftover) and not _looks_like_usn(leftover):
            name = leftover.title()
        rows.append(
            {
                "usn": usn,
                "name": name,
                "mark": mark,
                "confidence": 90.0,
                "uncertain": mark is None,
                "raw_line": line,
            }
        )
    return rows


def extract_roster_from_text(text: str) -> List[Dict[str, Any]]:
    """Extract student USN + name pairs from a college roster PDF."""
    rows: List[Dict[str, Any]] = []
    seen = set()
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        usn = None
        m = USN_PREFIX_PATTERN.search(line.replace(" ", ""))
        if m:
            usn = normalize_usn(m.group(0))
        else:
            for token in re.split(r"[\s,;|/]+", line):
                if _looks_like_usn(token):
                    usn = normalize_usn(token)
                    break
        if not usn or usn in seen:
            continue
        seen.add(usn)
        name = None
        leftover = USN_PREFIX_PATTERN.sub(" ", line)
        leftover = re.sub(re.escape(usn), " ", leftover, flags=re.I)
        leftover = re.sub(r"\d+", " ", leftover)
        leftover = re.sub(r"\s+", " ", leftover).strip(" -|,.")
        if leftover and len(leftover) >= 3:
            name = leftover.title()
        rows.append({"usn": usn, "full_name": name or "", "raw_line": line})
    return rows


async def extract_with_gemini(file_bytes: bytes, mime_type: str) -> List[Dict[str, Any]]:
    """Optional vision extraction. Never invents students if the model is unavailable."""
    if not settings.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not configured")
    import base64

    prompt = (
        "Extract attendance register rows as JSON array only. "
        "Each object: usn (string), name (string or null), mark (present, absent, or null), "
        "confidence (0-100), uncertain (boolean). "
        "Do not invent students. If a mark is missing or unclear, set mark to null and uncertain true. "
        "Do not treat empty cells as absent."
    )
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.GEMINI_MODEL}:generateContent"
    )
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": mime_type if mime_type in ("image/jpeg", "image/png", "application/pdf") else "image/jpeg",
                            "data": base64.b64encode(file_bytes).decode("ascii"),
                        }
                    },
                ]
            }
        ],
        "generationConfig": {"temperature": 0.1},
    }
    async with httpx.AsyncClient(timeout=45.0) as client:
        resp = await client.post(url, params={"key": settings.GEMINI_API_KEY}, json=payload)
    if resp.status_code == 429:
        raise RuntimeError("The extraction model quota was exceeded. Try again later or mark attendance manually.")
    if resp.status_code >= 400:
        raise RuntimeError(f"The extraction model returned an error ({resp.status_code}).")
    data = resp.json()
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("The extraction model returned an unexpected response.") from exc
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
    parsed = json.loads(text)
    if not isinstance(parsed, list):
        raise RuntimeError("The extraction model did not return a JSON array.")
    cleaned = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        usn = normalize_usn(str(item.get("usn") or ""))
        if not usn:
            continue
        mark = item.get("mark")
        if mark not in ("present", "absent", None):
            mark = None
        cleaned.append(
            {
                "usn": usn,
                "name": item.get("name") or None,
                "mark": mark,
                "confidence": float(item.get("confidence") or 50),
                "uncertain": bool(item.get("uncertain") or mark is None),
            }
        )
    return cleaned

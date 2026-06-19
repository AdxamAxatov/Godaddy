"""Email -> company lookup against assets/All Companies.csv.

A company's registered domain is (roughly) its legal name with spaces and
punctuation stripped, optionally without the LLC/INC suffix. This module
builds an in-memory index mapping every such candidate key to the company's
name + parsed address, so lookup(email) returns the matching record(s).
"""
import csv
import re
from pathlib import Path

_CSV_PATH = Path(__file__).parent.parent / "assets" / "All Companies.csv"
_SUFFIXES = {"llc", "inc", "corp", "corporation", "incorporated",
             "ltd", "co", "company", "lp", "llp"}

_index = None  # lazy dict[str, list[dict]]


def _normalize(s: str) -> str:
    """Lowercase and keep only a-z0-9 (drops spaces, &, ', -, ., etc.)."""
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _candidate_keys(name: str) -> set:
    """All normalized keys a registered domain might match this legal name by."""
    low = name.lower()
    keys = set()
    if _normalize(low):
        keys.add(_normalize(low))
    if "&" in low:
        keys.add(_normalize(low.replace("&", "and")))
    toks = low.split()
    while toks and _normalize(toks[-1]) in _SUFFIXES:
        toks.pop()
    nos = " ".join(toks)
    if _normalize(nos):
        keys.add(_normalize(nos))
        if "&" in nos:
            keys.add(_normalize(nos.replace("&", "and")))
    return keys


def _clean(line: str) -> str:
    """Collapse whitespace (incl. \\xa0) and strip."""
    return re.sub(r"\s+", " ", line).strip()


def _parse_address(physical: str) -> tuple:
    """Physical Address field -> (street, city_state) from its non-empty lines."""
    lines = [_clean(ln) for ln in (physical or "").splitlines() if _clean(ln)]
    if len(lines) >= 2:
        return lines[0], lines[-1]
    if len(lines) == 1:
        return "", lines[0]
    return "", ""


def _build_index() -> dict:
    index = {}
    try:
        with open(_CSV_PATH, encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                name = _clean(row.get("Legal Name") or "")
                if not name:
                    continue
                street, city_state = _parse_address(row.get("Physical Address"))
                rec = {"legal_name": name, "address": street, "city_state": city_state}
                for key in _candidate_keys(name):
                    bucket = index.setdefault(key, [])
                    # Collapse harmless duplicates (identical name + address).
                    if not any(b["legal_name"] == name and b["address"] == street
                               and b["city_state"] == city_state for b in bucket):
                        bucket.append(rec)
    except OSError:
        return {}  # missing/unreadable CSV -> callers see no-match
    return index


def _get_index() -> dict:
    global _index
    if _index is None:
        _index = _build_index()
    return _index


def _domain_label(email_or_domain: str) -> str:
    s = (email_or_domain or "").strip().lower()
    if "@" in s:
        s = s.split("@", 1)[1]
    s = s.split(".")[0]  # registrable label, before the first dot
    return _normalize(s)


def lookup(email_or_domain: str) -> list:
    """Return matching company records (see module docstring). Copy of the
    stored list so callers can mutate freely."""
    label = _domain_label(email_or_domain)
    if not label:
        return []
    return list(_get_index().get(label, []))

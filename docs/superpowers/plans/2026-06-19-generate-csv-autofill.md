# /generate CSV Auto-Fill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let `/generate` accept just a company email (`info@company.com`); the bot looks the company up in `assets/All Companies.csv`, auto-fills the company name and address, and continues the existing generate flow.

**Architecture:** A new isolated module `src/company_lookup.py` owns all CSV parsing and email→company matching, exposing one function `lookup(email) -> list[dict]`. `main.py`'s `_handle_generate_input` detects a bare email, calls `lookup`, and fills `pending_generate[chat_id]` with the company name + address — the same fields the existing manual `Label:` path produces — then hands off to the unchanged route-type → `_finish_generate` pipeline. One match auto-fills; multiple matches (same name, different cities) show an inline picker; zero matches fall back to the existing manual entry.

**Tech Stack:** Python 3.12 stdlib only — `csv`, `re`. No new dependencies. No test framework: standalone scripts run with `.venv/bin/python`, exiting non-zero on failure.

## Global Constraints

- **No new dependencies.** stdlib `csv` / `re` only. `requirements.txt` unchanged.
- **Run Python via `.venv/bin/python`** on this macOS box (the CLAUDE.md `source .venv/Scripts/activate` line is the Windows path). Tests and smoke checks use `.venv/bin/python`.
- **Tests are standalone scripts.** Run with `.venv/bin/python tests/<name>.py`; print which assertion failed and `sys.exit(1)` on failure; print `PASS` and exit 0 on success.
- **Do not modify** `assets/All Companies.csv`, the website generator, or the job-description generator.
- **CSV facts (verified):** columns are `Legal Name, U SDOT Number, MC/MX/FF Numbers, Physical Address`. `Physical Address` is a quoted multi-line field whose non-empty lines are `[street, "CITY, ST ZIP"]`. ~87% of names end in `LLC`/`INC`; names may contain `&`, `'`, `-`. City/state strings may contain doubled spaces and `\xa0`.
- **Commit on `master`** (small project, no feature branch).

---

### Task 1: `company_lookup.py` — email→company matcher

**Files:**
- Create: `src/company_lookup.py`
- Test: `tests/test_company_lookup.py`

**Interfaces:**
- Consumes: nothing (leaf module). Reads `assets/All Companies.csv` relative to its own location.
- Produces:
  - `lookup(email_or_domain: str) -> list[dict]` — returns a list of records `{"legal_name": str, "address": str, "city_state": str}`. Length 0 = no match, 1 = unique, >1 = ambiguous (same normalized name, different addresses). Records carry whitespace-normalized fields.
  - Internal (not relied on by other tasks): `_normalize`, `_candidate_keys`, `_parse_address`, `_build_index`, `_get_index`, `_domain_label`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_company_lookup.py`:

```python
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import company_lookup as cl

failures = []


def check(cond, msg):
    if not cond:
        failures.append(msg)


# 1. Unique match, suffix included.
r = cl.lookup("info@ptttransportationllc.com")
check(len(r) == 1, f"ptttransportationllc: expected 1 match, got {len(r)}")
check(r and r[0]["legal_name"] == "PTT TRANSPORTATION LLC",
      f"ptttransportationllc: wrong name {r}")

# 2. Same company matches with the LLC suffix DROPPED from the domain.
r = cl.lookup("info@ptttransportation.com")
check(len(r) == 1 and r[0]["legal_name"] == "PTT TRANSPORTATION LLC",
      f"ptttransportation (no suffix): expected unique PTT match, got {r}")

# 3. Address parsed into street + 'CITY, ST ZIP', whitespace normalized.
r = cl.lookup("info@ptttransportationllc.com")
cs = r[0]["city_state"]
check("," in cs, f"city_state missing comma: {cs!r}")
check(r[0]["address"] != "", f"street address empty: {r[0]}")
check("\xa0" not in cs and "  " not in cs, f"city_state not whitespace-normalized: {cs!r}")

# 4. '&' in the name still matches a domain that drops it (D&G -> dg).
r = cl.lookup("info@dgtransportinc.com")
check(len(r) >= 2, f"dgtransportinc: expected >=2 (ambiguous), got {len(r)}")
check(all("&" in rec["legal_name"] for rec in r),
      f"dgtransportinc: expected D&G records, got {[x['legal_name'] for x in r]}")
check(len({rec["city_state"] for rec in r}) >= 2,
      f"dgtransportinc: expected distinct cities, got {[x['city_state'] for x in r]}")

# 5. No match -> empty list.
r = cl.lookup("info@zzznotarealcompanyxyz.com")
check(r == [], f"bogus domain: expected [], got {r}")

# 6. Bare domain (no @) also works.
r = cl.lookup("ptttransportationllc.com")
check(len(r) == 1, f"bare domain: expected 1, got {len(r)}")

if failures:
    for f in failures:
        print("FAIL:", f)
    sys.exit(1)
print("PASS: company_lookup matches suffix/&/ambiguous/no-match correctly")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python tests/test_company_lookup.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'company_lookup'`.

- [ ] **Step 3: Write the module**

Create `src/company_lookup.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python tests/test_company_lookup.py`
Expected: `PASS: company_lookup matches suffix/&/ambiguous/no-match correctly` and exit 0.

- [ ] **Step 5: Commit**

```bash
git add src/company_lookup.py tests/test_company_lookup.py
git commit -m "Add company_lookup: email -> company matcher over All Companies.csv"
```

---

### Task 2: Wire email auto-fill into the `/generate` flow

**Files:**
- Modify: `src/main.py` — add `import company_lookup` (near line 27, after `import queue`); add `_BARE_EMAIL_RE` (near `_GENERATE_FIELDS`, line 994); refactor the route-type prompt out of `_handle_generate_input` into `_ask_route_type`; add the bare-email branch at the top of `_handle_generate_input` (line 1012); add helpers `_handle_email_lookup` and `_apply_company_record`; update the `/generate` prompt text (line 835); add the `gen_company:<idx>` callback (in `handle_callback`, near the `gen_route:` handler at line 1798).
- Test: `tests/test_generate_autofill.py` (create)

**Interfaces:**
- Consumes: `company_lookup.lookup` (Task 1); existing `pending_generate`, `tg_send`, `tg_edit_message`, `_handle_generate_input`, `handle_callback`.
- Produces:
  - `_ask_route_type(chat_id) -> None` — sets `step="awaiting_route_type"` and sends the OTR/Regional/Random picker.
  - `_apply_company_record(chat_id, rec: dict) -> None` — fills `company_name`, `company_short`, `address`, `city_state` from a lookup record, then calls `_ask_route_type`.
  - `_handle_email_lookup(chat_id, email: str) -> None` — runs the lookup and routes to auto-fill / picker / manual fallback.
  - New callback data `gen_company:<idx>`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_generate_autofill.py`:

```python
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import main
import company_lookup

failures = []
sent = []
main.tg_send = lambda chat_id, text, **kw: sent.append((chat_id, text, kw))
main.tg_edit_message = lambda chat_id, mid, text, **kw: sent.append((chat_id, text, kw))

CHAT = 999


def reset(fake_matches):
    sent.clear()
    main.pending_generate.clear()
    main.pending_generate[CHAT] = {"step": "awaiting_info"}
    company_lookup.lookup = lambda email: list(fake_matches)


# 1. Unique match -> auto-fill + route-type prompt.
reset([{"legal_name": "PTT TRANSPORTATION LLC", "address": "138 FREIDA RD",
        "city_state": "LEXINGTON, SC 29073"}])
main._handle_generate_input(CHAT, "info@ptttransportationllc.com")
st = main.pending_generate[CHAT]
if st.get("company_name") != "PTT TRANSPORTATION LLC":
    failures.append(f"unique: company_name not filled: {st}")
if st.get("city_state") != "LEXINGTON, SC 29073":
    failures.append(f"unique: city_state not filled: {st}")
if st.get("domain") != "ptttransportationllc.com":
    failures.append(f"unique: domain wrong: {st}")
if st.get("step") != "awaiting_route_type":
    failures.append(f"unique: step not advanced: {st.get('step')}")
if not any("Route type" in t for _, t, _ in sent):
    failures.append("unique: route-type prompt not sent")

# 2. No match -> stays awaiting_info, no company filled, asks for manual.
reset([])
main._handle_generate_input(CHAT, "info@nope.com")
st = main.pending_generate[CHAT]
if "company_name" in st:
    failures.append(f"no-match: should not fill company: {st}")
if st.get("step") != "awaiting_info":
    failures.append(f"no-match: step changed: {st.get('step')}")
if not any("find" in t.lower() or "paste" in t.lower() for _, t, _ in sent):
    failures.append(f"no-match: no fallback prompt: {sent}")

# 3. Ambiguous -> stores candidates, sends a picker with one button per match.
reset([{"legal_name": "D&G TRANSPORT INC", "address": "1 A ST", "city_state": "LODI, CA 95242"},
       {"legal_name": "D&G TRANSPORT INC", "address": "2 B ST", "city_state": "ANNANDALE, VA 22003"}])
main._handle_generate_input(CHAT, "info@dgtransportinc.com")
st = main.pending_generate[CHAT]
if len(st.get("company_candidates", [])) != 2:
    failures.append(f"ambiguous: candidates not stored: {st}")
picker = [kw for _, _, kw in sent if kw.get("reply_markup")]
if not picker or len(picker[-1]["reply_markup"]["inline_keyboard"]) != 2:
    failures.append(f"ambiguous: expected 2-button picker, got {picker}")

# 4. Picker callback applies the chosen record.
main.handle_callback("cbid", CHAT, 123, "gen_company:1")
st = main.pending_generate[CHAT]
if st.get("city_state") != "ANNANDALE, VA 22003":
    failures.append(f"picker: wrong record applied: {st}")
if st.get("step") != "awaiting_route_type":
    failures.append(f"picker: step not advanced: {st.get('step')}")

# 5. Regression: a multi-line Label: block still uses manual parsing (no lookup).
reset([{"legal_name": "SHOULD NOT BE USED", "address": "x", "city_state": "y"}])
called = {"n": 0}
company_lookup.lookup = lambda email: (called.__setitem__("n", called["n"] + 1) or [])
main._handle_generate_input(
    CHAT, "Company: Acme Trucking\nEmail: info@acme.com\nAddress: 1 Main St, Dallas, TX 75001")
st = main.pending_generate[CHAT]
if called["n"] != 0:
    failures.append("regression: Label: block should not call lookup")
if st.get("company_name") != "Acme Trucking":
    failures.append(f"regression: manual parse broke: {st}")

if failures:
    for f in failures:
        print("FAIL:", f)
    sys.exit(1)
print("PASS: /generate email auto-fill (unique/no-match/ambiguous/picker/manual)")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python tests/test_generate_autofill.py`
Expected: FAIL — `AttributeError: module 'main' has no attribute 'company_lookup'` (the `import company_lookup` line in `main` does not exist yet), or assertion failures.

- [ ] **Step 3: Add the import**

In `src/main.py`, after the `import queue` line (added in the concurrency work, near line 27), add:

```python
import company_lookup
```

- [ ] **Step 4: Add the bare-email regex**

In `src/main.py`, immediately after the `_GENERATE_REQUIRED = [...]` line (line 1007), add:

```python
# A message that is ONLY an email address triggers CSV auto-fill.
_BARE_EMAIL_RE = re.compile(r"^\s*([^@\s]+@[^@\s]+\.[^@\s]+)\s*$")
```

- [ ] **Step 5: Refactor the route-type prompt into `_ask_route_type`**

In `src/main.py`, find the tail of `_handle_generate_input` (the manual path), which currently reads:

```python
    # Merge parsed into state, then ask for route type
    state.update(parsed)
    state["step"] = "awaiting_route_type"
    tg_send(chat_id, "🛣️ *Route type for this job?*",
            reply_markup={"inline_keyboard": [[
                {"text": "🚛 OTR", "callback_data": "gen_route:otr"},
                {"text": "🏠 Regional", "callback_data": "gen_route:regional"},
                {"text": "🎲 Random", "callback_data": "gen_route:random"},
            ]]})
```

Replace that block with:

```python
    # Merge parsed into state, then ask for route type
    state.update(parsed)
    _ask_route_type(chat_id)
```

Then, immediately **above** `def _handle_generate_input(chat_id, raw_text):` (line 1010), add the three helpers:

```python
def _ask_route_type(chat_id):
    """Advance the generate flow to the route-type picker."""
    pending_generate[chat_id]["step"] = "awaiting_route_type"
    tg_send(chat_id, "🛣️ *Route type for this job?*",
            reply_markup={"inline_keyboard": [[
                {"text": "🚛 OTR", "callback_data": "gen_route:otr"},
                {"text": "🏠 Regional", "callback_data": "gen_route:regional"},
                {"text": "🎲 Random", "callback_data": "gen_route:random"},
            ]]})


def _apply_company_record(chat_id, rec):
    """Fill the generate state from a company_lookup record, then ask route type."""
    state = pending_generate[chat_id]
    company = rec["legal_name"]
    state["company_name"] = company
    state["company_short"] = company
    state["address"] = rec.get("address", "")
    state["city_state"] = rec.get("city_state", "")
    state.pop("company_candidates", None)
    loc = ", ".join(p for p in (rec.get("address"), rec.get("city_state")) if p)
    tg_send(chat_id, f"✅ *{company}*\n{loc}")
    _ask_route_type(chat_id)


def _handle_email_lookup(chat_id, email):
    """Look the email's company up in the CSV and route to fill/picker/fallback."""
    state = pending_generate[chat_id]
    state["email"] = email
    state["domain"] = email.split("@", 1)[1]
    matches = company_lookup.lookup(email)
    if len(matches) == 1:
        _apply_company_record(chat_id, matches[0])
    elif len(matches) > 1:
        state["company_candidates"] = matches
        buttons = [[{"text": f"{m['legal_name']} — {m['city_state']}",
                     "callback_data": f"gen_company:{i}"}]
                   for i, m in enumerate(matches)]
        tg_send(chat_id,
                f"🏢 Found {len(matches)} companies with that name. Which location?",
                reply_markup={"inline_keyboard": buttons})
    else:
        tg_send(chat_id,
                "🔍 Couldn't find that company in the list.\n\n"
                "Paste the details instead:\n"
                "`Company: ...\nEmail: ...\nAddress: ...`")
```

- [ ] **Step 6: Add the bare-email branch to `_handle_generate_input`**

In `src/main.py`, at the very top of `_handle_generate_input`, right after `state = pending_generate[chat_id]` (line 1012), add:

```python
    # A lone email address -> auto-fill company + address from the CSV.
    m = _BARE_EMAIL_RE.match(raw_text)
    if m:
        _handle_email_lookup(chat_id, m.group(1))
        return
```

- [ ] **Step 7: Update the `/generate` prompt text**

In `src/main.py`, replace the `/generate` command prompt (line 835 block) with one that leads with the email shortcut:

```python
        tg_send(chat_id,
                "🏗️ *Website Generator*\n\n"
                "Send the company email — I'll look up the name & address:\n"
                "`info@company.com`\n\n"
                "_Or paste full details:_\n"
                "`Company: 2-3 Logistics Corp\n"
                "Email: info@2-3logisticscorp.com\n"
                "Address: 508 Linden Dr, Round Lake, IL 60073`")
```

- [ ] **Step 8: Add the `gen_company:<idx>` callback handler**

In `src/main.py`, in `handle_callback`, immediately **above** the `if data.startswith("gen_route:"):` block (line 1798), add:

```python
    if data.startswith("gen_company:"):
        state = pending_generate.get(chat_id)
        candidates = state.get("company_candidates") if state else None
        if not candidates:
            tg_edit_message(chat_id, message_id, "⚠️ No active generate flow.")
            return
        try:
            idx = int(data.split(":", 1)[1])
            rec = candidates[idx]
        except (ValueError, IndexError):
            tg_edit_message(chat_id, message_id, "⚠️ Invalid choice.")
            return
        tg_edit_message(chat_id, message_id, f"📍 {rec['legal_name']} — {rec['city_state']}")
        _apply_company_record(chat_id, rec)
        return
```

- [ ] **Step 9: Run the test to verify it passes**

Run: `.venv/bin/python tests/test_generate_autofill.py`
Expected: `PASS: /generate email auto-fill (unique/no-match/ambiguous/picker/manual)` and exit 0.

- [ ] **Step 10: Run the full suite + import smoke check (no regressions)**

Run:
```bash
.venv/bin/python tests/test_browser_gate.py && \
.venv/bin/python tests/test_auth_lock.py && \
.venv/bin/python tests/test_concurrency.py && \
.venv/bin/python tests/test_company_lookup.py && \
.venv/bin/python tests/test_generate_autofill.py && \
.venv/bin/python -c "import sys; sys.path.insert(0,'src'); import main; print('import ok')"
```
Expected: five `PASS` lines and `import ok`.

- [ ] **Step 11: Commit**

```bash
git add src/main.py tests/test_generate_autofill.py
git commit -m "Auto-fill /generate company + address from email via CSV lookup"
```

---

### Task 3: Manual end-to-end check (human)

**Files:** none.

- [ ] **Step 1:** Start the bot: `.venv/bin/python src/main.py`.
- [ ] **Step 2:** `/generate`, then send a unique company email (e.g. `info@ptttransportationllc.com`). Expect a `✅ PTT TRANSPORTATION LLC` confirmation with address, then the route-type picker; finishing produces the website zip + Indeed HTML as before.
- [ ] **Step 3:** `/generate`, then `info@kgtruckingllc.com` (ambiguous). Expect a 2-button location picker; tapping one continues the flow.
- [ ] **Step 4:** `/generate`, then `info@somethingnotinthelist.com`. Expect the "couldn't find — paste details" message; pasting the `Company:/Email:/Address:` block still works.

---

## Self-Review

**Spec coverage (vs. the agreed design):**
- Isolated `company_lookup.py`, lazy cached index → Task 1. ✅
- Normalize lowercase + strip non-alnum; full + no-suffix + `&`→`and` candidate keys → Task 1 `_candidate_keys`. ✅
- Address from CSV newlines (street / city_state), whitespace-normalized → Task 1 `_parse_address` + `_clean`. ✅
- Email-only primary input, `Label:` fallback → Task 2 Steps 6/7 (regex branch + prompt), regression test case 5. ✅
- 1 match auto-fill → Task 2 `_apply_company_record`; many → picker (`gen_company:`); 0 → manual fallback → Task 2 Steps 5/8 + test cases 1–4. ✅
- Missing CSV → no-match (manual fallback) → Task 1 `_build_index` `except OSError`. ✅
- Downstream generate pipeline unchanged → Task 2 reuses `_ask_route_type` + existing `_finish_generate`. ✅

**Placeholder scan:** No TBD/TODO; every code step shows full content. ✅

**Type consistency:** Record shape `{legal_name, address, city_state}` is identical in Task 1 (`_build_index`), its test, `_apply_company_record`, `_handle_email_lookup`, and the `gen_company` callback. `lookup` / `_ask_route_type` / `_apply_company_record` / `_handle_email_lookup` names match across tasks and tests. `state` keys (`company_name`, `company_short`, `address`, `city_state`, `email`, `domain`, `company_candidates`, `step`) match what `_finish_generate` already consumes. ✅

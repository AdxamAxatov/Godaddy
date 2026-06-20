# Indeed Appeal Generator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A `/appeal <website-url>` command that reads a generated company site and produces a unique, human-sounding Indeed reinstatement appeal (plain text) to paste into Indeed's "Additional information" box.

**Architecture:** Generated sites embed their exact posting data as breakout-safe JSON (`<script id="company-data">`). The appeal flow fetches the URL, reads that JSON back (exact match to what Indeed sees), and `generate_appeal(info)` writes a randomized plain-text appeal. The appeal is delivered as a `.txt` document (never a Markdown message — avoids Telegram parse errors). Owner name comes from the email local-part, falling back to a domain-seeded plausible name via an isolated RNG.

**Tech Stack:** Python 3.12 stdlib + `requests`. No new dependencies. Tests are standalone scripts run with `.venv/bin/python`.

## Global Constraints

- **Run tests with the venv:** `.venv/bin/python tests/<name>.py` — system Python lacks `requests`. Tests print which assertion failed and `sys.exit(1)` on failure; print `PASS` on success.
- **Changes only in `src/website_generator.py` and `src/main.py`** plus new files under `tests/`. No new dependencies.
- **FIX 1 — never Markdown-send the appeal.** `tg_send` hardcodes `parse_mode: "Markdown"` (main.py:283); the appeal is free prose and will contain `_`/`*`/`` ` ``. Deliver it as a `.txt` document via `tg_send_document` (raw file body, no parse).
- **FIX 2 — breakout-safe embed.** Encode embedded JSON with `json.dumps(data).replace("<", "\\u003c")` so a `<` or `</script>` in any field can't end the script tag.
- **FIX 3 — RNG isolation.** `website_generator` uses the global `random` 23× with no seeding. The domain-seeded owner-name pick MUST use a private `random.Random(seed)` instance; never call `random.seed()`.
- **FIX 4 — tolerant fetch.** Normalize the URL (prepend `https://` if no scheme); on any fetch error retry once with `verify=False` (it's the user's own public page) before giving up.
- **FIX 5 — owner name on the fallback path.** The domain-seeded name needs only the domain, so even an old site with no embed still yields a stable name.
- **Per-chat state needs no locks** — `pending_appeal` is keyed by `chat_id`, touched only by that chat's worker (matches existing `pending_*` convention).

---

### Task 1: Owner-name resolver

**Files:**
- Modify: `src/website_generator.py` — add `import re`; add `_resolve_owner_name`
- Test: `tests/test_owner_name.py` (create)

**Interfaces:**
- Produces: `_resolve_owner_name(email: str, domain: str) -> str` — personal email local-part → that name (title-cased); generic mailbox (`info@`, `sales@`, …) or empty → a plausible first name chosen by a private `random.Random(domain)` (stable per domain). Never touches global `random`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_owner_name.py`:

```python
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import website_generator as wg

failures = []

# Personal local-part -> that name.
if wg._resolve_owner_name("lorna@pressonlogistics.com", "pressonlogistics.com") != "Lorna":
    failures.append("personal email should yield 'Lorna'")

# Generic mailbox -> a name from the pool, STABLE per domain.
a = wg._resolve_owner_name("info@pressonlogistics.com", "pressonlogistics.com")
b = wg._resolve_owner_name("info@pressonlogistics.com", "pressonlogistics.com")
if a != b:
    failures.append(f"generic mailbox name not stable per domain: {a} != {b}")
if a not in wg._OWNER_FIRST_NAMES:
    failures.append(f"generic fallback name not from pool: {a}")

# Empty email still works off the domain.
if not wg._resolve_owner_name("", "pressonlogistics.com"):
    failures.append("empty email should still yield a name from domain")

# FIX 3: must NOT disturb the global RNG.
random.seed(0)
x = random.random()
wg._resolve_owner_name("info@somecarrier.com", "somecarrier.com")
random.seed(0)
y = random.random()
if x != y:
    failures.append("resolver disturbed the global RNG (must use private Random)")

if failures:
    for f in failures:
        print("FAIL:", f)
    sys.exit(1)
print("PASS: owner-name resolver (personal/generic/stable/RNG-isolated)")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python tests/test_owner_name.py`
Expected: FAIL — `AttributeError: module 'website_generator' has no attribute '_resolve_owner_name'`.

- [ ] **Step 3: Add `import re`**

In `src/website_generator.py`, the import block ends with `from pathlib import Path` (line 13). Add after `import json` (line 7):

```python
import re
```

- [ ] **Step 4: Implement the resolver**

In `src/website_generator.py`, add near the top (after the imports, before the stock-image section at line ~15):

```python
_GENERIC_MAILBOXES = {
    "info", "sales", "dispatch", "hr", "jobs", "contact", "office", "careers",
    "admin", "support", "recruiting", "drive", "driving", "apply", "hiring", "team",
}
_OWNER_FIRST_NAMES = [
    "Lorna", "Marcus", "Dana", "Priya", "Hector", "Renee", "Curtis", "Yolanda",
    "Devin", "Tanya", "Roy", "Camille", "Brett", "Nadia", "Glenn", "Shauna",
    "Andre", "Marisol", "Keith", "Bianca", "Dwayne", "Allison", "Hassan", "Gloria",
]


def _resolve_owner_name(email: str, domain: str) -> str:
    """Owner first name for the appeal. A personal email local-part becomes the
    name; a generic mailbox (info@, sales@, ...) or no email falls back to a
    plausible name seeded by the domain so it's stable per company. Uses a
    private RNG — never touches the global random state."""
    local = email.split("@", 1)[0] if email and "@" in email else ""
    cleaned = re.sub(r"[^a-zA-Z]", "", local)
    if cleaned and cleaned.lower() not in _GENERIC_MAILBOXES:
        return cleaned[:1].upper() + cleaned[1:].lower()
    seed = (domain or local or "carrier").lower()
    return random.Random(seed).choice(_OWNER_FIRST_NAMES)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `.venv/bin/python tests/test_owner_name.py`
Expected: `PASS: owner-name resolver (personal/generic/stable/RNG-isolated)`

- [ ] **Step 6: Commit**

```bash
git add src/website_generator.py tests/test_owner_name.py
git commit -m "Add owner-name resolver for appeals"
```

---

### Task 2: Company-data embed/extract codec

**Files:**
- Modify: `src/website_generator.py` — add `_company_data_script` + `extract_company_data`
- Test: `tests/test_company_data_codec.py` (create)

**Interfaces:**
- Produces:
  - `_company_data_script(data: dict) -> str` — returns `<script type="application/json" id="company-data">…</script>\n`, breakout-safe (`<` → `<`).
  - `extract_company_data(html: str) -> dict | None` — returns the embedded dict, or `None` if absent/unparseable.

- [ ] **Step 1: Write the failing test**

Create `tests/test_company_data_codec.py`:

```python
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import website_generator as wg

failures = []

# Round-trips, including hostile content (FIX 2): '<', '&', apostrophe, '</script>'.
data = {
    "company_name": "A<B & C's </script> LLC",
    "perks": ["401(k) with match", "Dental & Vision"],
    "pay_range": "$1,200 – $1,400 / week",
    "owner_name": "Lorna",
}
html = "<body>" + wg._company_data_script(data) + "<h1>hi</h1></body>"

# The embedded payload must not contain a raw closing tag that could break out.
inner = html.split('id="company-data">', 1)[1].split("</script>", 1)[0]
if "</script" in inner.lower():
    failures.append("embedded JSON can break out of the script tag")

out = wg.extract_company_data(html)
if out != data:
    failures.append(f"round-trip mismatch: {out}")

# Missing/garbage -> None.
if wg.extract_company_data("<body>no data here</body>") is not None:
    failures.append("missing embed should return None")
if wg.extract_company_data('<script id="company-data">{bad json</script>') is not None:
    failures.append("unparseable embed should return None")

if failures:
    for f in failures:
        print("FAIL:", f)
    sys.exit(1)
print("PASS: company-data codec round-trips and is breakout-safe")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python tests/test_company_data_codec.py`
Expected: FAIL — `AttributeError: module 'website_generator' has no attribute '_company_data_script'`.

- [ ] **Step 3: Implement the codec**

In `src/website_generator.py`, add immediately after `_resolve_owner_name` (Task 1):

```python
_COMPANY_DATA_RE = re.compile(
    r'<script[^>]*id="company-data"[^>]*>(.*?)</script>', re.DOTALL)


def _company_data_script(data: dict) -> str:
    """Embed posting data as breakout-safe JSON in a <script> tag."""
    payload = json.dumps(data).replace("<", "\\u003c")
    return f'<script type="application/json" id="company-data">{payload}</script>\n'


def extract_company_data(html: str):
    """Return the embedded company-data dict, or None if absent/unparseable."""
    m = _COMPANY_DATA_RE.search(html or "")
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except (ValueError, TypeError):
        return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python tests/test_company_data_codec.py`
Expected: `PASS: company-data codec round-trips and is breakout-safe`

- [ ] **Step 5: Commit**

```bash
git add src/website_generator.py tests/test_company_data_codec.py
git commit -m "Add breakout-safe company-data embed/extract codec"
```

---

### Task 3: Embed company-data into generated websites

**Files:**
- Modify: `src/website_generator.py` — `generate_website_from_blocks` (`2092` region; the `body = _nav(ctx) + ...` line ~2109)
- Test: `tests/test_site_embed.py` (create)

**Interfaces:**
- Consumes: `_resolve_owner_name`, `_company_data_script` (Tasks 1–2).
- Produces: every site from `generate_website_from_blocks(info)` contains a `company-data` script with `company_name, domain, email, address, city_state, owner_name, job_title, pay_range, home_time, min_experience, routes_type, perks`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_site_embed.py`:

```python
import os
import sys
import zipfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import website_generator as wg

failures = []

info = {
    "company_name": "Press On Logistics Express LLC",
    "company_short": "Press On",
    "domain": "pressonlogistics.com",
    "email": "info@pressonlogistics.com",
    "address": "1951 Southampton Rd Apt H6",
    "city_state": "Atlanta, GA 30349",
    "job_title": "Regional CDL-A Truck Driver",
    "pay_range": "$1,200 – $1,400 / week",
    "home_time": "Home weekly for 2 days",
    "home_time_short": "Weekly",
    "home_time_detail": "Home 2 Days",
    "min_experience": "1 year",
    "fourth_card_value": "1 Yr. Exp",
    "fourth_card_label": "Min. Required",
    "routes": "Multi-State",
    "routes_type": "Regional Routes",
    "perks": ["Dental & Vision insurance", "401(k) with match", "Fuel card"],
}

zip_path = wg.generate_website_from_blocks(info)
with zipfile.ZipFile(zip_path) as z:
    html = z.read("index.html").decode("utf-8")

data = wg.extract_company_data(html)
if not data:
    print("FAIL: no company-data embedded in generated site")
    sys.exit(1)
for key in ("company_name", "pay_range", "perks", "routes_type"):
    if data.get(key) != info[key]:
        failures.append(f"{key} mismatch: {data.get(key)!r} != {info[key]!r}")
if not data.get("owner_name"):
    failures.append("owner_name missing from embed")

if failures:
    for f in failures:
        print("FAIL:", f)
    sys.exit(1)
print("PASS: generated site embeds matching company-data")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python tests/test_site_embed.py`
Expected: FAIL — `FAIL: no company-data embedded in generated site`.

- [ ] **Step 3: Embed the data in `generate_website_from_blocks`**

In `src/website_generator.py`, find the body-assembly line in `generate_website_from_blocks`:

```python
    body = _nav(ctx) + hero + process + about + careers + contact + _footer(ctx)
```

Replace it with:

```python
    owner_name = _resolve_owner_name(info.get("email", ""), ctx["domain"])
    company_data = {
        "company_name": ctx["company_name"], "domain": ctx["domain"],
        "email": ctx["email"], "address": ctx["address"],
        "city_state": ctx["city_state"], "owner_name": owner_name,
        "job_title": ctx["job_title"], "pay_range": ctx["pay_range"],
        "home_time": ctx["home_time"], "min_experience": ctx["min_experience"],
        "routes_type": ctx["routes_type"], "perks": ctx["perks"],
    }
    body = (_company_data_script(company_data)
            + _nav(ctx) + hero + process + about + careers + contact + _footer(ctx))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python tests/test_site_embed.py`
Expected: `PASS: generated site embeds matching company-data`

- [ ] **Step 5: Run the full suite (no regressions)**

Run: `for t in tests/test_*.py; do .venv/bin/python "$t" >/dev/null 2>&1 && echo "PASS $(basename $t)" || echo "FAIL $(basename $t)"; done`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add src/website_generator.py tests/test_site_embed.py
git commit -m "Embed company-data JSON into generated websites"
```

---

### Task 4: `generate_appeal(info)` — the appeal text

**Files:**
- Modify: `src/website_generator.py` — add `_natural_list` + `generate_appeal`
- Test: `tests/test_generate_appeal.py` (create)

**Interfaces:**
- Consumes: `_resolve_owner_name` (Task 1).
- Produces: `generate_appeal(info: dict) -> str` — plain-text appeal (no HTML/Markdown), randomized per call. Uses `owner_name`/`company_name`/`city_state`/`job_title`/`pay_range`/`home_time`/`min_experience`/`perks`/`routes_type`/`domain`. Gracefully omits any missing posting facts.

- [ ] **Step 1: Write the failing test**

Create `tests/test_generate_appeal.py`:

```python
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from website_generator import generate_appeal

INFO = {
    "company_name": "Press On Logistics Express LLC",
    "domain": "pressonlogistics.com",
    "email": "info@pressonlogistics.com",
    "owner_name": "Lorna",
    "address": "1951 Southampton Rd Apt H6",
    "city_state": "Atlanta, GA 30349",
    "job_title": "Regional CDL-A Truck Driver",
    "pay_range": "$1,200 – $1,400 / week",
    "home_time": "Home weekly for 2 days",
    "min_experience": "1 year",
    "routes_type": "Regional Routes",
    "perks": ["Dental & Vision insurance", "401(k) with match", "Fuel card"],
}

failures = []
samples = [generate_appeal(INFO) for _ in range(60)]

for i, a in enumerate(samples):
    # Plain text only — no HTML/Markdown control chars (FIX 1 hygiene).
    for ch in ("<", "`", "*", "#"):
        if ch in a:
            failures.append(f"sample {i}: contains forbidden char {ch!r}")
            break
    # Hits the key facts.
    if "Lorna" not in a:
        failures.append(f"sample {i}: missing owner name")
    if "Press On Logistics Express LLC" not in a:
        failures.append(f"sample {i}: missing company name")
    if "$1,200" not in a:
        failures.append(f"sample {i}: missing pay")
    if "pressonlogistics.com" not in a:
        failures.append(f"sample {i}: missing site URL for verification")

# Uniqueness: highly varied across runs.
if len(set(samples)) < 30:
    failures.append(f"not unique enough: {len(set(samples))}/60 distinct")

# Works on partial data (older site: no job specifics) without crashing.
partial = generate_appeal({"company_name": "X LLC", "domain": "x.com",
                           "city_state": "Dallas, TX 75001", "owner_name": "Roy"})
if "Roy" not in partial or "X LLC" not in partial:
    failures.append("partial-data appeal missing name/company")

if failures:
    for f in failures[:10]:
        print("FAIL:", f)
    sys.exit(1)
print("PASS: generate_appeal — plain, factual, unique, partial-safe")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python tests/test_generate_appeal.py`
Expected: FAIL — `ImportError: cannot import name 'generate_appeal'`.

- [ ] **Step 3: Implement `generate_appeal`**

In `src/website_generator.py`, add after `generate_job_description` (ends ~line 724):

```python
def _natural_list(items) -> str:
    items = [str(i) for i in items if str(i).strip()]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def generate_appeal(info: dict) -> str:
    """Plain-text Indeed reinstatement appeal. Human-like and unique each run,
    built from the site's embedded company-data. Omits missing posting facts."""
    company = info.get("company_name", "our company")
    domain = info.get("domain", "")
    city_state = info.get("city_state", "")
    city_only = city_state.split(",")[0].strip() if "," in city_state else city_state
    owner = info.get("owner_name") or _resolve_owner_name(info.get("email", ""), domain)
    job_title = info.get("job_title", "CDL-A Truck Driver")
    pay_range = info.get("pay_range", "")
    home_time = info.get("home_time", "")
    min_exp = info.get("min_experience", "")
    routes_type = info.get("routes_type", "OTR Routes")
    is_regional = "regional" in routes_type.lower()
    route_label = "Regional" if is_regional else "OTR"
    territory = "a focused multi-state region" if is_regional else "the lower 48"
    perks = info.get("perks", [])

    openings = [
        f"My name is {owner} and I run {company} out of {city_only}.",
        f"I'm {owner}, the owner of {company} here in {city_only}.",
        f"This is {owner} from {company} — we're a carrier based in {city_only}.",
        f"My name's {owner} and I own and operate {company} in {city_only}.",
        f"I'm {owner}, and I handle the day-to-day at {company} out of {city_only}.",
    ]
    nature = [
        f"We're a small {route_label.lower()} dry van carrier covering {territory}.",
        f"We run {route_label} dry van freight across {territory} — nothing fancy, just steady work.",
        f"We're a {route_label.lower()} carrier hauling dry van across {territory} with our own trucks.",
        f"We do {route_label} dry van runs across {territory}.",
    ]
    intros = [
        "I'm writing to appeal a flagged posting on our account.",
        "I'm reaching out to appeal a posting that got paused on our account.",
        "I wanted to follow up on a posting of ours that was flagged.",
    ]

    job_bits = []
    if pay_range:
        job_bits.append(f"The job we listed is a {job_title} paying {pay_range}.")
    else:
        job_bits.append(f"The job we listed is a {job_title}.")
    if home_time:
        job_bits.append(f"Home time is {home_time}.")
    if min_exp:
        job_bits.append(f"We ask for {min_exp} of CDL-A experience.")
    if perks:
        job_bits.append("We offer " + _natural_list(perks[:6]) + ".")
    job_block = " ".join(job_bits)

    legitimacy = [
        "I handle the hiring myself, so every application comes straight to me.",
        "There's no agency or third party involved — it's just us looking for a driver.",
        "We posted because we genuinely need a driver, plain and simple.",
        "Nothing about the posting is misleading; it's a real job at a real company.",
        "We're a small operation, and every hire matters to us.",
        "I'm the one reviewing applications and making the calls.",
    ]
    beats = " ".join(random.sample(legitimacy, k=random.randint(2, 3)))

    asks = [
        "I'd really appreciate it if you could take another look and reinstate the posting.",
        "I'd be grateful if this could be reviewed and put back up.",
        "Please take another look — I'd love to get this posting back online.",
        "I'm hoping you can review this and reinstate our access.",
    ]
    if domain:
        closes = [
            f"You can verify everything about us at {domain}, and I'm happy to send over any documents you need.",
            f"Everything checks out on our site at {domain}, and I can provide whatever paperwork helps.",
            f"Our site {domain} has all our company details, and I'll gladly share documents to confirm we're legitimate.",
        ]
    else:
        closes = [
            "I'm happy to send over any documents you need to verify us.",
            "I can provide whatever paperwork helps verify us.",
        ]

    p1 = " ".join([random.choice(openings), random.choice(nature), random.choice(intros)])
    p3 = " ".join([random.choice(asks), random.choice(closes)])
    paragraphs = [p1, job_block, beats, p3] if job_block else [p1, beats, p3]
    return "\n\n".join(p for p in paragraphs if p)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python tests/test_generate_appeal.py`
Expected: `PASS: generate_appeal — plain, factual, unique, partial-safe`

- [ ] **Step 5: Commit**

```bash
git add src/website_generator.py tests/test_generate_appeal.py
git commit -m "Add generate_appeal — randomized plain-text Indeed appeal"
```

---

### Task 5: `_fetch_company_data(url)` — fetch + extract + fallback

**Files:**
- Modify: `src/main.py` — add `_fetch_company_data`
- Test: `tests/test_fetch_company_data.py` (create)

**Interfaces:**
- Consumes: `website_generator.extract_company_data` (Task 2), `company_lookup.lookup`, `_http`.
- Produces: `_fetch_company_data(url: str) -> tuple` — returns `(data: dict, partial: bool)` or `(None, False)`. Embedded data → `(data, False)`. No embed but domain matches CSV → `(partial_dict, True)`. Otherwise `(None, False)`. Tolerant fetch (FIX 4): normalize scheme, retry once with `verify=False`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_fetch_company_data.py`:

```python
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import main
import website_generator as wg

failures = []


class _Resp:
    def __init__(self, text):
        self.text = text


# Case A: page has an embed -> (data, False).
embed_html = "<body>" + wg._company_data_script(
    {"company_name": "Z LLC", "domain": "z.com", "pay_range": "$1k", "perks": []}) + "</body>"
main._http = lambda method, url, **kw: _Resp(embed_html)
data, partial = main._fetch_company_data("z.com")  # no scheme -> normalized
if not data or data.get("company_name") != "Z LLC" or partial:
    failures.append(f"embed case wrong: {(data, partial)}")

# Case B: first fetch raises (SSL), retry succeeds (FIX 4).
calls = {"n": 0}
def flaky(method, url, **kw):
    calls["n"] += 1
    if kw.get("verify", True):
        raise main.requests.exceptions.SSLError("bad cert")
    return _Resp(embed_html)
main._http = flaky
data, partial = main._fetch_company_data("https://z.com")
if not data or calls["n"] < 2:
    failures.append(f"SSL retry path failed: calls={calls['n']} data={bool(data)}")

# Case C: no embed, domain matches CSV -> partial.
main._http = lambda method, url, **kw: _Resp("<body>no embed</body>")
main.company_lookup.lookup = lambda d: [
    {"legal_name": "CSV Carrier LLC", "address": "1 A St", "city_state": "Dallas, TX 75001"}]
data, partial = main._fetch_company_data("csvcarrier.com")
if not data or not partial or data.get("company_name") != "CSV Carrier LLC":
    failures.append(f"CSV fallback wrong: {(data, partial)}")

# Case D: no embed, no CSV match -> (None, False).
main.company_lookup.lookup = lambda d: []
data, partial = main._fetch_company_data("nope.com")
if data is not None:
    failures.append(f"no-data case should be None: {(data, partial)}")

if failures:
    for f in failures:
        print("FAIL:", f)
    sys.exit(1)
print("PASS: _fetch_company_data (embed / SSL-retry / CSV fallback / none)")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python tests/test_fetch_company_data.py`
Expected: FAIL — `AttributeError: module 'main' has no attribute '_fetch_company_data'`.

- [ ] **Step 3: Implement `_fetch_company_data`**

In `src/main.py`, add immediately above `def _deploy_to_cpanel` (the function added in the addon-recovery work, just above `handle_callback`):

```python
def _fetch_company_data(url):
    """Fetch a deployed site and return (company_data, partial). Reads the
    embedded company-data JSON when present (partial=False); else falls back to
    a domain->CSV lookup for name/address (partial=True, job specifics absent);
    else (None, False)."""
    from website_generator import extract_company_data
    u = (url or "").strip()
    if not u.startswith(("http://", "https://")):
        u = "https://" + u
    html = None
    for verify in (True, False):
        try:
            html = _http("GET", u, timeout=20, verify=verify).text
            break
        except Exception as e:
            log.warning(f"appeal fetch (verify={verify}) failed: {e}")
    if html:
        data = extract_company_data(html)
        if data:
            return data, False
    domain = u.split("//", 1)[-1].split("/", 1)[0]
    matches = company_lookup.lookup(domain)
    if len(matches) == 1:
        m = matches[0]
        return {
            "company_name": m["legal_name"], "address": m.get("address", ""),
            "city_state": m.get("city_state", ""), "domain": domain,
            "owner_name": "", "perks": [],
        }, True
    return None, False
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python tests/test_fetch_company_data.py`
Expected: `PASS: _fetch_company_data (embed / SSL-retry / CSV fallback / none)`

- [ ] **Step 5: Commit**

```bash
git add src/main.py tests/test_fetch_company_data.py
git commit -m "Add _fetch_company_data for the appeal flow"
```

---

### Task 6: `/appeal` command, flow, and `.txt` delivery

**Files:**
- Modify: `src/main.py` — add `pending_appeal` dict (near the other pending dicts, `605` region); add `_start_appeal`; add the `/appeal` command + pending-URL routing (before the unknown-command line `980`); add `pending_appeal` to `/cancel` cleanup; update `/start` help (`705–712`), the unknown-command string (`980`), and `tg_set_commands` menu (`2390` region)
- Test: `tests/test_appeal_flow.py` (create)

**Interfaces:**
- Consumes: `_fetch_company_data` (Task 5), `website_generator.generate_appeal` (Task 4), `tg_send_document`, `tg_send`.
- Produces: `pending_appeal: dict`; `_start_appeal(chat_id, url) -> None` (fetches, generates, sends the appeal as a `.txt` document — FIX 1).

- [ ] **Step 1: Write the failing test**

Create `tests/test_appeal_flow.py`:

```python
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import main

failures = []
sent = []
docs = []
main.tg_send = lambda chat_id, text, **kw: sent.append(text)
main.tg_send_document = lambda chat_id, path, caption=None: docs.append((path, open(path, encoding="utf-8").read()))

import website_generator
website_generator.generate_appeal = lambda info: f"APPEAL for {info.get('company_name')}"

# Full embed -> delivers a .txt document, no partial warning.
main._fetch_company_data = lambda url: ({"company_name": "Z LLC", "domain": "z.com"}, False)
main.pending_appeal.clear()
docs.clear(); sent.clear()
main.handle_message(42, "/appeal https://z.com")
if not docs or "APPEAL for Z LLC" not in docs[-1][1]:
    failures.append(f"did not deliver appeal document: {docs}")
if docs and not docs[-1][0].endswith(".txt"):
    failures.append("appeal must be delivered as .txt (FIX 1)")

# Two-step flow: /appeal then URL message.
main.pending_appeal.clear(); docs.clear()
main.handle_message(42, "/appeal")
if 42 not in main.pending_appeal:
    failures.append("/appeal with no url should await a url")
main.handle_message(42, "z.com")
if not docs:
    failures.append("URL follow-up did not produce an appeal")
if 42 in main.pending_appeal:
    failures.append("pending_appeal not cleared after delivery")

# Partial data -> still delivers, plus a warning.
main._fetch_company_data = lambda url: ({"company_name": "Old LLC", "domain": "old.com"}, True)
main.pending_appeal.clear(); docs.clear(); sent.clear()
main.handle_message(42, "/appeal old.com")
if not docs:
    failures.append("partial path should still deliver an appeal")
if not any("older site" in s.lower() or "left out" in s.lower() for s in sent):
    failures.append(f"partial path should warn about missing specifics: {sent}")

# No data -> clean error, no document.
main._fetch_company_data = lambda url: (None, False)
main.pending_appeal.clear(); docs.clear(); sent.clear()
main.handle_message(42, "/appeal bad.com")
if docs:
    failures.append("no-data path should not deliver a document")
if not any("couldn't" in s.lower() or "make sure" in s.lower() for s in sent):
    failures.append(f"no-data path should send an error: {sent}")

if failures:
    for f in failures:
        print("FAIL:", f)
    sys.exit(1)
print("PASS: /appeal flow (delivery / two-step / partial / error)")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python tests/test_appeal_flow.py`
Expected: FAIL — `AttributeError: module 'main' has no attribute 'pending_appeal'`.

- [ ] **Step 3: Add the `pending_appeal` dict**

In `src/main.py`, next to the other pending dicts (near `pending_remove_domain = {}`, line ~605), add:

```python
pending_appeal = {}  # chat_id -> {step}
```

- [ ] **Step 4: Add `_start_appeal`**

In `src/main.py`, add immediately above `_fetch_company_data` (Task 5):

```python
def _start_appeal(chat_id, url):
    """Generate an Indeed reinstatement appeal from a deployed site URL and send
    it as a .txt document (never a Markdown message)."""
    from website_generator import generate_appeal
    tg_send(chat_id, "⏳ Reading your site and writing the appeal...")
    data, partial = _fetch_company_data(url)
    if not data:
        tg_send(chat_id, "🔴 Couldn't read company info from that link.\n"
                "Make sure it's the deployed site URL, e.g. `https://yourcompany.com`.")
        return
    appeal = generate_appeal(data)
    safe = (data.get("domain") or "appeal").replace(".", "_")
    path = os.path.join(tempfile.gettempdir(), f"{safe}_appeal.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(appeal)
    tg_send_document(chat_id, path,
                     caption="📋 Indeed appeal — paste into the *Additional information* box.")
    if partial:
        tg_send(chat_id, "⚠️ That's an older site with no embedded job data, so pay / home "
                "time / experience were left out — add them before submitting.")
    try:
        os.remove(path)
    except OSError:
        pass
```

- [ ] **Step 5: Add the `/appeal` command + pending-URL routing**

In `src/main.py`, immediately **before** the unknown-command line (`tg_send(chat_id, "⚠️ Unknown command. Use ...")`, line ~980), add:

```python
    # Command: /appeal — generate an Indeed reinstatement appeal from a site URL
    if text == "/appeal" or text.startswith("/appeal "):
        url = raw_text.split(" ", 1)[1].strip() if " " in raw_text else ""
        if url:
            pending_appeal.pop(chat_id, None)
            _start_appeal(chat_id, url)
        else:
            pending_appeal[chat_id] = {"step": "awaiting_url"}
            tg_send(chat_id, "🧾 *Indeed Appeal*\n\nSend your deployed website link, "
                    "e.g. `https://yourcompany.com`.")
        return

    if chat_id in pending_appeal:
        pending_appeal.pop(chat_id, None)
        _start_appeal(chat_id, raw_text.strip())
        return
```

> Use `raw_text` (case preserved) for the URL — `text` is lowercased earlier in `handle_message`.

- [ ] **Step 6: Add `pending_appeal` to `/cancel` cleanup**

In `src/main.py`, in the `/cancel` block, after the `_pending_slot_recovery` cleanup (added in the addon-recovery work), add:

```python
        if chat_id in pending_appeal:
            del pending_appeal[chat_id]
            cancelled = True
```

- [ ] **Step 7: Surface `/appeal` in help + menu**

In `src/main.py`, in the `/start` help, change the last line:

```python
                "• /remove\\_domain — remove a domain from hosting")
```

to:

```python
                "• /remove\\_domain — remove a domain from hosting\n"
                "• /appeal — generate an Indeed reinstatement appeal")
```

Then change the unknown-command string (`980`) to include `/appeal`:

```python
    tg_send(chat_id, "⚠️ Unknown command. Use `/setup`, `/generate`, `/appeal`, `/run_autossl`, `/remove_domain`, or `/start`.")
```

Then in `tg_set_commands()`, add after the `remove_domain` entry:

```python
        {"command": "appeal", "description": "Generate an Indeed reinstatement appeal"},
```

- [ ] **Step 8: Run test to verify it passes**

Run: `.venv/bin/python tests/test_appeal_flow.py`
Expected: `PASS: /appeal flow (delivery / two-step / partial / error)`

- [ ] **Step 9: Run the full suite + import smoke**

Run:
```bash
.venv/bin/python -c "import sys; sys.path.insert(0,'src'); import main; print('import ok')" && \
for t in tests/test_*.py; do .venv/bin/python "$t" >/dev/null 2>&1 && echo "PASS $(basename $t)" || echo "FAIL $(basename $t)"; done
```
Expected: `import ok` then all PASS.

- [ ] **Step 10: Commit**

```bash
git add src/main.py tests/test_appeal_flow.py
git commit -m "Add /appeal command: site URL -> Indeed reinstatement appeal"
```

---

### Task 7: Manual end-to-end verification

**Files:** none (manual run).

- [ ] **Step 1:** Start the bot — `.venv/bin/python src/main.py`. The Telegram menu now lists `/appeal`.
- [ ] **Step 2:** Run `/generate` for a company and deploy the site (so a live URL with embedded data exists).
- [ ] **Step 3:** `/appeal https://<that-domain>` → you receive a `.txt` document; open it and confirm a natural, plain-text appeal naming the owner, company, city, the job (title/pay/home time/experience/perks), and the site URL.
- [ ] **Step 4:** Run `/appeal https://<same-domain>` a few more times → each appeal reads differently (unique styling).
- [ ] **Step 5:** `/appeal` with no URL → bot asks for the link; send the link → same result. `/cancel` mid-flow → "🚫 Cancelled."
- [ ] **Step 6:** `/appeal https://<a-site-generated-before-this-change>` (no embed) → still get an appeal from the CSV name/address, plus the "older site … add them" warning.

---

## Self-Review

**Spec coverage:**
- Owner name from email local-part, generic→domain-seeded, RNG-isolated (FIX 3, FIX 5) → Task 1. ✅
- Embed exact posting data, breakout-safe (FIX 2) → Tasks 2–3. ✅
- Plain-text, unique, human-like appeal hitting Indeed's three asks (nature / legitimacy / verification) → Task 4. ✅
- Read data back from the URL with tolerant fetch + CSV fallback (FIX 4) → Task 5. ✅
- `/appeal` command, two-step flow, `.txt` delivery (FIX 1), partial warning, /cancel, help, menu → Task 6. ✅
- Manual verification → Task 7. ✅

**Placeholder scan:** No TBD/TODO; every code step shows full content. ✅

**Type consistency:** `_resolve_owner_name(email, domain)`, `_company_data_script(data)`/`extract_company_data(html)`, `generate_appeal(info)`, `_fetch_company_data(url) -> (data, partial)`, `_start_appeal(chat_id, url)`, `pending_appeal`, and the embed key set (`company_name…perks` + `owner_name`) are used identically across tasks and tests. `tg_send_document(chat_id, path, caption=)` matches main.py's existing signature. The `(data, partial)` tuple shape is consistent between Tasks 5 and 6. ✅

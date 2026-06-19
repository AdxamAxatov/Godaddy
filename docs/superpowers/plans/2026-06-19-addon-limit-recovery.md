# Addon-Limit Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When a cPanel deploy hits the 50 addon-domain cap, let the user remove one of the account's addon domains (tap-to-pick) and retry the failed deploy, with a manual-cPanel fallback when automatic removal isn't possible.

**Architecture:** Detect the cap error at the create-domain failure point in both `/generate`-deploy and `/setup`. Route to a new `_offer_free_slot` that lists the account's addon domains as inline buttons (indexed) and stashes a retry context in a chat-keyed `_pending_slot_recovery` dict. New `freeslot_*` callbacks confirm removal, then offer a Retry that re-dispatches the stashed context (re-running the extracted `_deploy_to_cpanel` for generate, or `_start_website_setup` for setup). Any removal failure routes to a shared manual-cPanel message.

**Tech Stack:** Python 3.12 stdlib + `requests`. No new dependencies. Tests are standalone scripts run with `.venv/bin/python`.

## Global Constraints

- **Run tests with the venv:** `.venv/bin/python tests/<name>.py` — system Python lacks `requests`. Tests print which assertion failed and `sys.exit(1)` on failure; print `PASS` on success.
- **All changes in `src/main.py`** plus new files under `tests/`. No new dependencies.
- **Per-chat state needs no locks** — `_pending_slot_recovery` is keyed by `chat_id` and touched only by that chat's worker (matches existing `pending_*` convention).
- **Telegram callback_data ≤ 64 bytes** — select domains by index (`freeslot_rm:<idx>`), never embed raw domain strings.
- **`account['url']` only** in user messages — never credentials.
- Module is import-safe (no network at import); tests `import main` after adding `src/` to `sys.path`.

---

### Task 1: Detection helper `_is_addon_limit_error`

**Files:**
- Modify: `src/main.py` — `_friendly_cpanel_error` (`460`)
- Test: `tests/test_addon_limit_detect.py` (create)

**Interfaces:**
- Produces: `_is_addon_limit_error(error_msg: str) -> bool` — True for the addon-domain cap phrasings. `_friendly_cpanel_error` is refactored to call it.

- [ ] **Step 1: Write the failing test**

Create `tests/test_addon_limit_detect.py`:

```python
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import main

failures = []

cap_msgs = [
    "Sorry, you have reached your maximum number (50) of addon domains.",
    "The maximum number of addon domains the account may have has been reached.",
    "Addon domain limit exceeded.",
]
for m in cap_msgs:
    if not main._is_addon_limit_error(m):
        failures.append(f"should detect cap: {m!r}")

for m in ["DNS zone could not be created", "Domain already exists", ""]:
    if main._is_addon_limit_error(m):
        failures.append(f"should NOT detect cap: {m!r}")

# _friendly_cpanel_error still flags the cap and passes generic through.
if "limit" not in main._friendly_cpanel_error(cap_msgs[0]).lower():
    failures.append("friendly error lost cap message")
if "DNS zone" not in main._friendly_cpanel_error("DNS zone could not be created"):
    failures.append("friendly error lost generic message")

if failures:
    for f in failures:
        print("FAIL:", f)
    sys.exit(1)
print("PASS: _is_addon_limit_error detects cap, _friendly_cpanel_error intact")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python tests/test_addon_limit_detect.py`
Expected: FAIL — `AttributeError: module 'main' has no attribute '_is_addon_limit_error'`.

- [ ] **Step 3: Implement**

In `src/main.py`, replace the `_friendly_cpanel_error` body (currently `460`):

```python
def _is_addon_limit_error(error_msg: str) -> bool:
    """True when a cPanel failure is the addon-domain cap (a hard limit)."""
    low = (error_msg or "").lower()
    return "addon" in low and ("maximum" in low or "limit" in low
                               or "reached" in low or "exceed" in low)


def _friendly_cpanel_error(error_msg: str) -> str:
    """Turn a raw cPanel failure string into a clear, actionable user message."""
    if _is_addon_limit_error(error_msg):
        return ("🔴 This hosting account is full — the 50 addon-domain limit has "
                "been reached.\nFree a slot with `/remove_domain`, or deploy to "
                "another hosting account.")
    return f"🔴 Failed to add domain to hosting:\n`{error_msg}`"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python tests/test_addon_limit_detect.py`
Expected: `PASS: _is_addon_limit_error detects cap, _friendly_cpanel_error intact`

- [ ] **Step 5: Commit**

```bash
git add src/main.py tests/test_addon_limit_detect.py
git commit -m "Add _is_addon_limit_error predicate"
```

---

### Task 2: Shared `_list_addon_domains` helper

**Files:**
- Modify: `src/main.py` — extract from `_start_remove_domain` (`1479–1490` region)
- Test: `tests/test_list_addon_domains.py` (create)

**Interfaces:**
- Produces: `_list_addon_domains(account: dict) -> list[str]` — returns `data["addon_domains"]` (addon only, never main/parked). Raises on HTTP failure.
- `_start_remove_domain` reuses it for its existence check (keeping its own addon+parked+main union locally for validation).

- [ ] **Step 1: Write the failing test**

Create `tests/test_list_addon_domains.py`:

```python
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import main

failures = []


class _Resp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload

# Returns ONLY addon_domains, not main/parked.
payload = {"data": {
    "addon_domains": ["a.com", "b.com"],
    "parked_domains": ["p.com"],
    "main_domain": "main.com",
}}
main._http = lambda method, url, **kw: _Resp(payload)
account = {"url": "https://cp", "username": "u", "password": "x", "label": "L"}
# _cpanel_headers must not blow up on this account shape:
out = main._list_addon_domains(account)
if out != ["a.com", "b.com"]:
    failures.append(f"expected only addon domains, got {out}")

if failures:
    for f in failures:
        print("FAIL:", f)
    sys.exit(1)
print("PASS: _list_addon_domains returns addon domains only")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python tests/test_list_addon_domains.py`
Expected: FAIL — `AttributeError: module 'main' has no attribute '_list_addon_domains'`.

- [ ] **Step 3: Implement the helper**

In `src/main.py`, add this function immediately above `def _start_remove_domain` (`1456`):

```python
def _list_addon_domains(account: dict) -> list:
    """Return the account's addon domains (addon only — not main/parked)."""
    url = f"{account['url']}/execute/DomainInfo/list_domains"
    resp = _http("GET", url, headers=_cpanel_headers(account), timeout=15, verify=True)
    resp.raise_for_status()
    data = resp.json().get("data", {})
    return list(data.get("addon_domains", []))
```

- [ ] **Step 4: Refactor `_start_remove_domain` to use it**

In `src/main.py`, replace the existence-check block (`1480–1486`):

```python
    try:
        url = f"{account['url']}/execute/DomainInfo/list_domains"
        resp = _http("GET", url, headers=_cpanel_headers(account), timeout=15, verify=True)
        resp.raise_for_status()
        data = resp.json().get("data", {})
        addon_domains = data.get("addon_domains", [])
        all_domains = addon_domains + data.get("parked_domains", []) + [data.get("main_domain", "")]
        if domain not in all_domains:
```

with (reuse the helper for the addon part; keep parked+main union for validation):

```python
    try:
        url = f"{account['url']}/execute/DomainInfo/list_domains"
        resp = _http("GET", url, headers=_cpanel_headers(account), timeout=15, verify=True)
        resp.raise_for_status()
        data = resp.json().get("data", {})
        all_domains = (list(data.get("addon_domains", []))
                       + list(data.get("parked_domains", []))
                       + [data.get("main_domain", "")])
        if domain not in all_domains:
```

> Note: this keeps `_start_remove_domain`'s own validation union intact. `_list_addon_domains` is the reusable accessor that `_offer_free_slot` (Task 4) uses; both hit the same endpoint. We do not force `_start_remove_domain` through the helper here because it needs the parked/main lists too.

- [ ] **Step 5: Run test to verify it passes**

Run: `.venv/bin/python tests/test_list_addon_domains.py`
Expected: `PASS: _list_addon_domains returns addon domains only`

- [ ] **Step 6: Run the full suite (no regressions)**

Run: `for t in tests/test_*.py; do .venv/bin/python "$t" >/dev/null 2>&1 && echo "PASS $t" || echo "FAIL $t"; done`
Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
git add src/main.py tests/test_list_addon_domains.py
git commit -m "Extract _list_addon_domains helper"
```

---

### Task 3: Extract `_deploy_to_cpanel` from the deploy callback

**Files:**
- Modify: `src/main.py` — `gen_deploy_acc` callback (`2159–2223`)
- Test: `tests/test_deploy_extract.py` (create)

**Interfaces:**
- Produces: `_deploy_to_cpanel(chat_id, domain, zip_path, account_idx) -> None` — runs create-domain → upload → extract → server-delete. Touches **neither** `_pending_deploys` **nor** `_pending_slot_recovery`. On the addon cap it will call `_offer_free_slot` (wired in Task 5; this task leaves the existing `_friendly_cpanel_error` message in place).
- `gen_deploy_acc` becomes a thin wrapper: pops `_pending_deploys[chat_id]`, then calls `_deploy_to_cpanel`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_deploy_extract.py`:

```python
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import main

failures = []

# Stub cPanel + Telegram + filesystem-free zip removal.
calls = []
main.tg_send = lambda chat_id, text, **kw: calls.append(("send", text))
main.cpanel_create_domain = lambda domain, account: calls.append(("create", domain)) or {"errors": None}
main.cpanel_upload_file = lambda zip_path, dest, account: calls.append(("upload", dest))
main.cpanel_extract_file = lambda archive, dest, account: calls.append(("extract", archive))
main.cpanel_delete_file = lambda archive, account: calls.append(("delete", archive))
main.os.remove = lambda p: calls.append(("rm", p))

# Needs at least one cPanel account.
main.CPANEL_ACCOUNTS = [{"url": "https://cp", "username": "u", "password": "x", "label": "L"}]

main._deploy_to_cpanel(123, "example.com", "/tmp/example_com.zip", 0)

names = [c[0] for c in calls]
for required in ("create", "upload", "extract", "delete"):
    if required not in names:
        failures.append(f"deploy did not run {required}: {names}")
# Order: create before upload before extract.
if not (names.index("create") < names.index("upload") < names.index("extract")):
    failures.append(f"deploy steps out of order: {names}")

if failures:
    for f in failures:
        print("FAIL:", f)
    sys.exit(1)
print("PASS: _deploy_to_cpanel runs create->upload->extract->delete")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python tests/test_deploy_extract.py`
Expected: FAIL — `AttributeError: module 'main' has no attribute '_deploy_to_cpanel'`.

- [ ] **Step 3: Implement — add `_deploy_to_cpanel` above `handle_callback`**

In `src/main.py`, add immediately above `def handle_callback` (`1847`):

```python
def _deploy_to_cpanel(chat_id, domain, zip_path, account_idx):
    """Create the domain, upload + extract the zip, delete the server-side zip.

    Takes explicit params (no _pending_deploys / _pending_slot_recovery access),
    so both the original deploy and the post-removal retry call it the same way.
    """
    account = CPANEL_ACCOUNTS[account_idx]

    # Create domain on cPanel
    tg_send(chat_id, f"🌐 Adding `{domain}` to hosting ({account['label']})...")
    try:
        result = cpanel_create_domain(domain, account)
        errors = result.get("errors")
        if errors:
            error_msg = str(errors)
            if "already" in error_msg.lower() or "exists" in error_msg.lower():
                tg_send(chat_id, f"ℹ️ `{domain}` already exists in hosting. Continuing...")
            else:
                tg_send(chat_id, _friendly_cpanel_error(error_msg))
                return
        else:
            tg_send(chat_id, f"✅ `{domain}` added to hosting!")
    except Exception as e:
        tg_send(chat_id, f"🔴 Failed to add domain:\n`{e}`")
        return

    # Upload zip to cPanel
    dest_dir = f"/public_html/{domain}"
    file_name = Path(zip_path).name
    tg_send(chat_id, f"📤 Uploading to `{dest_dir}`...")
    try:
        cpanel_upload_file(zip_path, dest_dir, account)
        log.info(f"Uploaded {file_name} to {dest_dir}")
    except Exception as e:
        tg_send(chat_id, f"🔴 Upload failed:\n`{e}`")
        return
    finally:
        try:
            os.remove(zip_path)
        except OSError:
            pass

    # Extract
    archive_path = f"{dest_dir}/{file_name}"
    tg_send(chat_id, f"📂 Extracting `{file_name}`...")
    try:
        cpanel_extract_file(archive_path, dest_dir, account)
        log.info(f"Extracted {file_name} in {dest_dir}")
    except Exception as e:
        tg_send(chat_id, f"🔴 Extraction failed:\n`{e}`")
        return

    # Delete zip from server
    try:
        cpanel_delete_file(archive_path, account)
    except Exception:
        pass

    tg_send(chat_id,
            f"✅ *Website deployed!*\n\n"
            f"Domain: `{domain}`\n"
            f"Your site should be live at: http://{domain}")
    log.info(f"Generated website deployed for {domain}")
```

- [ ] **Step 4: Replace the `gen_deploy_acc` body with a thin wrapper**

In `src/main.py`, replace the whole block `2159–2223` (from `if data.startswith("gen_deploy_acc:"):` through its final `return`) with:

```python
    if data.startswith("gen_deploy_acc:"):
        deploy = _pending_deploys.pop(chat_id, None)
        if not deploy:
            return
        idx = int(data.split(":")[1])
        _deploy_to_cpanel(chat_id, deploy["domain"], deploy["zip_path"], idx)
        return
```

- [ ] **Step 5: Run test to verify it passes**

Run: `.venv/bin/python tests/test_deploy_extract.py`
Expected: `PASS: _deploy_to_cpanel runs create->upload->extract->delete`

- [ ] **Step 6: Run the full suite**

Run: `for t in tests/test_*.py; do .venv/bin/python "$t" >/dev/null 2>&1 && echo "PASS $t" || echo "FAIL $t"; done`
Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
git add src/main.py tests/test_deploy_extract.py
git commit -m "Extract _deploy_to_cpanel from gen_deploy_acc"
```

---

### Task 4: Recovery state, offer, and manual fallback

**Files:**
- Modify: `src/main.py` — add `_pending_slot_recovery` near the other pending dicts (`678` region); add to `/cancel` cleanup (`711–736`); add `_manual_cpanel_removal_msg` + `_offer_free_slot`
- Test: `tests/test_offer_free_slot.py` (create)

**Interfaces:**
- Produces:
  - `_pending_slot_recovery: dict` — `chat_id -> {"account_idx", "domains": list, "retry": dict}`.
  - `_manual_cpanel_removal_msg(chat_id, domain, account, retry_ctx=None) -> None` — sends manual-removal guidance; appends a 🔁 Retry button (`freeslot_retry`) when `retry_ctx` is provided.
  - `_offer_free_slot(chat_id, account_idx, retry_ctx) -> None` — stashes recovery state, lists addon domains as `freeslot_rm:<idx>` buttons; falls back to manual message when the list is empty/unfetchable.

- [ ] **Step 1: Write the failing test**

Create `tests/test_offer_free_slot.py`:

```python
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import main

failures = []

sent = []
main.tg_send = lambda chat_id, text, **kw: sent.append((text, kw))
main.CPANEL_ACCOUNTS = [{"url": "https://cp", "username": "u", "password": "x", "label": "L"}]

# Case A: domains exist -> stash recovery + show buttons.
main._list_addon_domains = lambda account: ["a.com", "b.com", "c.com"]
main._pending_slot_recovery.clear()
sent.clear()
ctx = {"kind": "generate", "domain": "new.com", "zip_path": "/tmp/z.zip", "account_idx": 0}
main._offer_free_slot(555, 0, ctx)

rec = main._pending_slot_recovery.get(555)
if not rec or rec.get("domains") != ["a.com", "b.com", "c.com"]:
    failures.append(f"recovery not stashed with domains: {rec}")
if not rec or rec.get("retry") != ctx:
    failures.append(f"retry ctx not stashed: {rec}")
# A keyboard with freeslot_rm:<idx> buttons was sent.
kbds = [kw.get("reply_markup") for _t, kw in sent if kw.get("reply_markup")]
flat = str(kbds)
if "freeslot_rm:0" not in flat or "freeslot_rm:2" not in flat:
    failures.append(f"missing indexed remove buttons: {flat}")

# Case B: no addon domains -> manual fallback, recovery still stashed (retry works).
main._list_addon_domains = lambda account: []
main._pending_slot_recovery.clear()
sent.clear()
main._offer_free_slot(555, 0, ctx)
flat = " ".join(t for t, _ in sent).lower()
if "manually" not in flat and "cpanel" not in flat:
    failures.append(f"empty list should show manual fallback: {flat}")
if main._pending_slot_recovery.get(555, {}).get("retry") != ctx:
    failures.append("manual fallback must keep retry ctx stashed")

# Case C: list call raises -> manual fallback, no crash.
def boom(account):
    raise main.requests.exceptions.ConnectionError("down")
main._list_addon_domains = boom
main._pending_slot_recovery.clear()
sent.clear()
main._offer_free_slot(555, 0, ctx)
flat = " ".join(t for t, _ in sent).lower()
if "manually" not in flat and "cpanel" not in flat:
    failures.append(f"raising list should show manual fallback: {flat}")

if failures:
    for f in failures:
        print("FAIL:", f)
    sys.exit(1)
print("PASS: _offer_free_slot stashes recovery, shows buttons, falls back to manual")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python tests/test_offer_free_slot.py`
Expected: FAIL — `AttributeError: module 'main' has no attribute '_pending_slot_recovery'` (or `_offer_free_slot`).

- [ ] **Step 3: Add the state dict**

In `src/main.py`, next to `_pending_deploys = {}` and the other pending dicts (around `678`), add:

```python
_pending_slot_recovery = {}  # chat_id -> {account_idx, domains, retry}
```

- [ ] **Step 4: Add `_pending_slot_recovery` to `/cancel` cleanup**

In `src/main.py`, in the `/cancel` block, after the `pending_remove_domain` cleanup (`734–736`), add:

```python
        if chat_id in _pending_slot_recovery:
            del _pending_slot_recovery[chat_id]
            cancelled = True
```

- [ ] **Step 5: Implement `_manual_cpanel_removal_msg` and `_offer_free_slot`**

In `src/main.py`, add both functions immediately above `def _deploy_to_cpanel` (added in Task 3, above `handle_callback`):

```python
def _manual_cpanel_removal_msg(chat_id, domain, account, retry_ctx=None):
    """Tell the user to remove a domain manually in cPanel (auto-removal failed)."""
    markup = None
    if retry_ctx is not None:
        markup = {"inline_keyboard": [[
            {"text": "🔁 Retry deploy", "callback_data": "freeslot_retry"},
        ]]}
    tg_send(chat_id,
            f"⚠️ Couldn't remove `{domain}` automatically (cPanel refused / no access).\n\n"
            f"Remove it manually: log into cPanel → *Domains / Addon Domains* → "
            f"delete `{domain}`.\n"
            f"cPanel: {account['url']}",
            reply_markup=markup)


def _offer_free_slot(chat_id, account_idx, retry_ctx):
    """On the addon cap, offer to remove a domain (buttons) and retry the deploy."""
    account = CPANEL_ACCOUNTS[account_idx]
    tg_send(chat_id,
            "🔴 This hosting account is full — the 50 addon-domain limit has been "
            "reached.\nYou can remove a domain to free a slot, then retry.")
    # Stash retry context first so the Retry button works on every path below.
    _pending_slot_recovery[chat_id] = {
        "account_idx": account_idx, "domains": [], "retry": retry_ctx,
    }
    try:
        domains = _list_addon_domains(account)
    except Exception as e:
        log.error(f"Could not list addon domains: {e}")
        domains = []
    if not domains:
        _manual_cpanel_removal_msg(chat_id, retry_ctx.get("domain", "a domain"),
                                   account, retry_ctx=retry_ctx)
        return
    _pending_slot_recovery[chat_id]["domains"] = domains
    buttons = [[{"text": f"🗑 {d}", "callback_data": f"freeslot_rm:{i}"}]
               for i, d in enumerate(domains)]
    buttons.append([{"text": "❌ Cancel", "callback_data": "freeslot_cancel"}])
    tg_send(chat_id, "Which domain should I remove to free a slot?",
            reply_markup={"inline_keyboard": buttons})
```

- [ ] **Step 6: Run test to verify it passes**

Run: `.venv/bin/python tests/test_offer_free_slot.py`
Expected: `PASS: _offer_free_slot stashes recovery, shows buttons, falls back to manual`

- [ ] **Step 7: Run the full suite**

Run: `for t in tests/test_*.py; do .venv/bin/python "$t" >/dev/null 2>&1 && echo "PASS $t" || echo "FAIL $t"; done`
Expected: all PASS.

- [ ] **Step 8: Commit**

```bash
git add src/main.py tests/test_offer_free_slot.py
git commit -m "Add slot-recovery state, offer, and manual fallback"
```

---

### Task 5: Wire detection → offer in both flows; add `freeslot_*` callbacks

**Files:**
- Modify: `src/main.py` — `_deploy_to_cpanel` create branch; `_start_website_setup` create branch (`1396–1398`); add `freeslot_*` callbacks in `handle_callback`; route `confirm_remove` failure (`2030–2032`) through the manual message
- Test: `tests/test_freeslot_callbacks.py` (create)

**Interfaces:**
- Consumes: `_is_addon_limit_error` (T1), `_offer_free_slot` / `_manual_cpanel_removal_msg` / `_pending_slot_recovery` (T4), `_deploy_to_cpanel` (T3), `_start_website_setup`, `cpanel_remove_domain`.
- Produces callbacks: `freeslot_rm:<idx>`, `freeslot_confirm:<idx>`, `freeslot_cancel`, `freeslot_retry`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_freeslot_callbacks.py`:

```python
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import main

failures = []

sent = []
edits = []
main.tg_send = lambda chat_id, text, **kw: sent.append(text)
main.tg_edit_message = lambda chat_id, mid, text, **kw: edits.append(text)
main.tg_answer_callback = lambda cqid: None
main.CPANEL_ACCOUNTS = [{"url": "https://cp", "username": "u", "password": "x", "label": "L"}]

CB = "cbid"

# --- Retry dispatch: generate kind calls _deploy_to_cpanel with stashed params ---
deploy_calls = []
main._deploy_to_cpanel = lambda chat_id, domain, zip_path, idx: deploy_calls.append((domain, zip_path, idx))
main._pending_slot_recovery.clear()
main._pending_slot_recovery[7] = {"account_idx": 0, "domains": ["a.com"],
    "retry": {"kind": "generate", "domain": "new.com", "zip_path": "/tmp/z.zip", "account_idx": 0}}
main.handle_callback(CB, 7, 1, "freeslot_retry")
if deploy_calls != [("new.com", "/tmp/z.zip", 0)]:
    failures.append(f"generate retry mis-dispatched: {deploy_calls}")
if 7 in main._pending_slot_recovery:
    failures.append("retry must pop recovery state")

# --- Retry dispatch: setup kind calls _start_website_setup ---
setup_calls = []
main._start_website_setup = lambda chat_id, domain, account_idx=None: setup_calls.append((domain, account_idx))
main._pending_slot_recovery.clear()
main._pending_slot_recovery[8] = {"account_idx": 0, "domains": ["a.com"],
    "retry": {"kind": "setup", "domain": "site.com", "account_idx": 0}}
main.handle_callback(CB, 8, 1, "freeslot_retry")
if setup_calls != [("site.com", 0)]:
    failures.append(f"setup retry mis-dispatched: {setup_calls}")

# --- freeslot_confirm success -> removal ok, offers retry ---
main.cpanel_remove_domain = lambda domain, account: {"errors": None}
main._pending_slot_recovery.clear()
main._pending_slot_recovery[9] = {"account_idx": 0, "domains": ["gone.com"],
    "retry": {"kind": "generate", "domain": "n", "zip_path": "/z", "account_idx": 0}}
sent.clear()
main.handle_callback(CB, 9, 1, "freeslot_confirm:0")
if not any("removed" in s.lower() for s in sent):
    failures.append(f"confirm success should report removed: {sent}")

# --- freeslot_confirm failure (errors) -> manual fallback ---
main.cpanel_remove_domain = lambda domain, account: {"errors": ["no access"]}
main._pending_slot_recovery.clear()
main._pending_slot_recovery[10] = {"account_idx": 0, "domains": ["stuck.com"],
    "retry": {"kind": "generate", "domain": "n", "zip_path": "/z", "account_idx": 0}}
sent.clear()
main.handle_callback(CB, 10, 1, "freeslot_confirm:0")
if not any("manually" in s.lower() or "cpanel" in s.lower() for s in sent):
    failures.append(f"confirm failure should show manual fallback: {sent}")

# --- freeslot_confirm exception -> manual fallback, no crash ---
def boom(domain, account):
    raise main.requests.exceptions.ConnectionError("down")
main.cpanel_remove_domain = boom
main._pending_slot_recovery.clear()
main._pending_slot_recovery[11] = {"account_idx": 0, "domains": ["x.com"],
    "retry": {"kind": "generate", "domain": "n", "zip_path": "/z", "account_idx": 0}}
sent.clear()
main.handle_callback(CB, 11, 1, "freeslot_confirm:0")
if not any("manually" in s.lower() or "cpanel" in s.lower() for s in sent):
    failures.append(f"confirm exception should show manual fallback: {sent}")

if failures:
    for f in failures:
        print("FAIL:", f)
    sys.exit(1)
print("PASS: freeslot callbacks dispatch retry + route removal failures to manual")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python tests/test_freeslot_callbacks.py`
Expected: FAIL — the `freeslot_*` callbacks don't exist yet, so `deploy_calls`/`sent` stay empty and assertions fail.

- [ ] **Step 3: Wire `_deploy_to_cpanel` create branch to the offer**

In `src/main.py`, inside `_deploy_to_cpanel` (Task 3), change the cap else-branch:

```python
            else:
                tg_send(chat_id, _friendly_cpanel_error(error_msg))
                return
```

to:

```python
            elif _is_addon_limit_error(error_msg):
                _offer_free_slot(chat_id, account_idx,
                                 {"kind": "generate", "domain": domain,
                                  "zip_path": zip_path, "account_idx": account_idx})
                return
            else:
                tg_send(chat_id, _friendly_cpanel_error(error_msg))
                return
```

- [ ] **Step 4: Wire `_start_website_setup` create branch to the offer**

In `src/main.py`, change the `_start_website_setup` cap branch (`1395–1398`):

```python
            else:
                log.error(f"cPanel domain creation failed: {error_msg}")
                tg_send(chat_id, _friendly_cpanel_error(error_msg))
                return
```

to:

```python
            elif _is_addon_limit_error(error_msg):
                log.error(f"cPanel addon cap hit for {domain}")
                _offer_free_slot(chat_id, account_idx,
                                 {"kind": "setup", "domain": domain,
                                  "account_idx": account_idx})
                return
            else:
                log.error(f"cPanel domain creation failed: {error_msg}")
                tg_send(chat_id, _friendly_cpanel_error(error_msg))
                return
```

> `_start_website_setup` must have a concrete `account_idx` here. It already
> resolves `account_idx` (defaulting to 0) before the create call, so the value
> is in scope.

- [ ] **Step 5: Add the `freeslot_*` callbacks**

In `src/main.py`, add this block inside `handle_callback`, immediately before the existing `if data.startswith("remove_acc:"):` (`2010`):

```python
    if data.startswith("freeslot_rm:"):
        rec = _pending_slot_recovery.get(chat_id)
        if not rec or not rec.get("domains"):
            tg_edit_message(chat_id, message_id, "⚠️ No active recovery.")
            return
        try:
            idx = int(data.split(":", 1)[1])
            domain = rec["domains"][idx]
        except (ValueError, IndexError):
            tg_edit_message(chat_id, message_id, "⚠️ Invalid choice.")
            return
        tg_edit_message(chat_id, message_id, f"🗑 Remove `{domain}`?")
        tg_send(chat_id, f"⚠️ Permanently remove `{domain}` from hosting?",
                reply_markup={"inline_keyboard": [[
                    {"text": "✅ Yes, Remove", "callback_data": f"freeslot_confirm:{idx}"},
                    {"text": "❌ Cancel", "callback_data": "freeslot_cancel"},
                ]]})
        return

    if data.startswith("freeslot_confirm:"):
        rec = _pending_slot_recovery.get(chat_id)
        if not rec or not rec.get("domains"):
            tg_edit_message(chat_id, message_id, "⚠️ No active recovery.")
            return
        try:
            idx = int(data.split(":", 1)[1])
            domain = rec["domains"][idx]
        except (ValueError, IndexError):
            tg_edit_message(chat_id, message_id, "⚠️ Invalid choice.")
            return
        account = CPANEL_ACCOUNTS[rec["account_idx"]]
        retry_ctx = rec.get("retry")
        tg_edit_message(chat_id, message_id, f"⏳ Removing `{domain}`...")
        try:
            result = cpanel_remove_domain(domain, account)
            if result.get("errors"):
                log.error(f"Slot-recovery removal failed: {result.get('errors')}")
                _manual_cpanel_removal_msg(chat_id, domain, account, retry_ctx=retry_ctx)
                return
        except Exception as e:
            log.error(f"Slot-recovery removal error: {e}")
            _manual_cpanel_removal_msg(chat_id, domain, account, retry_ctx=retry_ctx)
            return
        # Success — drop the removed domain from the list, offer retry.
        if domain in rec["domains"]:
            rec["domains"].remove(domain)
        tg_send(chat_id, f"✅ `{domain}` removed.",
                reply_markup={"inline_keyboard": [[
                    {"text": "🔁 Retry deploy", "callback_data": "freeslot_retry"},
                ]]})
        return

    if data == "freeslot_cancel":
        _pending_slot_recovery.pop(chat_id, None)
        tg_edit_message(chat_id, message_id, "🚫 Cancelled.")
        return

    if data == "freeslot_retry":
        rec = _pending_slot_recovery.pop(chat_id, None)
        retry_ctx = rec.get("retry") if rec else None
        if not retry_ctx:
            tg_edit_message(chat_id, message_id, "⚠️ Nothing to retry.")
            return
        tg_edit_message(chat_id, message_id, "🔁 Retrying...")
        if retry_ctx["kind"] == "generate":
            _deploy_to_cpanel(chat_id, retry_ctx["domain"],
                              retry_ctx["zip_path"], retry_ctx["account_idx"])
        elif retry_ctx["kind"] == "setup":
            _start_website_setup(chat_id, retry_ctx["domain"],
                                 account_idx=retry_ctx["account_idx"])
        return
```

- [ ] **Step 6: Route the existing `/remove_domain` failure through the manual message**

In `src/main.py`, in the `confirm_remove` callback, replace the failure branch (`2030–2032`):

```python
            if errors:
                log.error(f"Domain removal failed: {errors}")
                tg_send(chat_id, f"🔴 Failed to remove `{domain}`:\n`{errors}`")
```

with:

```python
            if errors:
                log.error(f"Domain removal failed: {errors}")
                _manual_cpanel_removal_msg(chat_id, domain, account)
```

> No `retry_ctx` here — this is the standalone `/remove_domain` flow, so no Retry
> button (correct).

- [ ] **Step 7: Run test to verify it passes**

Run: `.venv/bin/python tests/test_freeslot_callbacks.py`
Expected: `PASS: freeslot callbacks dispatch retry + route removal failures to manual`

- [ ] **Step 8: Run the full suite + import smoke**

Run: `.venv/bin/python -c "import sys; sys.path.insert(0,'src'); import main; print('import ok')" && for t in tests/test_*.py; do .venv/bin/python "$t" >/dev/null 2>&1 && echo "PASS $t" || echo "FAIL $t"; done`
Expected: `import ok` then all PASS.

- [ ] **Step 9: Commit**

```bash
git add src/main.py tests/test_freeslot_callbacks.py
git commit -m "Wire addon-cap recovery into deploy/setup + freeslot callbacks"
```

---

### Task 6: Manual end-to-end verification

**Files:** none (manual run).

- [ ] **Step 1: Start the bot** — `source .venv/bin/activate && python src/main.py`. Expected: starts, no errors.

- [ ] **Step 2: Trigger the cap** — run `/generate`, finish to the Deploy step, and Deploy to an account at the 50-domain cap. Expected: "account is full" message, then a list of 🗑 domain buttons + Cancel.

- [ ] **Step 3: Free a slot** — tap a domain → "Permanently remove?" → Yes. Expected: "✅ removed" + 🔁 Retry deploy button.

- [ ] **Step 4: Retry** — tap 🔁 Retry deploy. Expected: the same deploy resumes (adds domain, uploads, extracts) and reports the site is live.

- [ ] **Step 5: Manual-fallback path** — repeat to the remove step on a domain cPanel won't remove (or temporarily make `cpanel_remove_domain` return an error). Expected: the manual-cPanel guidance message (with the cPanel URL) and a 🔁 Retry button.

- [ ] **Step 6: `/cancel` clears recovery** — trigger the cap, then send `/cancel`. Expected: "🚫 Cancelled."; tapping an old 🗑 button afterward says "⚠️ No active recovery."

---

## Self-Review

**Spec coverage:**
- Component 1 (detection) → Task 1. ✅
- Component 2 (`_list_addon_domains`, addon-only) → Task 2. ✅
- Component 3 (`_offer_free_slot`, stash-first, manual on empty/raise) → Task 4 + wiring in Task 5. ✅
- Component 4 (freeslot_rm/confirm/cancel/retry callbacks; confirm step; pop-then-dispatch) → Task 5. ✅
- Component 5 (retry dispatch generate/setup) → Task 5 Step 5. ✅
- Component 6 (`_manual_cpanel_removal_msg`, shared with `/remove_domain`, retry button when ctx) → Task 4 (helper) + Task 5 Steps 5–6. ✅
- Component 7 (extract `_deploy_to_cpanel`, pop stays in wrapper) → Task 3. ✅
- Component 8 (state dict + `/cancel` cleanup, no locks) → Task 4 Steps 3–4. ✅
- Testing (detection, offer fallback, retry dispatch, removal-failure routing) → Tasks 1,2,3,4,5 tests + Task 6 manual. ✅

**Placeholder scan:** No TBD/TODO; every code step shows full replacement code with line anchors. ✅

**Type consistency:** `_is_addon_limit_error`, `_list_addon_domains`, `_offer_free_slot`, `_manual_cpanel_removal_msg(…, retry_ctx=None)`, `_deploy_to_cpanel(chat_id, domain, zip_path, account_idx)`, `_pending_slot_recovery` keys (`account_idx`/`domains`/`retry`), and the `retry_ctx` shape (`kind`/`domain`/`zip_path`/`account_idx`) are used identically across tasks and tests. Callback names `freeslot_rm:<idx>` / `freeslot_confirm:<idx>` / `freeslot_cancel` / `freeslot_retry` match between producer (Task 4/5) and tests. ✅

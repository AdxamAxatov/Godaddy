# Concurrent Per-Chat Processing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Telegram bot responsive under concurrent users by routing each Telegram update to a per-chat worker thread, while hard-gating the (now-shelved) browser flows so they leave no cross-thread crash path.

**Architecture:** The main thread becomes a pure dispatcher: it polls Telegram, runs the authorization check, and hands each update to that chat's worker queue. One daemon worker thread per authorized chat processes its updates in order (parallel across chats, sequential within a chat — so the `pending_*` state machines never race). The only genuinely shared state (`APPROVED_USERS` / `_pending_approvals`) is guarded by a single lock. The browser flows (`/buy`, `/email`, `/close`) are gated behind a flag so their cross-thread Playwright path is unreachable.

**Tech Stack:** Python 3.12 stdlib only — `threading`, `queue`. No new dependencies. No test framework: tests are standalone scripts run with `python`, exiting non-zero on failure.

## Global Constraints

- **No new dependencies.** Use stdlib `threading` / `queue` only. `requirements.txt` (`requests==2.32.5`, `playwright==1.58.0`) is unchanged.
- **Do not delete browser code.** `domain_automation.py`, `email_automation.py`, and the `/buy` `/email` `/close` handlers stay intact and reversible.
- **All work happens in `src/main.py`** plus new files under `tests/`.
- **Never close the browser on errors** and **never use `wait_for_load_state("networkidle")`** — unchanged project rules; not touched by this plan.
- **Tests are standalone scripts.** Run with `python tests/<name>.py`; print which assertion failed and `sys.exit(1)` on failure; print `PASS` and exit 0 on success.
- Module `src/main.py` is import-safe (no network at import; `playwright` import is lazy inside functions), so tests may `import main` after adding `src/` to `sys.path`.

---

### Task 1: Hard-gate the browser flows and clean the menus

**Files:**
- Modify: `src/main.py` — add `BROWSER_FLOWS_ENABLED` flag; gate `/close` (`660-669`), `/email` (`713-724`), `/buy` (`766-773`); update `/start` help (`617-627`); update `tg_set_commands()` menu (`2068-2080`).
- Test: `tests/test_browser_gate.py` (create)

**Interfaces:**
- Consumes: nothing (first task).
- Produces: module-level `BROWSER_FLOWS_ENABLED: bool` (default `False`). When `False`, the `/buy`, `/email`, `/close` command handlers early-return without touching `pending_buy` / `pending_email` / `active_browser`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_browser_gate.py`:

```python
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import main

failures = []

# Capture outgoing messages instead of hitting Telegram.
sent = []
main.tg_send = lambda chat_id, text, **kw: sent.append((chat_id, text))

main.BROWSER_FLOWS_ENABLED = False

for cmd in ("/buy", "/email", "/close"):
    sent.clear()
    main.pending_buy.clear()
    main.pending_email.clear()
    main.handle_message(12345, cmd)

    if main.pending_buy.get(12345) is not None:
        failures.append(f"{cmd}: created pending_buy entry while gated")
    if main.pending_email.get(12345) is not None:
        failures.append(f"{cmd}: created pending_email entry while gated")
    if not any("disabled" in text.lower() for _, text in sent):
        failures.append(f"{cmd}: no 'disabled' reply sent (got {sent})")

if failures:
    for f in failures:
        print("FAIL:", f)
    sys.exit(1)
print("PASS: browser commands gated, no pending state created")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python tests/test_browser_gate.py`
Expected: FAIL — either `AttributeError: module 'main' has no attribute 'BROWSER_FLOWS_ENABLED'`, or FAIL lines showing pending state was created / no "disabled" reply.

- [ ] **Step 3: Add the flag**

In `src/main.py`, immediately after the user-approval block (after line 193, the end of `is_authorized`), add:

```python
# ── Browser flows (/buy, /email, /close) are shelved. Set True to re-enable. ──
# NOTE: re-enabling requires revisiting active_browser locking + single-owner
# browser lifecycle (see docs/superpowers/specs/2026-06-19-...-design.md),
# because GoDaddyEmailBot's sync-Playwright objects are thread-affine.
BROWSER_FLOWS_ENABLED = False
```

- [ ] **Step 4: Gate the `/close` handler**

In `src/main.py`, replace the `/close` handler (lines 660-669):

```python
    # Command: /close — close the browser
    if text == "/close":
        bot = active_browser.pop(chat_id, None)
        if bot:
            bot.close()
            tg_send(chat_id, "🔒 Browser closed.")
            log.info("Browser closed via /close command")
        else:
            tg_send(chat_id, "No browser is open.")
        return
```

with:

```python
    # Command: /close — close the browser
    if text == "/close":
        if not BROWSER_FLOWS_ENABLED:
            tg_send(chat_id, "⚠️ This command is temporarily disabled.")
            return
        bot = active_browser.pop(chat_id, None)
        if bot:
            bot.close()
            tg_send(chat_id, "🔒 Browser closed.")
            log.info("Browser closed via /close command")
        else:
            tg_send(chat_id, "No browser is open.")
        return
```

- [ ] **Step 5: Gate the `/email` handler**

In `src/main.py`, insert the gate as the first lines inside the `/email` handler. Change (lines 713-715):

```python
    # Command: /email — create email account
    if text == "/email" or text.startswith("/email "):
        domain = text.split(" ", 1)[1].strip() if " " in text else ""
```

to:

```python
    # Command: /email — create email account
    if text == "/email" or text.startswith("/email "):
        if not BROWSER_FLOWS_ENABLED:
            tg_send(chat_id, "⚠️ This command is temporarily disabled.")
            return
        domain = text.split(" ", 1)[1].strip() if " " in text else ""
```

- [ ] **Step 6: Gate the `/buy` handler**

In `src/main.py`, insert the gate as the first lines inside the `/buy` handler. Change (lines 766-768):

```python
    # Command: /buy — purchase a domain
    if text == "/buy" or text.startswith("/buy "):
        pending_buy[chat_id] = {"step": "awaiting_company"}
```

to:

```python
    # Command: /buy — purchase a domain
    if text == "/buy" or text.startswith("/buy "):
        if not BROWSER_FLOWS_ENABLED:
            tg_send(chat_id, "⚠️ This command is temporarily disabled.")
            return
        pending_buy[chat_id] = {"step": "awaiting_company"}
```

- [ ] **Step 7: Update the `/start` help text**

In `src/main.py`, replace the `/start` body (lines 617-627) so it no longer advertises the gated commands:

```python
    if text == "/start":
        tg_send(chat_id,
                "👋 *GoDaddy Domain Bot*\n\n"
                "What I can do:\n"
                "• /setup — deploy a website\n"
                "• /generate — generate website + job description\n"
                "• /run\\_autossl — run AutoSSL for a domain\n"
                "• /remove\\_domain — remove a domain from hosting")
        return
```

- [ ] **Step 8: Remove gated commands from the Telegram menu**

In `src/main.py`, in `tg_set_commands()` replace the `commands` list (lines 2068-2080) with one that drops `buy`, `email`, and `close`:

```python
    commands = [
        {"command": "start", "description": "Show welcome message"},
        {"command": "setup", "description": "Deploy website to hosting"},
        {"command": "generate", "description": "Generate website + job description"},
        {"command": "run_autossl", "description": "Run AutoSSL for a domain"},
        {"command": "remove_domain", "description": "Remove a domain from hosting"},
        {"command": "cancel", "description": "Cancel current operation"},
        {"command": "users", "description": "List approved users (admin)"},
        {"command": "revoke", "description": "Revoke user access (admin)"},
    ]
```

- [ ] **Step 9: Run test to verify it passes**

Run: `python tests/test_browser_gate.py`
Expected: `PASS: browser commands gated, no pending state created` and exit 0.

- [ ] **Step 10: Commit**

```bash
git add src/main.py tests/test_browser_gate.py
git commit -m "Hard-gate browser flows behind BROWSER_FLOWS_ENABLED"
```

---

### Task 2: Guard the shared auth state with a lock

**Files:**
- Modify: `src/main.py` — add `import threading` (top, near line 22); add `_auth_lock` (near line 168); wrap `is_authorized` (`191-193`), `/users` snapshot (`676-687`), `/revoke` mutation (`703-711`), approve callback (`1708-1716`), deny callback (`1718-1724`).
- Test: `tests/test_auth_lock.py` (create)

**Interfaces:**
- Consumes: nothing structural (mechanical hardening).
- Produces: module-level `_auth_lock: threading.Lock`. All reads/writes of `APPROVED_USERS` and `_pending_approvals` happen under it. `is_authorized(chat_id) -> bool` keeps its signature.

- [ ] **Step 1: Write the failing test**

Create `tests/test_auth_lock.py`:

```python
import os
import sys
import threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import main

failures = []

# _auth_lock must exist and be a lock.
if not hasattr(main, "_auth_lock"):
    print("FAIL: main._auth_lock missing")
    sys.exit(1)

# Hammer is_authorized while another thread mutates APPROVED_USERS.
# Without locking around the /users-style snapshot + mutation this can raise.
stop = threading.Event()
errors = []

def reader():
    while not stop.is_set():
        try:
            main.is_authorized(555)
            with main._auth_lock:
                snapshot = sorted(main.APPROVED_USERS.items())
            for uid, _info in snapshot:
                _ = main.APPROVED_USERS.get(uid)
        except Exception as e:  # noqa: BLE001
            errors.append(repr(e))

def writer():
    for i in range(2000):
        with main._auth_lock:
            main.APPROVED_USERS[str(1000 + (i % 50))] = {"name": "x", "username": ""}
            if (i % 50) in main.APPROVED_USERS:
                main.APPROVED_USERS.pop(str(1000 + (i % 50)), None)

threads = [threading.Thread(target=reader) for _ in range(3)]
w = threading.Thread(target=writer)
for t in threads:
    t.start()
w.start()
w.join()
stop.set()
for t in threads:
    t.join()

if errors:
    print("FAIL: concurrent auth access raised:", errors[:3])
    failures.append("races")

if failures:
    sys.exit(1)
print("PASS: auth state access is lock-guarded with no races")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python tests/test_auth_lock.py`
Expected: FAIL — `FAIL: main._auth_lock missing` (the attribute does not exist yet).

- [ ] **Step 3: Add the threading import**

In `src/main.py`, the import block ends around line 26 (`from urllib.parse import quote`). Add after the `import random` line (line 23):

```python
import threading
import queue
```

(`queue` is added now so Task 3 needs no further import change.)

- [ ] **Step 4: Add the lock**

In `src/main.py`, just below `_pending_approvals = {}` (line 168) add:

```python
_auth_lock = threading.Lock()  # guards APPROVED_USERS and _pending_approvals (cross-thread)
```

- [ ] **Step 5: Lock `is_authorized`**

Replace (lines 191-193):

```python
def is_authorized(chat_id) -> bool:
    """Check if a user is approved."""
    return str(chat_id) in APPROVED_USERS
```

with:

```python
def is_authorized(chat_id) -> bool:
    """Check if a user is approved."""
    with _auth_lock:
        return str(chat_id) in APPROVED_USERS
```

- [ ] **Step 6: Lock the `/users` snapshot**

Replace the `/users` listing (lines 676-687):

```python
        if not APPROVED_USERS:
            tg_send(chat_id, "No approved users.")
        else:
            lines = ["👥 *Approved Users*\n"]
            for uid in sorted(APPROVED_USERS):
                info = APPROVED_USERS[uid]
                name = info.get("name", "Unknown")
                username = info.get("username", "")
                role = "👑 Admin" if uid == ADMIN_CHAT_ID else "👤 User"
                display = f"@{username}" if username else name
                lines.append(f"{role}: {display} (`{uid}`)")
            tg_send(chat_id, "\n".join(lines))
        return
```

with (snapshot `items()` once under the lock — avoids the `KeyError` at the old `APPROVED_USERS[uid]` if `/revoke` deletes a key mid-loop):

```python
        with _auth_lock:
            snapshot = sorted(APPROVED_USERS.items())
        if not snapshot:
            tg_send(chat_id, "No approved users.")
        else:
            lines = ["👥 *Approved Users*\n"]
            for uid, info in snapshot:
                name = info.get("name", "Unknown")
                username = info.get("username", "")
                role = "👑 Admin" if uid == ADMIN_CHAT_ID else "👤 User"
                display = f"@{username}" if username else name
                lines.append(f"{role}: {display} (`{uid}`)")
            tg_send(chat_id, "\n".join(lines))
        return
```

- [ ] **Step 7: Lock the `/revoke` mutation**

Replace the revoke body (lines 703-711):

```python
        if target_id in APPROVED_USERS:
            del APPROVED_USERS[target_id]
            _save_approved_users(APPROVED_USERS)
            tg_send(chat_id, f"✅ Revoked access for `{target_id}`.")
        else:
            tg_send(chat_id, f"User `{target_id}` is not in the approved list.")
        return
```

with:

```python
        with _auth_lock:
            existed = target_id in APPROVED_USERS
            if existed:
                del APPROVED_USERS[target_id]
                _save_approved_users(APPROVED_USERS)
        if existed:
            tg_send(chat_id, f"✅ Revoked access for `{target_id}`.")
        else:
            tg_send(chat_id, f"User `{target_id}` is not in the approved list.")
        return
```

> If the exact wording on lines 705/710 differs from above, keep the existing message strings — only wrap the `del` + `_save_approved_users` + membership check in `with _auth_lock:` as shown.

- [ ] **Step 8: Lock the approve callback**

Replace (lines 1708-1716):

```python
    if data.startswith("approve:"):
        target_id = data.split(":", 1)[1]
        user_info = _pending_approvals.pop(target_id, {"name": "Unknown", "username": ""})
        APPROVED_USERS[target_id] = user_info
        _save_approved_users(APPROVED_USERS)
        tg_edit_message(chat_id, message_id, f"✅ User `{target_id}` approved.")
        tg_send(int(target_id), "✅ Your access has been approved! Send /start to begin.")
        log.info(f"User {target_id} approved by admin")
        return
```

with:

```python
    if data.startswith("approve:"):
        target_id = data.split(":", 1)[1]
        with _auth_lock:
            user_info = _pending_approvals.pop(target_id, {"name": "Unknown", "username": ""})
            APPROVED_USERS[target_id] = user_info
            _save_approved_users(APPROVED_USERS)
        tg_edit_message(chat_id, message_id, f"✅ User `{target_id}` approved.")
        tg_send(int(target_id), "✅ Your access has been approved! Send /start to begin.")
        log.info(f"User {target_id} approved by admin")
        return
```

- [ ] **Step 9: Lock the deny callback**

Replace (lines 1718-1724):

```python
    if data.startswith("deny:"):
        target_id = data.split(":", 1)[1]
        _pending_approvals.pop(target_id, None)
        tg_edit_message(chat_id, message_id, f"❌ User `{target_id}` denied.")
        tg_send(int(target_id), "❌ Your access request has been denied.")
        log.info(f"User {target_id} denied by admin")
        return
```

with:

```python
    if data.startswith("deny:"):
        target_id = data.split(":", 1)[1]
        with _auth_lock:
            _pending_approvals.pop(target_id, None)
        tg_edit_message(chat_id, message_id, f"❌ User `{target_id}` denied.")
        tg_send(int(target_id), "❌ Your access request has been denied.")
        log.info(f"User {target_id} denied by admin")
        return
```

- [ ] **Step 10: Run test to verify it passes**

Run: `python tests/test_auth_lock.py`
Expected: `PASS: auth state access is lock-guarded with no races` and exit 0.

- [ ] **Step 11: Commit**

```bash
git add src/main.py tests/test_auth_lock.py
git commit -m "Guard shared auth state with _auth_lock"
```

---

### Task 3: Dispatcher + per-chat worker threads

**Files:**
- Modify: `src/main.py` — add the worker registry + `dispatch` + `process_update` + `_handle_unapproved` (place just above `def run()` at line 2089); rewrite the `run()` polling loop body (lines 2118-2184).
- Test: `tests/test_concurrency.py` (create)

**Interfaces:**
- Consumes: `is_authorized` and `_auth_lock` (Task 2); `handle_message`, `handle_callback`, `handle_document`, `tg_send`, `_get_user_display`, `ADMIN_CHAT_ID` (existing).
- Produces:
  - `process_update(update: dict) -> None` — routes an already-authorized update to the right handler (message/document/callback). No auth checks inside.
  - `dispatch(update: dict) -> None` — main-thread entry: authorizes, then enqueues to the chat's worker (or handles unapproved inline).
  - `_chat_workers: dict[int, ChatWorker]`, `_workers_lock: threading.Lock`, `_get_worker(chat_id) -> ChatWorker`.
  - `class ChatWorker` with `submit(update)` and an internal daemon thread that calls `process_update`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_concurrency.py`:

```python
import os
import sys
import time
import threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import main

failures = []

# Authorize both test chats.
with main._auth_lock:
    main.APPROVED_USERS["100"] = {"name": "A", "username": ""}
    main.APPROVED_USERS["200"] = {"name": "B", "username": ""}

# Replace the handler with a recorder that simulates work.
records = []
rec_lock = threading.Lock()

def fake_process(update):
    chat = update["message"]["chat"]["id"]
    seq = update["message"]["seq"]
    time.sleep(0.05)
    with rec_lock:
        records.append((chat, seq))

main.process_update = fake_process

# Interleave: (100,0)(200,0)(100,1)(200,1)(100,2)(200,2)
uid = 1
for i in range(3):
    for chat in (100, 200):
        main.dispatch({"update_id": uid,
                       "message": {"chat": {"id": chat}, "seq": i, "text": "x"}})
        uid += 1

# Wait for both workers to drain (serial worst case ~0.3s; allow margin).
time.sleep(1.5)

def order_for(chat):
    return [seq for c, seq in records if c == chat]

for chat in (100, 200):
    seqs = order_for(chat)
    if seqs != sorted(seqs):
        print(f"FAIL: chat {chat} processed out of order: {seqs}")
        failures.append("ordering")
    if len(seqs) != 3:
        print(f"FAIL: chat {chat} processed {len(seqs)}/3 updates: {seqs}")
        failures.append("dropped")

chat_seq = [c for c, _ in records]
switches = sum(1 for i in range(1, len(chat_seq)) if chat_seq[i] != chat_seq[i - 1])
if switches < 2:
    print(f"FAIL: chats did not interleave (switches={switches}): {chat_seq}")
    failures.append("no-parallelism")

if failures:
    sys.exit(1)
print("PASS: per-chat order preserved and chats ran in parallel")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python tests/test_concurrency.py`
Expected: FAIL — `AttributeError: module 'main' has no attribute 'dispatch'`.

- [ ] **Step 3: Add the worker registry, dispatcher, and process_update**

In `src/main.py`, immediately **above** `def run():` (line 2089), add:

```python
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CONCURRENCY: dispatcher + per-chat worker threads
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_chat_workers = {}            # chat_id -> ChatWorker
_workers_lock = threading.Lock()


class ChatWorker:
    """One daemon thread + queue per chat. Processes that chat's updates in order."""

    def __init__(self, chat_id):
        self.chat_id = chat_id
        self.queue = queue.Queue()
        self.thread = threading.Thread(
            target=self._run, name=f"chat-{chat_id}", daemon=True
        )
        self.thread.start()

    def submit(self, update):
        self.queue.put(update)

    def _run(self):
        while True:
            update = self.queue.get()
            try:
                process_update(update)
            except Exception:
                log.exception(f"Worker error processing update for chat {self.chat_id}")
                try:
                    tg_send(self.chat_id, "⚠️ Something went wrong, please try again.")
                except Exception:
                    pass


def _get_worker(chat_id):
    """Get (or lazily create) the worker for a chat."""
    with _workers_lock:
        worker = _chat_workers.get(chat_id)
        if worker is None:
            worker = ChatWorker(chat_id)
            _chat_workers[chat_id] = worker
        return worker


def _handle_unapproved(chat_id, msg):
    """Main-thread access-request flow for an unapproved user (deduped, runs once)."""
    str_id = str(chat_id)
    with _auth_lock:
        already = str_id in _pending_approvals
        if not already:
            user = msg.get("from", {})
            _pending_approvals[str_id] = {
                "name": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or "Unknown",
                "username": user.get("username", ""),
            }
    if already:
        return
    display = _get_user_display(msg)
    tg_send(chat_id, "🔒 You don't have access to this bot.\nA request has been sent to the admin.")
    tg_send(int(ADMIN_CHAT_ID),
            f"🔔 *Access Request*\n\n"
            f"User: {display}\n"
            f"ID: `{chat_id}`",
            reply_markup={"inline_keyboard": [[
                {"text": "✅ Approve", "callback_data": f"approve:{chat_id}"},
                {"text": "❌ Deny", "callback_data": f"deny:{chat_id}"},
            ]]})
    log.info(f"[{chat_id}] Access requested by {display}")


def process_update(update):
    """Route an already-authorized update to the right handler (runs on a worker)."""
    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        if "document" in msg:
            handle_document(chat_id, msg["document"], msg)
            return
        text = msg.get("text", "")
        if text:
            handle_message(chat_id, text, msg.get("message_id"))
    elif "callback_query" in update:
        cb = update["callback_query"]
        chat_id = cb["message"]["chat"]["id"]
        data = cb.get("data", "")
        handle_callback(cb["id"], chat_id, cb["message"]["message_id"], data)


def dispatch(update):
    """Main-thread routing: authorize, then enqueue to the chat's worker."""
    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        if not is_authorized(chat_id):
            _handle_unapproved(chat_id, msg)
            return
        _get_worker(chat_id).submit(update)

    elif "callback_query" in update:
        cb = update["callback_query"]
        chat_id = cb["message"]["chat"]["id"]
        data = cb.get("data", "")
        # Admin approve/deny: only the admin may trigger; handled on a worker.
        if data.startswith("approve:") or data.startswith("deny:"):
            if str(chat_id) == ADMIN_CHAT_ID:
                _get_worker(chat_id).submit(update)
            return
        if not is_authorized(chat_id):
            return
        _get_worker(chat_id).submit(update)
```

- [ ] **Step 4: Rewrite the `run()` polling loop**

In `src/main.py`, replace the entire `while True:` block in `run()` (lines 2118-2184) with the dispatcher-only version:

```python
    while True:
        try:
            updates = tg_get_updates(offset)
        except KeyboardInterrupt:
            raise
        except Exception as e:
            log.warning(f"Polling error: {e}")
            time.sleep(5)
            continue

        for update in updates:
            offset = update["update_id"] + 1
            try:
                dispatch(update)
            except Exception:
                log.exception("Dispatch error")
```

(Everything in `run()` above the loop — the banner prints, stale-update flush, and `tg_set_commands()` — stays unchanged.)

- [ ] **Step 5: Run test to verify it passes**

Run: `python tests/test_concurrency.py`
Expected: `PASS: per-chat order preserved and chats ran in parallel` and exit 0.

- [ ] **Step 6: Run the full test suite (no regressions)**

Run: `python tests/test_browser_gate.py && python tests/test_auth_lock.py && python tests/test_concurrency.py`
Expected: three `PASS` lines, exit 0.

- [ ] **Step 7: Smoke-check the module imports and compiles**

Run: `python -c "import sys; sys.path.insert(0,'src'); import main; print('import ok')"`
Expected: `import ok` (no exceptions).

- [ ] **Step 8: Commit**

```bash
git add src/main.py tests/test_concurrency.py
git commit -m "Add dispatcher + per-chat worker threads for concurrent processing"
```

---

### Task 4: Manual two-user verification

**Files:** none (manual run).

**Interfaces:** Consumes the finished bot. Produces a human-confirmed responsiveness check.

- [ ] **Step 1: Start the bot**

Run: `source .venv/Scripts/activate && python src/main.py`
Expected: startup banner, `Bot commands registered with Telegram`, no `buy`/`email`/`close` in the Telegram command menu.

- [ ] **Step 2: Confirm gated commands**

From a Telegram client, send `/buy`, `/email`, `/close`.
Expected: each replies `⚠️ This command is temporarily disabled.` and the bot logs no Playwright activity.

- [ ] **Step 3: Confirm concurrent responsiveness**

From chat A, start a slow flow (`/setup`, then begin a real zip upload / a long-running cPanel step). While that is mid-flight, from chat B (a different approved account) send `/start`.
Expected: chat B receives the welcome message **immediately**, without waiting for chat A's flow to finish. Chat A's flow continues normally.

- [ ] **Step 4: Stop the bot**

Press `Ctrl+C`.
Expected: `Bot stopped.` — clean exit (daemon workers die with the process).

---

## Self-Review

**Spec coverage:**
- Component 1 (dispatcher loop) → Task 3 Step 4. ✅
- Component 2 (auth gate on dispatcher, message + callback; deduped unapproved send on main thread) → Task 3 Step 3 (`dispatch`, `_handle_unapproved`). ✅
- Component 3 (per-chat worker registry, in-order, parallel) → Task 3 Step 3 (`ChatWorker`, `_get_worker`) + `tests/test_concurrency.py`. ✅
- Component 4 (`process_update` extraction) → Task 3 Step 3. ✅
- Component 5 (locking: `_auth_lock` over `APPROVED_USERS` incl. `/users` snapshot, `_pending_approvals`, `_save`; `active_browser` left unlocked because gated) → Task 2 + Task 1. ✅
- Component 6 (hard-gate `/buy` `/email` `/close`, flag, menu) → Task 1. ✅
- Component 7 (worker-level try/except logs + notifies) → Task 3 Step 3 (`ChatWorker._run`). ✅
- Testing (standalone interleaving test on real registry; manual two-user) → `tests/test_concurrency.py` + Task 4. ✅

**Placeholder scan:** No TBD/TODO; every code step shows full replacement code with exact line anchors. ✅

**Type consistency:** `dispatch`/`process_update`/`_get_worker`/`ChatWorker.submit` names are used identically in the test, the Interfaces blocks, and the implementation. `_auth_lock` and `BROWSER_FLOWS_ENABLED` names match across Tasks 1–3. ✅

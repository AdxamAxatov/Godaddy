# Design: Concurrent Per-Chat Processing for the Telegram Bot

**Date:** 2026-06-19
**Status:** Approved (pending spec review)
**Topic:** Make the bot responsive and concurrent so multiple users can interact at once without one user's work freezing everyone.

## Problem

The bot (`src/main.py`) runs a single synchronous loop in `run()` (`main.py:2118`):

```
while True:
    updates = tg_get_updates(offset)   # long-poll, ~5s
    for update in updates:
        handle_message(...)            # runs to completion, inline
```

Every update is processed inline to completion before the next is looked at. The
heavy browser flows (`/buy`, `/email`) drive real Chrome via Playwright's **sync
API** and can take minutes. During that time the loop cannot poll Telegram, so all
other users get total silence — even their own `/cancel` is not seen.

Goal: the bot must never freeze for everyone while one job runs, and independent
users must be able to run flows in parallel.

## Scope

- **In scope:** concurrency for the flows actually used — `/setup`, `/generate`,
  `/run_autossl`, `/remove_domain` — plus the admin/auth and `/cancel`/`/start`
  paths. These are cPanel HTTP calls (`requests`) and local HTML generation:
  I/O-bound and CPU-light, well suited to threads.
- **Browser flows (`/buy`, `/email`, `/close`):** being shelved. They are
  hard-gated off (see Component 5). Code stays intact and reversible.
- **Out of scope:** asyncio rewrite; deleting browser automation; multi-user
  contention queues for shared GoDaddy accounts (moot once browser flows are gated).

## Constraints (verified against code)

1. Playwright's **sync API objects are thread-affine** — bound to the thread that
   created them. Today all browsers are created/closed on the single main thread,
   so this is safe. Per-chat threading would break it (see Component 5).
2. `active_browser` is **cross-thread shared state**: the `/email` flow at
   `main.py:1536–1544` reaches into *other* chats' browsers and calls
   `other_bot.close()` to release the shared profile lock. Under per-chat workers
   this becomes worker A closing worker B's Playwright object — a greenlet
   "cannot switch thread" crash, not just a dict race. The hard-gate makes this
   path unreachable rather than locking it.
3. `pending_*` state dicts are each keyed by `chat_id` and only read/written on
   that chat's turn → safe under per-chat serialization, no locks needed.
4. `APPROVED_USERS` / `_pending_approvals` are touched by multiple chats (admin
   approves/revokes another chat's access) → genuinely shared, needs a lock.

## Chosen Approach: Per-Chat Worker Threads (Option A)

Rejected alternatives:
- **Thread-per-update** — breaks per-chat ordering; rapid same-chat messages can
  process step 2 before step 1 and corrupt `pending_*` state.
- **Full asyncio rewrite** — large/risky for a few-user bot; would require
  rewriting every `requests` call, and is incompatible with the sync-Playwright
  code if browser flows are ever revived.

## Components

### 1. Main loop becomes a pure dispatcher
`run()` keeps a single thread owning Telegram polling and the `offset` cursor
(unchanged: startup stale-flush, `tg_set_commands()`, `while True:
tg_get_updates(offset)`). For each update it:
1. Extracts `chat_id`.
2. Runs the **auth gate** (see Component 2) — on the main thread.
3. For authorized chats, hands the raw update to that chat's worker queue and
   immediately loops back to polling.

The dispatcher does no *unbounded* slow work → the bot stays responsive. **One
accepted exception:** the unapproved-user access-request path (moved to the main
thread, see Component 2) makes two blocking `tg_send` calls (`main.py:2145` to the
user, `2146` to the admin). This is acceptable because `_pending_approvals`
dedupes — each stranger triggers it exactly once, then is silent. Deliberately
*not* pushed to a worker, as that would resurrect the per-stranger thread
Component 2 exists to avoid.

### 2. Auth gate on the dispatcher (main thread)
The authorization checks run in the dispatcher **before any worker is created**,
spanning **both** update kinds:
- **Message path** — `is_authorized()` + the unapproved-user access-request flow
  (currently `main.py:2136–2155`).
- **Callback path** — the callback authorization gate (`main.py:2177–2178`,
  `if not is_authorized(chat_id): continue`) and the admin-only approve/deny
  special-case (`2172–2175`). Without this, an unauthorized user firing callback
  queries at an old inline keyboard would still reach a worker before being
  dropped, defeating the bound below.

Consequences:
- Unapproved/spam traffic (messages *and* callbacks) never allocates a thread or
  queue.
- Workers are created lazily only for authorized chats (and admin approve/deny,
  which is admin-authorized) → thread count bounded by real users.
- The `_pending_approvals` insert stays on the main thread, shrinking lock scope.

The approve/deny *handling* itself still lives in `process_update` /
`handle_callback` under `_auth_lock` (Component 5) — only the
authorized-or-not routing decision moves to the dispatcher.

### 3. Per-chat worker registry
Module-level `_chat_workers: {chat_id -> ChatWorker}`, guarded by
`_workers_lock` (a `threading.Lock`) for the get-or-create. Each `ChatWorker`:
- a `queue.Queue` of pending updates,
- one daemon `threading.Thread` that loops: `update = queue.get()` →
  `process_update(update)` → repeat.

Result: **parallel across chats** (separate threads), **sequential within a chat**
(single queue), so `pending_*` state machines never reorder or race. No reaping
logic (YAGNI at this scale; daemon threads die with the process).

### 4. Extract `process_update(update)`
The body currently inside `for update in updates:` in `run()`
(`main.py:2128–2184`) — minus the auth gate, which moves to the dispatcher — is
lifted **verbatim** into a new `process_update(update)` function: document /
message / callback routing and the approve/deny callback path. Handler logic
itself is untouched. Workers call `process_update`.

### 5. Locking — genuinely shared state only
- `pending_*` dicts: **no locks** (per-chat serialization owns them).
- `_auth_lock` (`threading.Lock`) wraps **all** access to the auth set:
  - `APPROVED_USERS` mutations: approve/deny callback (`main.py:1703–1720`),
    revoke (`703–705`).
  - `APPROVED_USERS` **reads** that can race a mutation: `is_authorized()`
    (`191`) and the `/users` snapshot+access (`680–681`). Note: `sorted(...)`
    takes a list snapshot, so the failure mode at `681` is a `KeyError` on
    `APPROVED_USERS[uid]` after a concurrent `/revoke`, not a `RuntimeError` —
    the lock prevents it either way.
  - `_pending_approvals` mutations and `_save_approved_users()`.
- `active_browser`: **left unlocked, and that is safe specifically because** the
  hard-gate (Component 6) makes the cross-thread path at `1536–1544` unreachable.
  This is documented so a future reader knows re-enabling browser flows requires
  revisiting locking + single-owner browser lifecycle.

### 6. Hard-gate the browser flows
- Module-level flag `BROWSER_FLOWS_ENABLED = False`.
- The `/buy`, `/email`, and `/close` command handlers early-return with
  "⚠️ This command is temporarily disabled." when the flag is off — before
  touching any `pending_buy` / `pending_email` / `active_browser` state.
- Remove `buy`, `email`, `close` from the `commands` list in `tg_set_commands()`
  (`main.py:2068`).
- All browser code (handlers, `domain_automation.py`, `email_automation.py`,
  playwright dependency) stays intact. Reversible by flipping the flag and
  re-adding the three menu entries.

### 7. Error handling
The worker loop wraps each `process_update` in `try/except`: log the full
traceback to `automation.log` and send the user a brief "⚠️ Something went wrong,
please try again." So one handler crash logs and notifies instead of silently
killing that chat's worker thread. Per-call Telegram send failures stay handled
as today. `Ctrl+C` stops the main thread; daemon workers exit with the process.

## Testing

No test framework exists in the repo. Verification:

1. **Standalone interleaving test** — `tests/test_concurrency.py`, run directly
   with `python tests/test_concurrency.py` (no framework). It:
   - pushes interleaved fake updates from two `chat_id`s through the **real**
     dispatch-to-worker routing + `_chat_workers` registry (not a stub),
   - monkeypatches the per-update handler to record `(chat_id, seq)` with a small
     sleep, so ordering and interleaving are observable,
   - asserts per-chat order is preserved AND the two chats' work interleaves
     (proving parallelism + ordering). On failure it prints which assertion failed
     and exits non-zero (no framework to format results).
2. **Manual two-user check** — start a slow flow (`/setup` mid zip-upload) in
   chat A; confirm `/start` in chat B replies immediately.

## Files Touched

- `src/main.py` — dispatcher refactor, `process_update` extraction, worker
  registry, `_auth_lock`, `BROWSER_FLOWS_ENABLED` gate, `tg_set_commands` menu.
- New: `tests/test_concurrency.py` — standalone interleaving/ordering test.
- `requirements.txt` / `domain_automation.py` / `email_automation.py` — **unchanged**.

## Risks & Mitigations

- **Hidden cross-thread state beyond `active_browser`** — mitigated by the
  verified inventory above; only `active_browser` and the auth set are shared, and
  both are addressed.
- **Re-enabling browser flows later** — the spec documents that doing so requires
  revisiting `active_browser` locking and single-owner browser lifecycle before
  flipping `BROWSER_FLOWS_ENABLED`.
- **Worker thread leak** — bounded by authorized users only (auth gate on
  dispatcher); no reaping needed at this scale.

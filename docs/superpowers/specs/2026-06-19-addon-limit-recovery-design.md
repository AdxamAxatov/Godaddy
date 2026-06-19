# Design: "Account full → free a slot → retry" recovery

**Date:** 2026-06-19
**Status:** Approved (pending spec review)
**Topic:** When a cPanel deploy hits the 50 addon-domain cap, don't dead-end the user — let them remove a domain to free a slot and retry the deploy, with a manual-cPanel fallback when automatic removal isn't possible.

## Problem

`/generate` (Deploy button) and `/setup` both create cPanel addon domains. When
the hosting account is at the 50 addon-domain limit, `cpanel_create_domain`
returns an error and the flow stops with a message. The user is dead-ended: to
proceed they must separately run `/remove_domain`, remember which domain to
remove, then re-run the whole generate/setup flow. Additionally, automatic
removal sometimes fails ("no access to remove subdomain"), leaving the user with
a raw error and no guidance.

## Goals

1. On the addon-domain cap, offer (optionally) to free a slot by removing one of
   the account's existing addon domains, picked from a list.
2. After a successful removal, offer to retry the exact deploy that failed —
   no re-running `/generate` or `/setup` from scratch.
3. When automatic removal isn't possible (cPanel refuses / no access), direct the
   user to remove the domain manually in cPanel — and still let them retry.
4. Apply the manual-removal guidance to the existing `/remove_domain` flow too,
   since it has the same failure point.

## Scope

- **In scope:** both domain-creating flows — `/generate` Deploy and `/setup` —
  plus the shared manual-fallback improvement to `/remove_domain`.
- **Out of scope:** pagination of the addon-domain button list (50 buttons is
  acceptable; YAGNI); changing the pre-existing `confirm_remove:<acc>:<domain>`
  callback shape (not this feature's job).

## Constraints (verified against code)

- `_friendly_cpanel_error` (`main.py:460`) already contains the cap-detection
  logic to extract: `"addon" in low and ("maximum"|"limit"|"reached"|"exceed")`.
- Both create-domain failure branches call `_friendly_cpanel_error(error_msg)`
  then `return`: `_start_website_setup:1397` and the deploy callback
  `gen_deploy_acc:2178`.
- **Zip survives a limit failure:** the deploy callback returns at `2179`, before
  the upload step's `finally: os.remove(zip_path)` (`2196–2200`) and the
  server-side delete. So `zip_path` still exists locally for retry.
- `cpanel_remove_domain(domain, account)` (`569`) fails two ways: returns
  `{"errors": [...]}` (e.g. "not found as addon domain", `591`; or a
  `deladdondomain` refusal `reason`, `612–614`) **or** raises (via
  `raise_for_status`). Both must route to the manual fallback.
- The addon-domain list parse lives inline in `_start_remove_domain:1481–1486`
  (`DomainInfo/list_domains` → `data["addon_domains"]`).
- Telegram callback_data has a 64-byte limit → select domains by **index**, not
  raw domain string.
- Per-chat `pending_*` dicts are touched only by that chat's worker → no locking
  needed; new state follows the same convention.

## Components

### 1. Detection — `_is_addon_limit_error(error_msg) -> bool`
Extract the cap predicate from `_friendly_cpanel_error`, which then calls it.
In both create-domain failure branches, when `_is_addon_limit_error(error_msg)`
is true, call `_offer_free_slot(...)` instead of sending the friendly text. All
other cPanel errors keep the current `_friendly_cpanel_error` message + `return`.

### 2. Shared helper — `_list_addon_domains(account) -> list[str]`
Extract the `DomainInfo/list_domains` call + parse from
`_start_remove_domain:1481–1486` into one reusable function returning **only**
`data["addon_domains"]` (never the main/parked union — the primary domain must
never appear as a removable slot). Raises on HTTP failure (caller handles).
`_start_remove_domain` is refactored to use it for its existence check (it keeps
its own main+parked+addon union locally for validation; the helper returns just
addon).

### 3. Offer — `_offer_free_slot(chat_id, account_idx, retry_ctx)`
1. Send the "this hosting account is full" message.
2. Stash `_pending_slot_recovery[chat_id] = {"account_idx": account_idx,
   "domains": [], "retry": retry_ctx}` first, so the Retry button works on
   every path below (it reads `_pending_slot_recovery[chat_id]["retry"]`).
3. `domains = _list_addon_domains(account)` inside try/except.
4. If the fetch raises **or** `domains` is empty → **manual-cPanel fallback**
   (Component 6) using `retry_ctx`, and return (recovery state stays stashed so
   Retry still works after a manual deletion).
5. Otherwise set `_pending_slot_recovery[chat_id]["domains"] = domains` and send
   one button per domain (`callback_data = f"freeslot_rm:{idx}"`) plus a Cancel
   button (`freeslot_cancel`).

### 4. Removal + retry offer (callbacks)
- `freeslot_rm:<idx>` → look up `_pending_slot_recovery[chat_id]`; if missing,
  edit message to "⚠️ No active recovery." and return. Else show a confirm:
  "⚠️ Remove `domain` from hosting?" with `freeslot_confirm:<idx>` /
  `freeslot_cancel`.
- `freeslot_confirm:<idx>` → resolve `domain` from the stashed `domains[idx]` and
  `account` from `account_idx`; call `cpanel_remove_domain(domain, account)`
  inside try/except:
  - **success** (no `errors`) → send "✅ `domain` removed." then a single
    **🔁 Retry deploy** button (`freeslot_retry`).
  - **failure** (`errors` present **or** exception) → **manual-cPanel fallback**
    (Component 6), which itself includes the 🔁 Retry button.
- `freeslot_cancel` → edit message to "🚫 Cancelled." and
  `_pending_slot_recovery.pop(chat_id, None)`.
- `freeslot_retry` → read `retry_ctx = _pending_slot_recovery[chat_id]["retry"]`
  (if missing, "⚠️ Nothing to retry."), pop `_pending_slot_recovery[chat_id]`,
  then dispatch (Component 5). If the retry re-hits the cap, `_offer_free_slot`
  simply re-stashes fresh recovery state, so the re-offer still works.

### 5. Retry dispatch — `retry_ctx`
Stashed at failure time. Two kinds:
- `{"kind": "generate", "domain", "zip_path", "account_idx"}` →
  `_deploy_to_cpanel(chat_id, domain, zip_path, account_idx)`.
- `{"kind": "setup", "domain", "account_idx"}` →
  `_start_website_setup(chat_id, domain, account_idx)`.

`freeslot_retry` pops `_pending_slot_recovery[chat_id]` before dispatching so a
fresh failure starts clean.

### 6. Manual-cPanel fallback — `_manual_cpanel_removal_msg(chat_id, domain, account, retry_ctx=None)`
Shared by the recovery path **and** the existing `/remove_domain` `confirm_remove`
failure. Sends:

> ⚠️ Couldn't remove `domain` automatically (cPanel refused / no access).
> Remove it manually: log into cPanel → **Domains / Addon Domains** → delete
> `domain`. cPanel: `<account['url']>`

(`account['url']` only — no credentials.) When called with a `retry_ctx`
(recovery path), also append a **🔁 Retry deploy** button (`freeslot_retry`); when
called from `/remove_domain` (no retry_ctx), no button. Self-healing note: if the
user retries without actually freeing a slot, the deploy re-hits the limit and
re-offers recovery — an acceptable loop.

### 7. Refactor — extract `_deploy_to_cpanel(chat_id, domain, zip_path, account_idx)`
Lift the create-domain → upload → extract → server-delete body out of
`gen_deploy_acc` into a function taking explicit params. It touches **neither**
`_pending_deploys` **nor** `_pending_slot_recovery`. The thin `gen_deploy_acc`
wrapper keeps the `_pending_deploys.pop(chat_id)` (`2160`) and then calls
`_deploy_to_cpanel(...)`. The retry path calls `_deploy_to_cpanel(...)` directly
with values from `retry_ctx` (it has no `_pending_deploys` entry, by design).
Inside `_deploy_to_cpanel`, the create-domain limit branch calls
`_offer_free_slot(chat_id, account_idx, {"kind":"generate", ...})`.

### 8. State & cleanup
- New module dict: `_pending_slot_recovery = {}  # chat_id -> {account_idx, domains, retry}`.
- Add it to the `/cancel` cleanup (`~657`) alongside the other `pending_*` dicts.
- Chat-keyed, worker-owned → no locking.

## Data Flow (generate Deploy, happy recovery)

```
Deploy → _deploy_to_cpanel → cpanel_create_domain → limit error
  → _offer_free_slot(generate ctx) → list addon domains as buttons
  → user taps domain → confirm → freeslot_confirm → cpanel_remove_domain OK
  → "✅ removed" + 🔁 Retry → freeslot_retry → _deploy_to_cpanel (succeeds)
```

If removal fails at `freeslot_confirm` → `_manual_cpanel_removal_msg` (+🔁 Retry).

## Testing

Standalone scripts (TDD), monkeypatching `tg_send`/`cpanel_*`/`_list_addon_domains`
as existing tests do:
- `_is_addon_limit_error`: true for the cap phrasings, false for generic errors.
- `_offer_free_slot`: empty/unfetchable domain list → manual fallback (no
  buttons, recovery state not stashed); non-empty → stashes
  `_pending_slot_recovery` with the domain list and `retry`.
- Retry dispatch: `freeslot_retry` with `kind="generate"` calls
  `_deploy_to_cpanel` with the stashed params; `kind="setup"` calls
  `_start_website_setup`.
- Removal failure (both `errors` payload and raised exception) routes to
  `_manual_cpanel_removal_msg`.

## Files Touched

- `src/main.py` — new helpers (`_is_addon_limit_error`, `_list_addon_domains`,
  `_offer_free_slot`, `_manual_cpanel_removal_msg`, `_deploy_to_cpanel`), new
  callbacks (`freeslot_rm`, `freeslot_confirm`, `freeslot_cancel`,
  `freeslot_retry`), `_pending_slot_recovery` dict + `/cancel` cleanup,
  refactors of `gen_deploy_acc`, `_start_website_setup`, `_start_remove_domain`,
  `confirm_remove`.
- New tests under `tests/`.

## Risks & Mitigations

- **50-button keyboard** — acceptable in Telegram; pagination is YAGNI.
- **Stale recovery state** — cleared by `/cancel` and popped on retry dispatch.
- **Retry without freeing a slot** — self-heals by re-offering recovery.
- **Long domain names in callback_data** — avoided via index-based selection.

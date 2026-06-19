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
kbds = [kw.get("reply_markup") for _t, kw in sent if kw.get("reply_markup")]
flat = str(kbds)
if "freeslot_rm:0" not in flat or "freeslot_rm:2" not in flat:
    failures.append(f"missing indexed remove buttons: {flat}")

# Case B: no addon domains -> manual/can't-list fallback, recovery kept (retry works).
main._list_addon_domains = lambda account: []
main._pending_slot_recovery.clear()
sent.clear()
main._offer_free_slot(555, 0, ctx)
flat = " ".join(t for t, _ in sent).lower()
if "manually" not in flat and "cpanel" not in flat:
    failures.append(f"empty list should show manual fallback: {flat}")
# Fix A: must NOT name the domain being deployed as something to remove.
if "new.com" in flat:
    failures.append(f"can't-list fallback wrongly names the deploy domain: {flat}")
if main._pending_slot_recovery.get(555, {}).get("retry") != ctx:
    failures.append("manual fallback must keep retry ctx stashed")

# Case C: list call raises -> fallback, no crash.
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

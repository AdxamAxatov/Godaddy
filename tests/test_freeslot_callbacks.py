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

# --- freeslot_confirm success -> removal ok, offers retry, list NOT mutated (fix B) ---
main.cpanel_remove_domain = lambda domain, account: {"errors": None}
main._pending_slot_recovery.clear()
main._pending_slot_recovery[9] = {"account_idx": 0, "domains": ["keep.com", "gone.com"],
    "retry": {"kind": "generate", "domain": "n", "zip_path": "/z", "account_idx": 0}}
sent.clear()
main.handle_callback(CB, 9, 1, "freeslot_confirm:1")
if not any("removed" in s.lower() for s in sent):
    failures.append(f"confirm success should report removed: {sent}")
if main._pending_slot_recovery[9]["domains"] != ["keep.com", "gone.com"]:
    failures.append("fix B: domains list must stay index-stable after removal")

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

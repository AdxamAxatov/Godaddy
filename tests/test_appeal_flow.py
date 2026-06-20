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

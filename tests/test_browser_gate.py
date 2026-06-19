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

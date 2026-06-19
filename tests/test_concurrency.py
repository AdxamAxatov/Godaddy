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

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

# Hammer is_authorized while another thread churns APPROVED_USERS (add AND remove).
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
        key = str(1000 + (i % 50))
        with main._auth_lock:
            if key in main.APPROVED_USERS:
                main.APPROVED_USERS.pop(key, None)
            else:
                main.APPROVED_USERS[key] = {"name": "x", "username": ""}


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

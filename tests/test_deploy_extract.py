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

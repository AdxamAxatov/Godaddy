import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import main

failures = []


class _Resp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


# Returns ONLY addon_domains, not main/parked.
payload = {"data": {
    "addon_domains": ["a.com", "b.com"],
    "parked_domains": ["p.com"],
    "main_domain": "main.com",
}}
main._http = lambda method, url, **kw: _Resp(payload)
account = {"url": "https://cp", "username": "u", "password": "x", "label": "L"}
out = main._list_addon_domains(account)
if out != ["a.com", "b.com"]:
    failures.append(f"expected only addon domains, got {out}")

if failures:
    for f in failures:
        print("FAIL:", f)
    sys.exit(1)
print("PASS: _list_addon_domains returns addon domains only")

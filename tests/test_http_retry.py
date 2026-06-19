"""TDD test for _http(): retry + backoff on transient failures.

Run with the project venv:  .venv/bin/python tests/test_http_retry.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import main

failures = []

# No real waiting between retries during tests.
main._HTTP_BACKOFF_BASE = 0


class _Resp:
    def __init__(self, status_code=200):
        self.status_code = status_code

    def json(self):
        return {"ok": True, "status": self.status_code}


# 1. Transient ConnectionError ("Connection aborted") twice, then success.
calls = {"n": 0}

def flaky(method, url, **kwargs):
    calls["n"] += 1
    if calls["n"] < 3:
        raise main.requests.exceptions.ConnectionError("('Connection aborted.', ...)")
    return _Resp(200)

main.requests.request = flaky
resp = main._http("GET", "http://example/test")
if calls["n"] != 3:
    failures.append(f"connection-retry: expected 3 attempts, got {calls['n']}")
if resp.status_code != 200:
    failures.append(f"connection-retry: expected 200 response, got {resp.status_code}")

# 2. Always Timeout -> exhausts retries and raises (1 + 3 = 4 attempts).
calls["n"] = 0

def always_timeout(method, url, **kwargs):
    calls["n"] += 1
    raise main.requests.exceptions.Timeout("slow")

main.requests.request = always_timeout
try:
    main._http("POST", "http://example/test")
    failures.append("exhaustion: expected Timeout to be raised, none raised")
except main.requests.exceptions.Timeout:
    if calls["n"] != 4:
        failures.append(f"exhaustion: expected 4 attempts, got {calls['n']}")

# 3. HTTP 5xx is retried, then a 200 is returned.
calls["n"] = 0

def flaky_5xx(method, url, **kwargs):
    calls["n"] += 1
    return _Resp(503) if calls["n"] < 3 else _Resp(200)

main.requests.request = flaky_5xx
resp = main._http("GET", "http://example/test")
if resp.status_code != 200:
    failures.append(f"5xx-retry: expected final 200, got {resp.status_code}")
if calls["n"] != 3:
    failures.append(f"5xx-retry: expected 3 attempts, got {calls['n']}")

# 4. Success on first try -> exactly one attempt.
calls["n"] = 0

def ok(method, url, **kwargs):
    calls["n"] += 1
    return _Resp(200)

main.requests.request = ok
main._http("GET", "http://example/test")
if calls["n"] != 1:
    failures.append(f"happy-path: expected 1 attempt, got {calls['n']}")

if failures:
    for f in failures:
        print("FAIL:", f)
    sys.exit(1)
print("PASS: _http retries transient errors + 5xx, raises after exhaustion")

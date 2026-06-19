"""TDD test for _friendly_cpanel_error(): clear message for the addon-domain cap.

Run with the project venv:  .venv/bin/python tests/test_cpanel_error_message.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import main

failures = []

# Real-world cPanel phrasings for hitting the addon-domain limit.
limit_messages = [
    "Sorry, you have reached your maximum number (50) of addon domains.",
    "The maximum number of addon domains the account may have has been reached.",
    "Addon domain limit exceeded.",
]
for msg in limit_messages:
    out = main._friendly_cpanel_error(msg)
    low = out.lower()
    if "50" not in out and "limit" not in low and "full" not in low and "maximum" not in low:
        failures.append(f"limit msg not recognized as a cap: {msg!r} -> {out!r}")
    # Must point the user at a concrete next step.
    if "remove_domain" not in low and "another" not in low:
        failures.append(f"limit msg gives no next step: {msg!r} -> {out!r}")

# A generic/unknown error must still be surfaced (not swallowed or mislabeled).
generic = "DNS zone could not be created"
out = main._friendly_cpanel_error(generic)
if generic not in out:
    failures.append(f"generic error not surfaced: {out!r}")

if failures:
    for f in failures:
        print("FAIL:", f)
    sys.exit(1)
print("PASS: _friendly_cpanel_error flags the addon-domain cap and passes generic errors through")

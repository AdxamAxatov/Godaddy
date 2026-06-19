import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import main

failures = []

cap_msgs = [
    "Sorry, you have reached your maximum number (50) of addon domains.",
    "The maximum number of addon domains the account may have has been reached.",
    "Addon domain limit exceeded.",
]
for m in cap_msgs:
    if not main._is_addon_limit_error(m):
        failures.append(f"should detect cap: {m!r}")

for m in ["DNS zone could not be created", "Domain already exists", ""]:
    if main._is_addon_limit_error(m):
        failures.append(f"should NOT detect cap: {m!r}")

# _friendly_cpanel_error still flags the cap and passes generic through.
if "limit" not in main._friendly_cpanel_error(cap_msgs[0]).lower():
    failures.append("friendly error lost cap message")
if "DNS zone" not in main._friendly_cpanel_error("DNS zone could not be created"):
    failures.append("friendly error lost generic message")

if failures:
    for f in failures:
        print("FAIL:", f)
    sys.exit(1)
print("PASS: _is_addon_limit_error detects cap, _friendly_cpanel_error intact")

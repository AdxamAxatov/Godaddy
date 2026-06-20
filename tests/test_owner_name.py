import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import website_generator as wg

failures = []

# Personal local-part -> that name.
if wg._resolve_owner_name("lorna@pressonlogistics.com", "pressonlogistics.com") != "Lorna":
    failures.append("personal email should yield 'Lorna'")

# Generic mailbox -> a name from the pool, STABLE per domain.
a = wg._resolve_owner_name("info@pressonlogistics.com", "pressonlogistics.com")
b = wg._resolve_owner_name("info@pressonlogistics.com", "pressonlogistics.com")
if a != b:
    failures.append(f"generic mailbox name not stable per domain: {a} != {b}")
if a not in wg._OWNER_FIRST_NAMES:
    failures.append(f"generic fallback name not from pool: {a}")

# Empty email still works off the domain.
if not wg._resolve_owner_name("", "pressonlogistics.com"):
    failures.append("empty email should still yield a name from domain")

# FIX 3: must NOT disturb the global RNG.
random.seed(0)
x = random.random()
wg._resolve_owner_name("info@somecarrier.com", "somecarrier.com")
random.seed(0)
y = random.random()
if x != y:
    failures.append("resolver disturbed the global RNG (must use private Random)")

if failures:
    for f in failures:
        print("FAIL:", f)
    sys.exit(1)
print("PASS: owner-name resolver (personal/generic/stable/RNG-isolated)")
